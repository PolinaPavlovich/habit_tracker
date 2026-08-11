"""Aggregate router mounted by the application."""

from fastapi import APIRouter

from app.api.routers import activities, logs

api_router = APIRouter()
api_router.include_router(activities.router)
api_router.include_router(logs.router)
