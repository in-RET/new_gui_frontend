from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.responses import JSONResponse

from .admin.router import admin_router
from .constants import create_db_and_tables
from .projects.router import projects_router
from .users.router import users_router


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    # startup event
    # create db and tables
    create_db_and_tables()

    # TODO: Befüllen der Komponentendatenbank zum Start der Anwendung, wenn diese nicht bestehen.
    yield
    # shutdown events

app = FastAPI(lifespan=lifespan)

# including api routers
app.include_router(
    router=users_router
)
app.include_router(
    router=admin_router,
)

app.include_router(
    router=projects_router
)


@app.get("/")
async def root():
    return JSONResponse(
        content={"message": "Hello World"},
        status_code=200,
    )

