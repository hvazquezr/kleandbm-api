"""Python FastAPI Auth0 integration example
"""

from fastapi import FastAPI, Security
from .utils import VerifyToken
from celery.result import AsyncResult
import worker.main as worker

# Creates app instance
app = FastAPI()
auth = VerifyToken()

@app.get("/api/public")
def public():
    """No access token required to access this route"""

    result = {
        "status": "success",
        "msg": ("Hello from a public endpoint! You don't need to be "
                "authenticated to see this.")
    }
    return result

@app.get("/api/private")
def private(auth_result: str = Security(auth.verify)):
    """A valid access token is required to access this route"""
    return auth_result

@app.post("/tasks/")
def create_task_endpoint(auth_result: str = Security(auth.verify)):
    task = worker.create_task.delay()
    return {"task_id": task.id}

@app.get("/tasks/{task_id}")
def get_status(task_id: str, auth_result: str = Security(auth.verify)):
    task_result = worker.celery.AsyncResult(task_id)
    task_result.get() # Cleaning results
    result = {
        "task_id": task_id,
        "task_status": task_result.status,
        "task_result": task_result.result
    }
    return result