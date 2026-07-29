import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from geoflow_config import get_settings

from geoflow_api.auth.dependencies import CurrentUser
from geoflow_api.models import AreaOfInterest, Project
from geoflow_api.projects.dependencies import get_project_service
from geoflow_api.projects.geojson import GeoJSONValidationError
from geoflow_api.projects.service import ProjectService, ResourceNotFoundError
from geoflow_api.schemas import (
    AOICreate,
    AOIResponse,
    AOIUpdate,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)

router = APIRouter(prefix="/projects", tags=["projects"])
ProjectServiceDependency = Annotated[ProjectService, Depends(get_project_service)]


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    user: CurrentUser, service: ProjectServiceDependency
) -> list[Project]:
    return await service.list_projects(user.id)


@router.post(
    "", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED
)
async def create_project(
    payload: ProjectCreate,
    user: CurrentUser,
    service: ProjectServiceDependency,
) -> Project:
    return await service.create_project(
        user.id, name=payload.name, description=payload.description
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    user: CurrentUser,
    service: ProjectServiceDependency,
) -> Project:
    try:
        return await service.get_project(user.id, project_id)
    except ResourceNotFoundError as exc:
        raise _not_found(exc) from exc


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    user: CurrentUser,
    service: ProjectServiceDependency,
) -> Project:
    try:
        return await service.update_project(
            user.id,
            project_id,
            name=payload.name,
            description=payload.description,
            description_is_set="description" in payload.model_fields_set,
        )
    except ResourceNotFoundError as exc:
        raise _not_found(exc) from exc


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: uuid.UUID,
    user: CurrentUser,
    service: ProjectServiceDependency,
) -> None:
    try:
        await service.delete_project(user.id, project_id)
    except ResourceNotFoundError as exc:
        raise _not_found(exc) from exc


@router.get("/{project_id}/aois", response_model=list[AOIResponse])
async def list_aois(
    project_id: uuid.UUID,
    user: CurrentUser,
    service: ProjectServiceDependency,
) -> list[AOIResponse]:
    try:
        aois = await service.list_aois(user.id, project_id)
    except ResourceNotFoundError as exc:
        raise _not_found(exc) from exc
    return [_aoi_response(service, aoi) for aoi in aois]


@router.post(
    "/{project_id}/aois",
    response_model=AOIResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_aoi(
    project_id: uuid.UUID,
    payload: AOICreate,
    user: CurrentUser,
    service: ProjectServiceDependency,
) -> AOIResponse:
    try:
        aoi = await service.create_aoi(
            user.id,
            project_id,
            name=payload.name,
            geometry=payload.geometry,
        )
    except ResourceNotFoundError as exc:
        raise _not_found(exc) from exc
    except GeoJSONValidationError as exc:
        raise _invalid_geometry(exc) from exc
    return _aoi_response(service, aoi)


@router.post(
    "/{project_id}/aois/upload",
    response_model=AOIResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_aoi(
    project_id: uuid.UUID,
    user: CurrentUser,
    service: ProjectServiceDependency,
    name: Annotated[str, Form(min_length=2, max_length=120)],
    file: Annotated[UploadFile, File()],
) -> AOIResponse:
    settings = get_settings()
    content = await file.read(settings.aoi_max_upload_bytes + 1)
    cleaned_name = " ".join(name.split())
    if len(cleaned_name) < 2:
        await file.close()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Name must contain at least 2 characters",
        )
    try:
        aoi = await service.create_aoi_from_upload(
            user.id,
            project_id,
            name=cleaned_name,
            filename=file.filename,
            content_type=file.content_type,
            content=content,
        )
    except ResourceNotFoundError as exc:
        raise _not_found(exc) from exc
    except GeoJSONValidationError as exc:
        raise _invalid_geometry(exc) from exc
    finally:
        await file.close()
    return _aoi_response(service, aoi)


@router.get("/{project_id}/aois/{aoi_id}", response_model=AOIResponse)
async def get_aoi(
    project_id: uuid.UUID,
    aoi_id: uuid.UUID,
    user: CurrentUser,
    service: ProjectServiceDependency,
) -> AOIResponse:
    try:
        aoi = await service.get_aoi(user.id, project_id, aoi_id)
    except ResourceNotFoundError as exc:
        raise _not_found(exc) from exc
    return _aoi_response(service, aoi)


@router.patch("/{project_id}/aois/{aoi_id}", response_model=AOIResponse)
async def update_aoi(
    project_id: uuid.UUID,
    aoi_id: uuid.UUID,
    payload: AOIUpdate,
    user: CurrentUser,
    service: ProjectServiceDependency,
) -> AOIResponse:
    try:
        aoi = await service.update_aoi(
            user.id,
            project_id,
            aoi_id,
            name=payload.name,
            geometry=payload.geometry,
        )
    except ResourceNotFoundError as exc:
        raise _not_found(exc) from exc
    except GeoJSONValidationError as exc:
        raise _invalid_geometry(exc) from exc
    return _aoi_response(service, aoi)


@router.delete(
    "/{project_id}/aois/{aoi_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_aoi(
    project_id: uuid.UUID,
    aoi_id: uuid.UUID,
    user: CurrentUser,
    service: ProjectServiceDependency,
) -> None:
    try:
        await service.delete_aoi(user.id, project_id, aoi_id)
    except ResourceNotFoundError as exc:
        raise _not_found(exc) from exc


def _aoi_response(
    service: ProjectService, aoi: AreaOfInterest
) -> AOIResponse:
    return AOIResponse(
        id=aoi.id,
        project_id=aoi.project_id,
        name=aoi.name,
        geometry=service.serialize_aoi_geometry(aoi),
        area_sq_km=aoi.area_sq_km,
        created_at=aoi.created_at,
        updated_at=aoi.updated_at,
    )


def _not_found(exc: ResourceNotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


def _invalid_geometry(exc: GeoJSONValidationError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=str(exc),
    )
