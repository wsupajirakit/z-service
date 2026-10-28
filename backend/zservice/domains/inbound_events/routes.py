"""/api/events/inbound/{sender}: the public receiving end (authenticated by its Standard
Webhooks signature, not by a session); /api/inbound-events: the list, for signed-in users."""

from typing import Annotated

from fastapi import APIRouter, Query, Request, Response

from . import service

router = APIRouter()
INBOUND_PREFIX = "/api/events/inbound/"


@router.post(INBOUND_PREFIX + "{sender}", status_code=204)
async def receive(sender: str, request: Request) -> Response:
    body = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}
    service.receive(sender, headers, body)  # raises ApiError with the refusal code
    return Response(status_code=204)


@router.get("/api/inbound-events")
def inbound_events(
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    sender: Annotated[str | None, Query(max_length=40)] = None,
    event_type: Annotated[str | None, Query(alias="type", max_length=100)] = None,
):
    return service.recent(limit, sender, event_type)
