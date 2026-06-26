import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import main


class StubRedisClient:
    async def connect(self):
        return None

    async def disconnect(self):
        return None

    async def warm_up_cache(self):
        return None

    async def health_check(self):
        return True

    async def search_jobs(self, **kwargs):
        return []

    async def get_all_jobs(self, **kwargs):
        return []

    async def get_jobs_by_company(self, **kwargs):
        return []

    async def get_job(self, job_id: str):
        return None

    async def get_detailed_stats(self):
        return {"total_jobs": 0}


@pytest.fixture
def client(monkeypatch):
    async def fake_connect():
        return None

    async def fake_init_db():
        return None

    async def fake_disconnect():
        return None

    monkeypatch.setattr(main.db_client, "connect", fake_connect)
    monkeypatch.setattr(main.db_client, "init_db", fake_init_db)
    monkeypatch.setattr(main.db_client, "disconnect", fake_disconnect)
    monkeypatch.setattr(main, "redis_client", StubRedisClient())

    with TestClient(main.app) as test_client:
        yield test_client


def test_health_reports_database_status(client):
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database"] == "connected"
    assert "redis" not in payload
