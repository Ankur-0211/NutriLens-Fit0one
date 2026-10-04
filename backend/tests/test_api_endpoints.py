import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health_endpoints():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data

    ready_resp = client.get("/v1/ready")
    assert ready_resp.status_code == 200
    rdata = ready_resp.json()
    assert rdata["status"] == "ready"
    assert rdata["database"] == "connected"

def test_food_search():
    response = client.get("/v1/food/search?q=roti")
    assert response.status_code == 200
    items = response.json()
    assert len(items) > 0
    assert any("roti" in i["food_id"] for i in items)

def test_nutrition_calculate():
    payload = {
        "items": [
            {"food_id": "roti_plain", "quantity": 2, "unit": "roti"},
            {"food_id": "dal_tadka", "quantity": 1, "unit": "katori"},
        ]
    }
    response = client.post("/v1/nutrition/calculate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["totals"]["energy_kcal"]["value"] > 0
    assert data["totals"]["protein_g"]["value"] > 0

def test_meal_logging_and_daily_summary():
    payload = {
        "meal_type": "lunch",
        "items": [
            {"food_id": "roti_plain", "grams": 70, "unit": "roti", "unit_qty": 2},
            {"food_id": "paneer_butter_masala", "grams": 150, "unit": "katori", "unit_qty": 1},
        ],
        "notes": "Testing meal persist",
    }
    response = client.post("/v1/meals", json=payload)
    assert response.status_code == 201
    meal = response.json()
    assert meal["meal_type"] == "lunch"
    assert len(meal["items"]) == 2

    # Check daily summary
    summary_resp = client.get("/v1/nutrition/daily")
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["totals"]["energy_kcal"]["value"] >= meal["totals"]["energy_kcal"]["value"]
    assert "lunch" in summary["by_meal"]
    assert summary["by_meal"]["lunch"]["items_count"] >= 2
