from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import places, projects
from app.database import Base, engine


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Travel Planner",
    version="0.1.0",
    description="Plan trips by collecting artworks from the Art Institute of Chicago as places to visit.",
    lifespan=lifespan,
)

app.include_router(projects.router)
app.include_router(places.router)


@app.get("/", tags=["meta"])
def root():
    return {"message": "Travel Planner API", "docs": "/docs"}
