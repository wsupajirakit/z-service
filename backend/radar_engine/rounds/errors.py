"""Errors a round raises for the API to answer."""


class RadarError(Exception):
    """A user-facing problem with the request or the stored data (-> HTTP 400)."""
