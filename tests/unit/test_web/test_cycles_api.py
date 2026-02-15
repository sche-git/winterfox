from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from winterfox.web.api import cycles
from winterfox.web.models.api_models import ActiveCycleResponse, RunCycleResponse
from winterfox.web.services.cycle_runner import CycleAlreadyRunningError


class _FakeRunner:
    def __init__(self):
        self.last_request = None

    async def start_cycle(self, request):
        self.last_request = request
        return RunCycleResponse(
            cycle_id=12,
            status="running",
            started_at=datetime.now(UTC),
        )

    async def get_active_cycle(self):
        return ActiveCycleResponse(
            cycle_id=12,
            status="running",
            focus_node_id="node-1",
            current_step="synthesis",
            progress_percent=60,
        )


def _build_client(fake_runner):
    app = FastAPI()
    cycles._cycle_runner = fake_runner
    app.include_router(cycles.router, prefix="/api/cycles")
    return TestClient(app)


def test_run_cycle_returns_accepted():
    fake_runner = _FakeRunner()
    client = _build_client(fake_runner)

    response = client.post(
        "/api/cycles",
        json={"target_node_id": "abc", "cycle_instruction": "Focus on demand signals"},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["cycle_id"] == 12
    assert body["status"] == "running"
    assert fake_runner.last_request.target_node_id == "abc"
    assert fake_runner.last_request.cycle_instruction == "Focus on demand signals"


def test_run_cycle_returns_conflict_when_active():
    class _BusyRunner(_FakeRunner):
        async def start_cycle(self, request):  # noqa: ARG002
            raise CycleAlreadyRunningError(cycle_id=7)

    client = _build_client(_BusyRunner())

    response = client.post("/api/cycles", json={})

    assert response.status_code == 409
    body = response.json()
    assert body["detail"]["active_cycle_id"] == 7


def test_get_active_cycle_returns_runner_state():
    client = _build_client(_FakeRunner())

    response = client.get("/api/cycles/active")

    assert response.status_code == 200
    assert response.json() == {
        "cycle_id": 12,
        "status": "running",
        "focus_node_id": "node-1",
        "current_step": "synthesis",
        "progress_percent": 60,
    }
