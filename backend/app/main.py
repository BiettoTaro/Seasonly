from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.router import api_router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, debug=settings.app_debug)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.app_trusted_hosts)
    if settings.app_force_https:
        app.add_middleware(HTTPSRedirectMiddleware)
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
