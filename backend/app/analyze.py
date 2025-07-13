# app/api/gitpal.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os, shutil, tempfile, requests, re
from datetime import datetime
from git import Repo, Actor
from urllib.parse import urlparse

from app.linter import run_linter, parse_linter_output
from app.gemini_fix import fix_code_with_gemini   # must support save flag

router = APIRouter()

# ────────────────── Pydantic models ──────────────────
class AnalyzeRequest(BaseModel):
    repo_url: str
    token: str

class FixRequest(BaseModel):
    file_path: str          # full temp path received from frontend
    smell_code: str
    line_number: int

class PreviewResponse(BaseModel):
    success: bool
    message: str
    file_path: str
    original: str
    preview_code: str

class FileRequest(BaseModel):
    file_path: str          # path the frontend wants to read

class SingleFix(BaseModel):
    file_path: str          # **relative** path inside repo (frontend sends display_path)
    fixed_code: str

class CommitFixesRequest(BaseModel):
    repo_url: str
    token: str
    fixes: List[SingleFix]
    create_pr: Optional[bool] = False  # New field to indicate if PR should be created
    pr_title: Optional[str] = None
    pr_body: Optional[str] = None
    base_branch: Optional[str] = "main"  # Default base branch

class PullRequestResponse(BaseModel):
    success: bool
    branch: str
    files_changed: int
    message: str
    pr_url: Optional[str] = None
    pr_number: Optional[int] = None

# ────────────────── Helper Functions ──────────────────
def extract_repo_info(repo_url: str) -> tuple:
    """Extract owner and repo name from GitHub URL"""
    try:
        # Handle different GitHub URL formats
        if repo_url.startswith("https://github.com/"):
            path = repo_url.replace("https://github.com/", "")
        elif repo_url.startswith("git@github.com:"):
            path = repo_url.replace("git@github.com:", "")
        else:
            raise ValueError("Invalid GitHub URL format")
        
        # Remove .git suffix if present
        if path.endswith(".git"):
            path = path[:-4]
        
        parts = path.split("/")
        if len(parts) != 2:
            raise ValueError("Invalid repository path")
        
        return parts[0], parts[1]  # owner, repo
    except Exception as e:
        raise ValueError(f"Could not parse repository URL: {str(e)}")

def create_github_pull_request(repo_url: str, token: str, branch: str, base_branch: str, 
                              title: str, body: str) -> dict:
    """Create a pull request using GitHub API"""
    try:
        owner, repo = extract_repo_info(repo_url)
        
        # GitHub API endpoint for creating pull requests
        api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }
        
        data = {
            "title": title,
            "head": branch,
            "base": base_branch,
            "body": body
        }
        
        response = requests.post(api_url, headers=headers, json=data)
        
        if response.status_code == 201:
            pr_data = response.json()
            return {
                "success": True,
                "pr_url": pr_data["html_url"],
                "pr_number": pr_data["number"],
                "message": "Pull request created successfully"
            }
        else:
            error_msg = response.json().get("message", "Unknown error")
            return {
                "success": False,
                "message": f"Failed to create PR: {error_msg}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"Error creating pull request: {str(e)}"
        }

def get_default_branch(repo_url: str, token: str) -> str:
    """Get the default branch of the repository"""
    try:
        owner, repo = extract_repo_info(repo_url)
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 200:
            repo_data = response.json()
            return repo_data.get("default_branch", "main")
        else:
            return "main"  # fallback
            
    except Exception:
        return "main"  # fallback

# ────────────────── /analyze ──────────────────
# Update your analyze endpoint in gitpal.py

@router.post("")
def analyze_repo(request: AnalyzeRequest):
    temp_dir = None
    try:
        # Create temporary directory for cloning
        temp_dir = tempfile.mkdtemp()
        print(f"Created temporary directory: {temp_dir}")
        
        # Clone repository
        repo_url = request.repo_url.replace("https://", f"https://{request.token}@")
        print(f"Cloning repository: {request.repo_url}")
        
        repo = Repo.clone_from(repo_url, temp_dir)
        print(f"Repository cloned successfully to: {temp_dir}")
        
        # Verify the repository was cloned successfully
        if not os.path.exists(temp_dir) or not os.path.exists(os.path.join(temp_dir, '.git')):
            raise Exception("Repository cloning failed - .git directory not found")
        
        # List some files to verify the clone worked
        files_in_repo = []
        for root, dirs, files in os.walk(temp_dir):
            # Skip .git directory
            if '.git' in dirs:
                dirs.remove('.git')
            for file in files:
                if file.endswith(('.py', '.js', '.ts', '.java', '.cpp', '.c')):  # Add your target file types
                    rel_path = os.path.relpath(os.path.join(root, file), temp_dir)
                    files_in_repo.append(rel_path)
        
        print(f"Found {len(files_in_repo)} source files in repository")
        if len(files_in_repo) == 0:
            print("Warning: No source files found in repository")
        
        # Run linter ONLY on the cloned repository
        print("Running linter on cloned repository...")
        output = run_linter(temp_dir)
        
        if not output.strip():
            print("Warning: Linter returned empty output")
            return {
                "success": True,
                "message": "Analysis completed - no issues found.",
                "smell_patterns": [],
                "total_issues": 0,
                "repo_path": temp_dir,
            }
        
        # Parse issues and ensure they're all from repository files
        print("Parsing linter output...")
        smell_issues = parse_linter_output(output, temp_dir)
        
        # Filter out any invalid issues
        valid_issues = []
        for issue in smell_issues:
            if 'error' in issue:
                print(f"Error in issue: {issue['error']}")
                continue
                
            # Verify the file path is in the repository
            if 'file_path' in issue and issue['file_path'].startswith(temp_dir):
                valid_issues.append(issue)
            else:
                print(f"Skipping invalid issue: {issue}")
        
        print(f"Analysis complete: {len(valid_issues)} valid issues found")
        
        return {
            "success": True,
            "message": "Analysis completed.",
            "smell_patterns": valid_issues,
            "total_issues": len(valid_issues),
            "repo_path": temp_dir,
        }
        
    except Exception as e:
        error_msg = f"Analysis failed: {str(e)}"
        print(error_msg)
        
        # Clean up temp directory on error
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
                
        raise HTTPException(status_code=500, detail=error_msg)
    try:
        temp_dir = tempfile.mkdtemp()
        repo_url = request.repo_url.replace("https://", f"https://{request.token}@")
        Repo.clone_from(repo_url, temp_dir)

        output = run_linter(temp_dir)
        smell_issues = parse_linter_output(output, temp_dir)  # adds display_path + code

        return {
            "success": True,
            "message": "Analysis completed.",
            "smell_patterns": smell_issues,
            "total_issues": len(smell_issues),
            "repo_path": temp_dir,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ────────────────── /preview-fix ──────────────────
@router.post("/preview-fix", response_model=PreviewResponse)
def preview_fix(req: FixRequest):
    if not os.path.exists(req.file_path):
        raise HTTPException(status_code=404, detail="File not found")

    original_code = open(req.file_path, "r").read()
    preview_code = fix_code_with_gemini(
        req.file_path, req.smell_code, req.line_number, save=False
    )

    return {
        "success": True,
        "message": "Preview generated.",
        "file_path": req.file_path,
        "original": original_code,
        "preview_code": preview_code,
    }

# ────────────────── /generate-fix ──────────────────
@router.post("/generate-fix")
def generate_fix(req: FixRequest):
    if not os.path.exists(req.file_path):
        raise HTTPException(status_code=404, detail="File not found")

    fixed = fix_code_with_gemini(req.file_path, req.smell_code, req.line_number, save=True)
    if not fixed or fixed.startswith("Error"):
        raise HTTPException(status_code=500, detail="Failed to generate fix")

    return {
        "success": True,
        "message": "Fix applied.",
        "file_path": req.file_path,
        "fix": fixed,
    }

# ────────────────── /fix-all (unchanged) ──────────────────
@router.post("/fix-all")
def fix_all(req: AnalyzeRequest):
    try:
        temp_dir = tempfile.mkdtemp()
        repo = Repo.clone_from(
            req.repo_url.replace("https://", f"https://{req.token}@"), temp_dir
        )

        output = run_linter(temp_dir)
        issues = parse_linter_output(output, temp_dir)

        fixed, skipped = [], []
        for iss in issues:
            try:
                code = fix_code_with_gemini(
                    iss["file_path"], iss["code"], iss["line_number"], save=True
                )
                fixed.append({**iss, "fix": code})
            except Exception as e:
                skipped.append({**iss, "error": str(e)})

        return {
            "success": True,
            "message": "Auto‑fix complete.",
            "fixed_issues": fixed,
            "skipped_issues": skipped,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ────────────────── /get-file-content ──────────────────
@router.post("/get-file-content")
def get_file_content(req: FileRequest):
    if not os.path.exists(req.file_path):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        with open(req.file_path, "r") as f:
            return {"content": f.read()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ────────────────── /commit-fixes (Enhanced) ──────────────────
@router.post("/commit-fixes", response_model=PullRequestResponse)
def commit_fixes(req: CommitFixesRequest):
    """
    Enhanced commit-fixes endpoint with pull request support.
    The frontend sends a list of {file_path (relative), fixed_code}.
    We rewrite those files in a fresh clone, commit, and optionally create a PR.
    """
    temp_dir = tempfile.mkdtemp()
    try:
        # Validate input
        if not req.fixes:
            raise HTTPException(status_code=400, detail="No fixes provided")
        
        # Clean and validate repo URL
        if not req.repo_url or not req.token:
            raise HTTPException(status_code=400, detail="Missing repo URL or token")
        
        # Get default branch if not specified
        if not req.base_branch:
            req.base_branch = get_default_branch(req.repo_url, req.token)
        
        # Clone repository
        repo_url = req.repo_url.replace("https://", f"https://{req.token}@")
        try:
            repo = Repo.clone_from(repo_url, temp_dir)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to clone repository: {str(e)}")

        # Process each fix
        files_written = 0
        for fx in req.fixes:
            try:
                # Clean the file path - remove any temp directory prefixes
                clean_path = fx.file_path
                if '/tmp/' in clean_path:
                    # Extract the relative path after the temp directory
                    parts = clean_path.split('/')
                    if len(parts) > 1:
                        # Find the index where the actual repo content starts
                        start_idx = -1
                        for i, part in enumerate(parts):
                            if part and not part.startswith('tmp') and part != '':
                                start_idx = i
                                break
                        if start_idx > 0:
                            clean_path = '/'.join(parts[start_idx:])
                
                # Ensure the path doesn't start with /
                clean_path = clean_path.lstrip('/')
                
                # Create absolute path in the new clone
                abs_path = os.path.join(temp_dir, clean_path)
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                
                # Write the fixed code
                with open(abs_path, "w", encoding='utf-8') as f:
                    f.write(fx.fixed_code)
                
                files_written += 1
                
            except Exception as e:
                print(f"Error processing file {fx.file_path}: {str(e)}")
                # Continue with other files instead of failing completely
                continue

        if files_written == 0:
            raise HTTPException(status_code=400, detail="No files could be written")

        # Check if there are actual changes
        if not repo.is_dirty():
            raise HTTPException(status_code=400, detail="No changes detected in repository")

        # Create and switch to new branch
        branch_name = f"gitpal-fixes-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        try:
            repo.git.checkout("-b", branch_name)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create branch: {str(e)}")

        # Add all changes
        try:
            repo.git.add(all=True)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to add changes: {str(e)}")

        # Commit changes
        try:
            bot = Actor("GitPal Bot", "bot@gitpal.dev")
            commit_message = f"🤖 Apply {files_written} code fixes via GitPal"
            repo.index.commit(commit_message, author=bot, committer=bot)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to commit changes: {str(e)}")

        # Push to remote
        try:
            origin = repo.remote(name="origin")
            origin.push(branch_name)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to push branch: {str(e)}")

        # Create pull request if requested
        pr_url = None
        pr_number = None
        response_message = f"Successfully committed {files_written} fixes and pushed to branch {branch_name}"
        
        if req.create_pr:
            # Set default PR title and body if not provided
            pr_title = req.pr_title or f"🤖 GitPal: Fix {files_written} code smell{'s' if files_written > 1 else ''}"
            pr_body = req.pr_body or f"""## 🤖 GitPal Automated Code Fixes

This pull request contains automated fixes for {files_written} code smell{'s' if files_written > 1 else ''} detected by GitPal.

### Changes Made:
- Applied {files_written} automated fix{'es' if files_written > 1 else ''}
- Improved code quality and maintainability
- Fixed various code smells and anti-patterns

### Review Notes:
- All fixes were generated using AI-powered analysis
- Please review the changes before merging
- Consider running your test suite to ensure nothing is broken

---
*This PR was automatically generated by GitPal 🤖*"""

            pr_result = create_github_pull_request(
                req.repo_url, req.token, branch_name, req.base_branch, pr_title, pr_body
            )
            
            if pr_result["success"]:
                pr_url = pr_result["pr_url"]
                pr_number = pr_result["pr_number"]
                response_message += f" and created pull request #{pr_number}"
            else:
                response_message += f" but failed to create PR: {pr_result['message']}"

        return PullRequestResponse(
            success=True,
            branch=branch_name,
            files_changed=files_written,
            message=response_message,
            pr_url=pr_url,
            pr_number=pr_number
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Catch any other unexpected errors
        print(f"Unexpected error in commit_fixes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        # Always cleanup temp directory
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass

# ────────────────── /get-repo-info ──────────────────
@router.post("/get-repo-info")
def get_repo_info(request: AnalyzeRequest):
    """Get repository information including default branch"""
    try:
        default_branch = get_default_branch(request.repo_url, request.token)
        owner, repo = extract_repo_info(request.repo_url)
        
        return {
            "success": True,
            "owner": owner,
            "repo": repo,
            "default_branch": default_branch,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))