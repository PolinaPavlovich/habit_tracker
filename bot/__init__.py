"""Telegram bot client for the habit tracker API.

This package talks to the FastAPI backend over HTTP only. It must never import
from ``app`` or open a database connection of its own.
"""
