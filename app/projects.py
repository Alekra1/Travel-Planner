from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.artic import ArticNotFound, ArticUpstreamError, fetch_artwork
from app.database import get_db

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=schemas.ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(payload: schemas.ProjectCreate, db: Session = Depends(get_db)):
    external_ids = [p.external_id for p in payload.places]
    if len(external_ids) != len(set(external_ids)):
        raise HTTPException(status_code=409, detail="Duplicate places in request")

    place_objs: list[models.Place] = []
    for place_in in payload.places:
        try:
            art = await fetch_artwork(place_in.external_id)
        except ArticNotFound as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ArticUpstreamError as e:
            raise HTTPException(status_code=502, detail=str(e))
        place_objs.append(
            models.Place(external_id=art["external_id"], title=art["title"])
        )

    project = models.Project(
        name=payload.name,
        description=payload.description,
        start_date=payload.start_date,
        places=place_objs,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[schemas.ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.scalars(select(models.Project)).all()


@router.get("/{project_id}", response_model=schemas.ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(models.Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=schemas.ProjectOut)
def update_project(
    project_id: int,
    payload: schemas.ProjectUpdate,
    db: Session = Depends(get_db),
):
    project = db.get(models.Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(models.Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if any(p.visited for p in project.places):
        raise HTTPException(
            status_code=409,
            detail="Cannot delete a project with visited places",
        )
    db.delete(project)
    db.commit()
