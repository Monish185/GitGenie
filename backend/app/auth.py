from fastapi import APIRouter, Request, Depends, HTTPException
import os
import httpx
from dotenv import load_dotenv

load_dotenv()
router = APIRouter()

CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")

@router.get("/login")
async def login(request: Request):
    if not CLIENT_ID or not CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="GitHub OAuth credentials are not set.")
    
    redirect_uri = "http://localhost:5173/callback"
    return {
        "authorization_url": f"https://github.com/login/oauth/authorize?client_id={CLIENT_ID}&scope=repo&redirect_uri={redirect_uri}"
    }


@router.get("/callback")
async def github_callback(code: str, request: Request):
    if not CLIENT_ID or not CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="GitHub OAuth credentials are not set.")
    
    token_url = "https://github.com/login/oauth/access_token"
    headers = {"Accept":"application/json"}
    async with httpx.AsyncClient() as client:
        res = await client.post(token_url,data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code
        }, headers=headers)
        res.raise_for_status()
        if res.status_code != 200:
            raise HTTPException(status_code=res.status_code, detail="Failed to retrieve access token from GitHub.")
        data = res.json()
        return {
            "access_token": data.get("access_token"),
            "token_type": data.get("token_type"),
            "scope": data.get("scope")
        }



