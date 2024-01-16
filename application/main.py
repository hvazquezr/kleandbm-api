"""Python FastAPI Auth0 integration example
"""

from fastapi import FastAPI, Security, APIRouter, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from typing import List

from application.utils import VerifyToken
from application.models.kleandbm import Project, ProjectHeader, ProjectCreate, ProjectUpdate, Job, JobResult
from application.config import get_settings

import worker.main as worker

from services.project_service import ProjectService

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

@router.post("/projects", response_model=Job, status_code=202)
async def create_project(new_project: ProjectCreate, response: Response, auth_result: str = Security(auth.verify)):
    job = worker.create_project.delay(new_project.model_dump(exclude_none=True))
    response.status_code = status.HTTP_202_ACCEPTED
    return {"jobId": job.id}
    #response.status_code = status.HTTP_202_ACCEPTED
    #return ProjectService.create_project(new_project)

@router.get("/jobs/{job_id}", response_model=JobResult)
async def get_status(job_id: str, auth_result: str = Security(auth.verify)):
    job_result = worker.celery.AsyncResult(job_id)
    #job_result.get() # Cleaning results
    #task_result.forget()
    result = {
        "jobId": job_id,
        "status": job_result.status,
        "result": job_result.result
    }
    return result

@router.get("/projects", response_model=List[ProjectHeader])
async def get_projects(auth_result: str = Security(auth.verify)):
    projects = await ProjectService.get_projects()
    return projects

@router.get("/projects/{project_id}", response_model=Project)
async def get_project(project_id: str, auth_result: str = Security(auth.verify)):
    project = await ProjectService.get_project(project_id)
    return project

@router.patch("/projects/{project_id}", response_model=ProjectUpdate)
async def update_project(project_id: str, updated_project: ProjectUpdate, auth_result: str = Security(auth.verify)):
    return (await ProjectService.update_project(project_id, updated_project))


    
app.include_router(router)