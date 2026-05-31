from fastapi.testclient import TestClient

from app.main import create_app


def test_list_data_registrations() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/data/registrations")

    assert response.status_code == 200
    assert {item["metadata"]["data_key"] for item in response.json()} == {
        "eu_seasonal_produce",
        "eu_recipes",
        "recommendation_events",
    }


def test_read_data_targets() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/data/targets/eu_recipes")

    assert response.status_code == 200
    assert response.json()["data_key"] == "eu_recipes"
    assert len(response.json()["targets"]) == 2
