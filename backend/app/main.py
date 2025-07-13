from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.auth import router as auth_router
from app.github_api import router as github_api_router
from app.analyze import router as analyze_router
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials = True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth",tags=["auth"])
app.include_router(github_api_router, prefix="/github", tags=["github"])
app.include_router(analyze_router, prefix="/analyze", tags=["analyze"])

@app.get("/")
def read_root():
    return {"message": "Welcome to Gitpal!"}