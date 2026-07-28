from geoflow_worker.tasks import ping


def test_ping_task() -> None:
    assert ping.run() == {"status": "ok", "service": "geoflow-worker"}

