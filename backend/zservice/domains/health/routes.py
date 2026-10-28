"""GET /api/healthz — answers "ok" once the app has imported and can serve requests.

Public on purpose (the Docker HEALTHCHECK has no credentials), so it must never return
anything beyond the fixed status.
"""

from fastapi import APIRouter

router = APIRouter()

PATH = "/api/healthz"


@router.get(PATH)
def healthz() -> dict:
    return {"status": "ok"}
