from fastapi import FastAPI
import routes.team_routes as team_routes
import routes.score_routes as score_routes
import routes.display_routes as display_routes
import routes.schedule_routes as schedule_routes
from fastapi.middleware.cors import CORSMiddleware

from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="FLL Scoreboard API",
        version="1.0.0",
        description="API for managing FLL team scores and display.",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app = FastAPI()
app.include_router(team_routes.router, prefix="/team", tags=["Teams"])
app.include_router(score_routes.router, prefix="/score", tags=["Scores"])
app.include_router(display_routes.router, prefix="/display", tags=["Display"])
app.include_router(schedule_routes.router, prefix="/schedule", tags=["Schedule"])

app.route("/")(lambda: {"message": "Welcome to the FLL Scoreboard API"})

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.openapi = custom_openapi

