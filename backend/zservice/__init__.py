"""z-service backend package.

New code lives here, one folder per concern (core, security, domains, integrations).
`backend/main.py` stays the uvicorn entry point and re-exports the legacy names that
other code imports from it, so moving code here never breaks existing callers.
"""
