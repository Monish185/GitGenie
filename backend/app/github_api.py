from fastapi import APIRouter, Query
import httpx

router = APIRouter()

@router.get("/repos")
async def list_repos(
    token: str = Query(..., description="GitHub personal access token")
):
    url = f"https://api.github.com/user/repos"
    headers = {"Authorization": f"token {token}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
    return response.json()