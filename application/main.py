"""Python FastAPI Auth0 integration example
"""

from fastapi import FastAPI, Security, APIRouter, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from typing import List

from application.utils import VerifyToken
from application.models.kleandbm import Project, ProjectHeader, ProjectCreate, ProjectUpdate, NodeUpdate,Job, JobResult, TableUpdate, RelationshipUpdate, AITablesUpdate
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
    #worker.generate_project_image.delay(new_project.id, new_project.questions)
    response.status_code = status.HTTP_202_ACCEPTED
    return {"jobId": job.id}

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
    project = await ProjectService.async_get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.patch("/projects/{project_id}", response_model=ProjectUpdate)
async def update_project(project_id: str, updated_project: ProjectUpdate, auth_result: str = Security(auth.verify)):
    return (await ProjectService.update_project(project_id, updated_project))

@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(project_id: str, auth_result: str = Security(auth.verify)):
    await ProjectService.delete_project(project_id)
    return Response(status_code = status.HTTP_204_NO_CONTENT)

@router.patch("/projects/{project_id}/nodes/{node_id}", response_model= NodeUpdate)
async def update_node(project_id: str, node_id:str, updated_node: NodeUpdate, auth_result: str = Security(auth.verify)):
    return (await ProjectService.update_node(project_id, node_id, updated_node))

@router.delete("/projects/{project_id}/nodes/{node_id}", status_code=204)
async def delete_node(project_id: str, node_id: str, auth_result: str = Security(auth.verify)):
    await ProjectService.delete_node(project_id, node_id)
    return Response(status_code = status.HTTP_204_NO_CONTENT)

@router.patch("/projects/{project_id}/tables/{table_id}", response_model= TableUpdate)
async def update_table(project_id: str, table_id:str, updated_table: TableUpdate, auth_result: str = Security(auth.verify)):
    return (await ProjectService.update_table(project_id, table_id, updated_table))

@router.delete("/projects/{project_id}/tables/{table_id}", status_code=204)
async def delete_table(project_id: str, table_id: str, auth_result: str = Security(auth.verify)):
    await ProjectService.delete_table(project_id, table_id)
    return Response(status_code = status.HTTP_204_NO_CONTENT)

@router.patch("/projects/{project_id}/relationships/{relationship_id}", response_model= RelationshipUpdate)
async def update_relationship(project_id: str, relationship_id: str, updated_relationship: RelationshipUpdate, auth_result: str = Security(auth.verify)):
    return (await ProjectService.update_relationship(project_id, relationship_id, updated_relationship))

@router.delete("/projects/{project_id}/relationships/{relationship_id}", status_code=204)
async def delete_relationship(project_id: str, relationship_id: str, auth_result: str = Security(auth.verify)):
    await ProjectService.delete_relationship(project_id, relationship_id)
    return Response(status_code = status.HTTP_204_NO_CONTENT)

@router.get("/projects/{project_id}/sql", response_model=Job)
async def get_project_sql(project_id: str, response: Response, auth_result: str = Security(auth.verify)):
    job = worker.get_project_sql.delay(project_id)
    response.status_code = status.HTTP_202_ACCEPTED
    return {"jobId": job.id}

@router.post("/projects/{project_id}/aisuggestedtables", response_model=Job)
async def generate_table_recommendations_with_ai(project_id: str, aiTableUpdate: AITablesUpdate, response: Response, auth_result: str = Security(auth.verify)):
    job = worker.generate_table_recommendations.delay(project_id, aiTableUpdate.prompt, aiTableUpdate.position.model_dump())
    response.status_code = status.HTTP_202_ACCEPTED
    return {"jobId": job.id}

@router.post("/projects/{project_id}/tables/{table_id}/aitableedits")
async def generate_table_edit_with_ai(project_id: str, table_id: str, user_request: dict, response: Response, auth_result: str = Security(auth.verify)):
    job = worker.generate_table_edits.delay(project_id, user_request)
    response.status_code = status.HTTP_202_ACCEPTED
    return {"jobId": job.id}

@router.get("/image/{image_id}")
async def get_project_image(image_id: str):
    response = ProjectService.get_project_imagae(image_id)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

    
app.include_router(router)