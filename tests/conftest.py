"""Shared pytest fixtures."""
import pytest


@pytest.fixture(autouse=True)
def offline_weather(monkeypatch):
    """Stub the home page's weather lookup so no test calls Open-Meteo; a test can patch it again to show weather."""
    monkeypatch.setattr("app.dashboard.fetch_weather", lambda: None)
