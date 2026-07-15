from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.db.session import get_db_session
from app.main import create_app


def test_health_check() -> None:
    app = create_app()
    session = AsyncMock()

    async def override_session() -> AsyncGenerator[AsyncMock, None]:
        yield session

    app.dependency_overrides[get_db_session] = override_session
    client = TestClient(app)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    session.execute.assert_awaited_once()
