"""z-service backend entry point: `uvicorn main:app` (Dockerfile CMD).

All code lives in the `zservice` package (see docs/web-ui-plan.md section 17); import from
there, never from this module. It only loads the environment and builds the app.
"""

from zservice import bootstrap

bootstrap.load_env()  # before any Settings class reads the environment

from zservice.app import create_app  # noqa: E402

app = create_app()
