from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.iqs_routes import router as iqs_router
from backend.app.api.pendencias_routes import router as pendencias_router
from backend.app.api.filas_routes import router as filas_router
from backend.app.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="ADMStoIQS API",
        description="API local para processamento, consulta, governança e exportação ADMStoIQS.",
        version="0.7.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    def root() -> dict[str, str]:
        return {"status": "ok", "app": "ADMStoIQS API"}

    app.include_router(router)
app.include_router(iqs_router)
app.include_router(pendencias_router)
app.include_router(filas_router)

    return app


app = create_app()
