import io
import uuid
from datetime import date
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.core.security import create_access_token
from backend.app.core.rate_limit import InMemoryRateLimiter, rate_limiter
from backend.app.models.user import AppUser
from backend.app.models.meal import Meal, MealItem
from backend.app.models.correction import CorrectionEvent
from backend.app.models.image import ImageRecord
from backend.app.modules.compliance.service import ComplianceService

client = TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_rate_limiter_unit():
    limiter = InMemoryRateLimiter()
    key = f"test_user_{uuid.uuid4().hex[:6]}"

    # Allowed 3 requests in 60s
    ok1, rem1, _ = limiter.is_allowed(key, limit=3, window_seconds=60)
    assert ok1 is True
    assert rem1 == 2

    ok2, rem2, _ = limiter.is_allowed(key, limit=3, window_seconds=60)
    assert ok2 is True
    assert rem2 == 1

    ok3, rem3, _ = limiter.is_allowed(key, limit=3, window_seconds=60)
    assert ok3 is True
    assert rem3 == 0

    # 4th request exceeds limit
    ok4, rem4, reset4 = limiter.is_allowed(key, limit=3, window_seconds=60)
    assert ok4 is False
    assert rem4 == 0
    assert reset4 > 0

def test_rate_limit_headers_on_analyze():
    # Call /v1/food/analyze with small image
    img = Image.new("RGB", (320, 320), color=(200, 100, 50))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)

    # Use unique user ID header to avoid tripping from other tests
    headers = {"X-User-ID": f"user_test_{uuid.uuid4().hex[:6]}"}
    res = client.post(
        "/v1/food/analyze",
        files={"image": ("meal.jpg", buf.getvalue(), "image/jpeg")},
        headers=headers,
    )
    assert res.status_code == 200
    assert "X-RateLimit-Limit" in res.headers
    assert res.headers["X-RateLimit-Limit"] == "30"
    assert "X-RateLimit-Remaining" in res.headers
    assert "X-RateLimit-Reset" in res.headers
    assert "X-Request-ID" in res.headers

def test_user_data_export_and_deletion(db_session):
    # Setup test user
    uid = str(uuid.uuid4())
    user = AppUser(
        id=uid,
        email=f"export_{uuid.uuid4().hex[:6]}@example.com",
        display_name="Export Tester",
        training_consent=True,
    )
    db_session.add(user)

    # Add a meal
    meal = Meal(
        id=str(uuid.uuid4()),
        user_id=uid,
        meal_type="dinner",
        local_date=date(2026, 10, 4),
        totals={"energy_kcal": {"value": 520.0}},
    )
    db_session.add(meal)
    db_session.commit()

    # 1. Test Data Export (GDPR Portability)
    exported = ComplianceService.export_user_data(db_session, uid)
    assert exported["format"] == "nutrilens_gdpr_export_v1"
    assert exported["profile"]["email"] == user.email
    assert exported["meals_count"] == 1
    assert exported["meals"][0]["meal_type"] == "dinner"

    # Test export API with header
    token = create_access_token({"sub": uid})
    headers = {"Authorization": f"Bearer {token}", "X-User-ID": uid}
    res_export = client.get("/v1/users/me/export", headers=headers)
    assert res_export.status_code == 200
    assert res_export.json()["meals_count"] >= 1

    # 2. Test Account Deletion (Right to be Forgotten)
    del_res = client.delete("/v1/users/me", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "success"

    # Verify user is anonymized and soft-deleted
    db_session.refresh(user)
    assert user.deleted_at is not None
    assert "deleted_" in user.email

def test_retention_purge(db_session):
    res = client.post("/v1/admin/compliance/retention-purge?max_age_hours=12")
    assert res.status_code == 200
    data = res.json()
    assert "purged_count" in data
    assert data["max_age_hours"] == 12

def test_prometheus_and_json_metrics():
    # JSON format
    res_json = client.get("/v1/metrics?format=json")
    assert res_json.status_code == 200
    jdata = res_json.json()
    assert jdata["status"] == "healthy"
    assert "telemetry" in jdata
    assert "users_active" in jdata["telemetry"]

    # Prometheus text format
    res_prom = client.get("/v1/metrics?format=prometheus")
    assert res_prom.status_code == 200
    text = res_prom.text
    assert "# HELP nutrilens_users_total" in text
    assert "# TYPE nutrilens_meals_total counter" in text
    assert "nutrilens_scans_total" in text
