import subprocess
import json
import os
from typing import List, Dict

def run_linter(path: str) -> str:
    """
    Run pylint on the specific repository path only
    """
    try:
        # Ensure we're working with absolute path
        abs_path = os.path.abspath(path)
        
        # Verify the path exists and is a directory
        if not os.path.exists(abs_path):
            raise Exception(f"Path does not exist: {abs_path}")
        
        if not os.path.isdir(abs_path):
            raise Exception(f"Path is not a directory: {abs_path}")
        
        # Change to the repository directory to ensure relative paths work correctly
        original_cwd = os.getcwd()
        os.chdir(abs_path)
        
        print(f"Running pylint on: {abs_path}")
        print(f"Current working directory: {os.getcwd()}")
        
        # Run pylint with specific configurations
        result = subprocess.run(
            [
                "pylint",
                ".",  # Scan current directory (the cloned repo)
                "--output-format=json",
                "--disable=all",
                "--enable=C0114,C0115,C0301,C0303,C0411,C0412,C0413,C0414,C0415,C0416,D0123,C0417,E0401,E1101,E1102,E1103,E1104,E1105,E1106,E1120,E1121,E1122,E1123",
                "--ignore=.git,node_modules,__pycache__,.vscode,.idea,venv,env",  # Ignore common non-source directories
                "--recursive=y"  # Recursively scan subdirectories
            ],
            capture_output=True,
            text=True,
            cwd=abs_path  # Ensure subprocess runs in the repo directory
        )
        
        # Restore original working directory
        os.chdir(original_cwd)
        
        print(f"Pylint exit code: {result.returncode}")
        print(f"Pylint stdout length: {len(result.stdout)}")
        print(f"Pylint stderr: {result.stderr}")
        
        return result.stdout
        
    except Exception as e:
        # Restore original directory in case of error
        if 'original_cwd' in locals():
            os.chdir(original_cwd)
        print(f"Error in run_linter: {str(e)}")
        raise e


def parse_linter_output(output: str, temp_dir: str) -> List[Dict]:
    """
    Parse pylint JSON output and ensure all paths are relative to repository
    """
    try:
        if not output.strip():
            print("Empty linter output")
            return []
            
        data = json.loads(output)
        issues = []
        temp_dir = os.path.abspath(temp_dir)
        
        print(f"Parsing {len(data)} linter issues")
        print(f"Repository temp directory: {temp_dir}")

        for item in data:
            abs_path = item.get("path")
            
            if not abs_path:
                continue
                
            # Convert to absolute path if it's relative
            if not os.path.isabs(abs_path):
                abs_path = os.path.join(temp_dir, abs_path)
            
            # Ensure the file is actually in the repository
            if not is_file_in_repository(abs_path, temp_dir):
                print(f"Skipping file outside repository: {abs_path}")
                continue
            
            # Calculate relative path for display
            try:
                relative_path = os.path.relpath(abs_path, start=temp_dir)
            except ValueError:
                print(f"Could not calculate relative path for: {abs_path}")
                continue
            
            # Skip if relative path goes outside the repo (starts with ..)
            if relative_path.startswith('..'):
                print(f"Skipping file outside repository bounds: {relative_path}")
                continue

            issues.append({
                "file_path": abs_path,               # Full path for backend processing
                "display_path": relative_path,       # Clean relative path for display
                "line_number": item.get("line", 1),
                "column_number": item.get("column", 1),
                "code": item.get("message-id", "UNKNOWN"),  
                "message": item.get("message", "No message"),
                "symbol": item.get("symbol", ""),
            })

        print(f"Returning {len(issues)} valid issues")
        return issues

    except json.JSONDecodeError as e:
        print(f"JSON decode error: {str(e)}")
        print(f"Raw output: {output[:500]}...")  # First 500 chars for debugging
        return [{"error": f"Invalid JSON from linter: {str(e)}"}]
    except Exception as e:
        print(f"Parse error: {str(e)}")
        return [{"error": f"Failed to parse linter output: {str(e)}"}]


def is_file_in_repository(file_path: str, repo_root: str) -> bool:
    """
    Check if a file is actually inside the repository directory
    """
    try:
        # Convert both paths to absolute paths
        file_path = os.path.abspath(file_path)
        repo_root = os.path.abspath(repo_root)
        
        # Check if file path starts with repo root
        common_path = os.path.commonpath([file_path, repo_root])
        
        # File is in repository if the common path is the repository root
        return common_path == repo_root
        
    except (ValueError, OSError) as e:
        print(f"Error checking if file is in repository: {str(e)}")
        return False