from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.artic import ArticNotFound, ArticUpstreamError, fetch_artwork
from app.database import get_db

MAX_PLACES = 10

router = APIRouter(prefix="/projects/{project_id}/places", tags=["places"])


def _get_project_or_404(db: Session, project_id: int) -> models.Project:
    project = db.get(models.Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("", response_model=schemas.PlaceOut, status_code=status.HTTP_201_CREATED)
async def add_place(
    project_id: int,
    payload: schemas.PlaceIn,
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(db, project_id)

    if len(project.places) >= MAX_PLACES:
        raise HTTPException(
            status_code=400,
            detail=f"Project already has the maximum of {MAX_PLACES} places",
        )
    if any(p.external_id == payload.external_id for p in project.places):
        raise HTTPException(
            status_code=409,
            detail="This place is already in the project",
        )

    try:
        art = await fetch_artwork(payload.external_id)
    except ArticNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ArticUpstreamError as e:
        raise HTTPException(status_code=502, detail=str(e))

    place = models.Place(
        project_id=project_id,
        external_id=art["external_id"],
        title=art["title"],
    )
    db.add(place)
    db.commit()
    db.refresh(place)
    return place


@router.get("", response_model=list[schemas.PlaceOut])
def list_places(project_id: int, db: Session = Depends(get_db)):
    return _get_project_or_404(db, project_id).places


@router.get("/{place_id}", response_model=schemas.PlaceOut)
def get_place(project_id: int, place_id: int, db: Session = Depends(get_db)):
    place = db.get(models.Place, place_id)
    if place is None or place.project_id != project_id:
        raise HTTPException(status_code=404, detail="Place not found")
    return place


@router.patch("/{place_id}", response_model=schemas.PlaceOut)
def update_place(
    project_id: int,
    place_id: int,
    payload: schemas.PlaceUpdate,
    db: Session = Depends(get_db),
):
    place = db.get(models.Place, place_id)
    if place is None or place.project_id != project_id:
        raise HTTPException(status_code=404, detail="Place not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(place, field, value)
    db.commit()
    db.refresh(place)
    return place
