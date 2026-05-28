# Travel Planner

A small REST API for planning trips. A **project** is a trip; it contains **places** sourced from the [Art Institute of Chicago API](https://api.artic.edu/docs/) (treated here as places to visit). Travellers add notes to places, mark them as visited, and the project auto-completes once every place has been visited.

## Tech stack

- **Python 3.13** managed by [uv](https://docs.astral.sh/uv/)
- **FastAPI** + **Uvicorn**
- **SQLAlchemy 2** with **SQLite**
- **httpx** for the external API client
- **Docker** + **docker compose** for local runs

## Run with Docker (recommended)

```bash
docker compose up --build
```

Then open <http://localhost:8000/docs> for the interactive Swagger UI.

The SQLite file lives at `./data/travel.db` on the host (mounted into the container), so data persists across `docker compose down`.

## Run locally without Docker

```bash
uv sync
uv run uvicorn app.main:app --reload
```

Same URL, same docs. Run this from the project root so the relative SQLite path resolves correctly.

## Configuration

| Env var | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/travel.db` | SQLAlchemy URL. Inside Docker overridden to `sqlite:////app/data/travel.db` (absolute). |

## API documentation

- Interactive: <http://localhost:8000/docs> (Swagger UI) — also <http://localhost:8000/redoc>
- Raw OpenAPI spec: [`docs/openapi.json`](docs/openapi.json) — paste into <https://editor.swagger.io/> or import into Postman.

To regenerate the spec after changing endpoints:

```bash
uv run python -c "import json; from app.main import app; print(json.dumps(app.openapi(), indent=2))" > docs/openapi.json
```

### Endpoints

| Method | Path | Behaviour |
|---|---|---|
| `POST` | `/projects` | Create project. Optional `places: [{external_id}]` array (max 10); each is validated against the Art Institute API before save. |
| `GET` | `/projects` | List all projects (with nested places). |
| `GET` | `/projects/{id}` | Single project. |
| `PATCH` | `/projects/{id}` | Update `name` / `description` / `start_date`. |
| `DELETE` | `/projects/{id}` | `204 No Content` on success; **`409`** if any place in the project is already visited. |
| `POST` | `/projects/{id}/places` | Add one place. Validates against the Art Institute API; enforces max 10 per project; rejects duplicates per `external_id`. |
| `GET` | `/projects/{id}/places` | List places for a project. |
| `GET` | `/projects/{id}/places/{place_id}` | Single place. |
| `PATCH` | `/projects/{id}/places/{place_id}` | Update `notes` and/or `visited`. |

A project's `completed` flag is **derived**, not stored: `len(places) > 0 and all(p.visited for p in places)`. It is computed on each response, so it can never drift from the underlying place state.

### Error responses

| Status | When |
|---|---|
| `404` | Project, place, or external artwork not found. |
| `409` | Duplicate place in request or in project; delete blocked by visited places. |
| `400` / `422` | Body validation (empty name, too many places, etc.). |
| `502` | Art Institute API is unreachable or returning 5xx. |

## Example requests

Create a project with one real artwork (Seurat — *A Sunday on La Grande Jatte*, Art Institute ID `27992`):

```bash
curl -X POST localhost:8000/projects \
  -H 'content-type: application/json' \
  -d '{"name":"Paris weekend","places":[{"external_id":27992}]}'
```

Add another place to that project:

```bash
curl -X POST localhost:8000/projects/1/places \
  -H 'content-type: application/json' \
  -d '{"external_id":111628}'
```

Mark a place as visited (the project flips to `completed: true` once every place is visited):

```bash
curl -X PATCH localhost:8000/projects/1/places/1 \
  -H 'content-type: application/json' \
  -d '{"visited":true,"notes":"Loved it"}'
```

Try to delete a project that has visited places — blocked with `409`:

```bash
curl -i -X DELETE localhost:8000/projects/1
```

## Project layout

```
app/
├── main.py        # FastAPI app, router registration, lifespan (Base.metadata.create_all)
├── database.py    # engine, SessionLocal, Base, get_db dependency
├── models.py      # Project, Place ORM models
├── schemas.py     # Pydantic request/response models (incl. derived `completed`)
├── artic.py       # Art Institute API client (httpx)
├── projects.py    # /projects router
└── places.py      # /projects/{id}/places router

docs/openapi.json  # generated OpenAPI 3.1 spec
Dockerfile
docker-compose.yml
```

## Design notes

In scope:
- Validation at API and DB layers — max 10 places per project, unique `(project_id, external_id)`, name length, etc.
- External API validation: places are verified against the Art Institute before being stored, and the artwork title is cached locally for display.
- `completed` is derived rather than stored, preventing drift.
- Foreign-key cascade so deleting a project deletes its places (still gated by the "no visited places" rule).
