import io
import cv2
import numpy as np
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_full_analyze_and_correct_pipeline():
    # 1. Create a dummy synthetic meal image (500x500 RGB)
    img = Image.new("RGB", (500, 500), color=(120, 90, 60))
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="JPEG")
    img_bytes = img_byte_arr.getvalue()

    # 2. Call POST /food/analyze
    files = {"image": ("test_thali.jpg", img_bytes, "image/jpeg")}
    response = client.post("/v1/food/analyze", files=files)
    assert response.status_code == 200
    data = response.json()

    assert "analysis_id" in data
    assert "model_versions" in data
    assert len(data["items"]) >= 1
    assert data["totals"]["energy_kcal"]["value"] > 0

    analysis_id = data["analysis_id"]
    item0 = data["items"][0]

    # 3. Test correction flow: POST /food/correct
    correction_payload = {
        "analysis_id": analysis_id,
        "events": [
            {
                "type": "quantity_changed",
                "item_id": item0["item_id"],
                "from": {"grams": item0["portion"]["grams"]},
                "to": {"grams": 200.0},
            }
        ],
    }
    corr_response = client.post("/v1/food/correct", json=correction_payload)
    assert corr_response.status_code == 201
    corr_data = corr_response.json()
    assert "correction_batch_id" in corr_data
    assert "recalculated" in corr_data

    # 4. Save confirmed meal: POST /meals
    meal_items = [
        {
            "food_id": item["food"]["food_id"],
            "variant_id": item["food"]["variant_id"],
            "grams": item["portion"]["grams"],
            "unit": item["portion"]["unit"]["unit"],
            "unit_qty": item["portion"]["unit"]["qty"],
            "source": "user_corrected",
            "item_key": item["item_id"],
        }
        for item in corr_data["recalculated"]["items"]
    ]

    meal_payload = {
        "analysis_id": analysis_id,
        "meal_type": "lunch",
        "items": meal_items,
        "notes": "Verified Indian Thali lunch",
    }
    save_resp = client.post("/v1/meals", json=meal_payload)
    assert save_resp.status_code == 201
    meal_obj = save_resp.json()
    assert meal_obj["meal_type"] == "lunch"
    assert len(meal_obj["items"]) == len(meal_items)

def test_indian_thali_cv_pixel_recognition():
    """
    Tests live computer vision recognition on image pixels:
    Generates a 4-item Indian thali (Paneer Butter Masala, Dal Tadka, Paratha, Rice)
    and verifies that the detector, crop classifier, and resolver correctly identify each item.
    """
    thali = np.full((600, 600, 3), (30, 30, 30), dtype=np.uint8)

    # Q1: Paneer Butter Masala (Orange-Red BGR: B=20, G=70, R=210)
    cv2.circle(thali, (180, 180), 90, (20, 70, 210), -1)

    # Q2: Yellow Dal Tadka (Yellow BGR: B=30, G=190, R=220)
    cv2.circle(thali, (420, 180), 90, (30, 190, 220), -1)

    # Q3: Roti/Paratha (Wheat tan BGR: B=110, G=150, R=185) with spots
    cv2.circle(thali, (180, 420), 100, (110, 150, 185), -1)
    for _ in range(25):
        rx, ry = np.random.randint(120, 240), np.random.randint(360, 480)
        cv2.circle(thali, (rx, ry), 4, (40, 50, 80), -1)

    # Q4: Steamed Basmati Rice (White/Cream BGR: B=230, G=235, R=240)
    cv2.circle(thali, (420, 420), 95, (230, 235, 240), -1)

    _, enc = cv2.imencode(".jpg", thali)
    files = {"image": ("thali_pixel_test.jpg", enc.tobytes(), "image/jpeg")}
    response = client.post("/v1/food/analyze", files=files)
    assert response.status_code == 200

    data = response.json()
    assert len(data["items"]) == 4

    detected_foods = {it["food"]["food_id"] for it in data["items"]}
    # Verify that all 4 canonical foods were identified from pixel features
    assert "paneer_butter_masala" in detected_foods
    assert "dal_tadka" in detected_foods
    assert "basmati_rice_steamed" in detected_foods
    assert any("roti" in f or "paratha" in f for f in detected_foods)
