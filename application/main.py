"""Python FastAPI Auth0 integration example
"""

from fastapi import FastAPI, Security, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from .utils import VerifyToken
from celery.result import AsyncResult
import worker.main as worker
from application.config import get_settings

settings = get_settings()
# Creates app instance
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers
)

router = APIRouter(prefix=settings.api_prefix)
auth = VerifyToken()

@router.get("/api/public")
def public():
    """No access token required to access this route"""

    result = {
        "status": "success",
        "msg": ("Hello from a public endpoint! You don't need to be "
                "authenticated to see this.")
    }
    return result

@router.post("/tasks/")
async def create_task_endpoint(auth_result: str = Security(auth.verify)):
    task = worker.create_task.delay()
    return {"task_id": task.id}

@router.get("/tasks/{task_id}")
async def get_status(task_id: str, auth_result: str = Security(auth.verify)):
    task_result = worker.celery.AsyncResult(task_id)
    task_result.get() # Cleaning results
    result = {
        "task_id": task_id,
        "task_status": task_result.status,
        "task_result": task_result.result
    }
    return result

app.include_router(router)