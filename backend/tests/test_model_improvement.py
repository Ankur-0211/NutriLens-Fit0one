import os
import uuid
import tempfile
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.user import AppUser
from backend.app.models.image import ImageRecord
from backend.app.models.analysis import AnalysisRecord
from backend.app.models.correction import CorrectionEvent
from backend.app.models.improvement import ModelVersion, DatasetVersion, DatasetSample, FeedbackReview
from backend.app.modules.improvement.validators import (
    validate_image_decodable,
    compute_dhash,
    hamming_distance,
    check_duplicate_or_leakage,
    validate_correction_plausibility,
    classify_correction_cause,
)
from backend.app.modules.improvement.service import ModelImprovementService

client = TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_automated_validators(db_session):
    # 1. Image Decodability
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        img_path = f.name
        img = Image.new("RGB", (128, 128), color=(200, 100, 50))
        img.save(img_path)

    try:
        valid, err, w, h = validate_image_decodable(img_path)
        assert valid is True
        assert w == 128 and h == 128
        assert err is None

        # Corrupted / non-existent file
        valid_bad, err_bad, _, _ = validate_image_decodable("non_existent_file.jpg")
        assert valid_bad is False
        assert err_bad is not None
    finally:
        if os.path.exists(img_path):
            os.remove(img_path)

    # 2. Perceptual dHash & Hamming distance
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f1:
        path1 = f1.name
        Image.new("RGB", (100, 100), color=(255, 0, 0)).save(path1)

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f2:
        path2 = f2.name
        Image.new("RGB", (100, 100), color=(0, 255, 0)).save(path2)

    try:
        h1 = compute_dhash(path1)
        h2 = compute_dhash(path2)
        assert len(h1) == 16
        assert hamming_distance(h1, h1) == 0

        # Check leakage guard
        frozen_hashes = [h1]
        violates, vtype, _ = check_duplicate_or_leakage(h1, existing_hashes=[], frozen_test_hashes=frozen_hashes)
        assert violates is True
        assert vtype == "leakage_violation"
    finally:
        if os.path.exists(path1): os.remove(path1)
        if os.path.exists(path2): os.remove(path2)

    # 3. Plausibility validation
    ok_plaus, _ = validate_correction_plausibility("quantity_changed", {}, {"portion_g": 150.0}, db_session)
    assert ok_plaus is True

    bad_plaus_qty, err_qty = validate_correction_plausibility("quantity_changed", {}, {"portion_g": 4000.0}, db_session)
    assert bad_plaus_qty is False
    assert "Implausibly large" in err_qty

    bad_plaus_food, err_food = validate_correction_plausibility("food_changed", {}, {"food_id": "alien_space_food_xyz"}, db_session)
    assert bad_plaus_food is False
    assert "not found" in err_food

    # 4. Cause classification
    cause_var = classify_correction_cause("variant_changed", {"variant_id": "a"}, {"variant_id": "b"})
    assert cause_var == "variant_ambiguity"

    cause_qty = classify_correction_cause("quantity_changed", {"portion_g": 100}, {"portion_g": 200})
    assert cause_qty == "portion_bias"

def test_feedback_etl_pipeline(db_session):
    # Setup test user with training consent = False
    no_consent_user = AppUser(
        id=str(uuid.uuid4()),
        email=f"noconsent_{uuid.uuid4().hex[:6]}@example.com",
        display_name="Private User",
        training_consent=False,
    )
    db_session.add(no_consent_user)

    # Setup test user with training consent = True
    consenting_user = AppUser(
        id=str(uuid.uuid4()),
        email=f"consent_{uuid.uuid4().hex[:6]}@example.com",
        display_name="Consenting User",
        training_consent=True,
    )
    db_session.add(consenting_user)

    # Analysis record
    analysis = AnalysisRecord(
        id=str(uuid.uuid4()),
        user_id=consenting_user.id,
        model_versions={"classifier": "cls-0.5.0"},
    )
    db_session.add(analysis)
    db_session.commit()

    # Event 1: No consent -> should become consent_declined
    ev_no_consent = CorrectionEvent(
        id=str(uuid.uuid4()),
        batch_id=str(uuid.uuid4()),
        analysis_id=analysis.id,
        user_id=no_consent_user.id,
        item_key="item_0",
        event_type="quantity_changed",
        before={"portion_g": 100},
        after={"portion_g": 150},
        review_status="pending",
    )
    db_session.add(ev_no_consent)

    # Event 2: Consenting user, valid correction -> should become queued
    ev_consent = CorrectionEvent(
        id=str(uuid.uuid4()),
        batch_id=str(uuid.uuid4()),
        analysis_id=analysis.id,
        user_id=consenting_user.id,
        item_key="item_0",
        event_type="variant_changed",
        before={"variant_id": "roti_plain:default"},
        after={"variant_id": "roti_plain:with_ghee"},
        review_status="pending",
    )
    db_session.add(ev_consent)

    # Event 3: Consenting user, but implausible quantity -> should become auto_rejected
    ev_bad_qty = CorrectionEvent(
        id=str(uuid.uuid4()),
        batch_id=str(uuid.uuid4()),
        analysis_id=analysis.id,
        user_id=consenting_user.id,
        item_key="item_0",
        event_type="quantity_changed",
        before={"portion_g": 100},
        after={"portion_g": 9999.0},
        review_status="pending",
    )
    db_session.add(ev_bad_qty)
    db_session.commit()

    # Run ETL via API endpoint
    res = client.post("/v1/admin/feedback/etl")
    assert res.status_code == 200
    summary = res.json()["summary"]
    assert summary["processed"] >= 3

    # Verify statuses
    db_session.refresh(ev_no_consent)
    db_session.refresh(ev_consent)
    db_session.refresh(ev_bad_qty)

    assert ev_no_consent.review_status == "consent_declined"
    assert ev_consent.review_status == "queued"
    assert ev_bad_qty.review_status == "auto_rejected"

def test_reviewer_decision_and_dataset_snapshot(db_session):
    # 1. Fetch pending reviews
    res_list = client.get("/v1/admin/feedback/pending")
    assert res_list.status_code == 200
    data = res_list.json()
    assert "items" in data

    # 2. Pick a queued event or create one
    ev = db_session.query(CorrectionEvent).filter(CorrectionEvent.review_status == "queued").first()
    if not ev:
        analysis = AnalysisRecord(id=str(uuid.uuid4()), model_versions={"classifier": "cls-0.5.0"})
        db_session.add(analysis)
        ev = CorrectionEvent(
            id=str(uuid.uuid4()),
            batch_id=str(uuid.uuid4()),
            analysis_id=analysis.id,
            item_key="item_0",
            event_type="variant_changed",
            before={"variant_id": "dal_tadka:default"},
            after={"variant_id": "dal_tadka:restaurant_rich"},
            review_status="queued",
        )
        db_session.add(ev)
        db_session.commit()

    # Submit human reviewer decision
    res_rev = client.post("/v1/admin/feedback/review", json={
        "correction_id": ev.id,
        "decision": "accepted",
        "cause": "variant_ambiguity",
        "notes": "Verified homestyle dal portion was restaurant preparation with extra tadka butter",
    })
    assert res_rev.status_code == 200
    assert res_rev.json()["decision"] == "accepted"

    db_session.refresh(ev)
    assert ev.review_status == "accepted"

    # 3. Build versioned dataset snapshot from accepted reviews
    v_id = f"ds-test-{uuid.uuid4().hex[:6]}"
    res_ds = client.post("/v1/admin/datasets/build", json={
        "version_id": v_id,
        "notes": "Test dataset snapshot from reviewed corrections",
    })
    assert res_ds.status_code == 200
    ds_data = res_ds.json()["dataset"]
    assert ds_data["dataset_version"] == v_id
    assert ds_data["total_samples"] >= 1

    # Check list datasets
    res_all_ds = client.get("/v1/admin/datasets")
    assert res_all_ds.status_code == 200
    assert any(d["id"] == v_id for d in res_all_ds.json()["datasets"])

def test_model_registry_lifecycle_and_rollback(db_session):
    # 1. Verify baseline models exist
    res_models = client.get("/v1/admin/models")
    assert res_models.status_code == 200
    models = res_models.json()["models"]
    assert any(m["id"] == "cls-0.5.0" and m["stage"] == "production" for m in models)

    # 2. Register candidate model in staging
    cand_id = f"cls-cand-{uuid.uuid4().hex[:4]}"
    cand_model = ModelVersion(
        id=cand_id,
        kind="classifier",
        stage="staging",
        labelset_version="vis-2026.01",
        metrics={"top1": 0.91, "top3": 0.98, "ece": 0.05},
        notes="Challenger model trained on reviewed feedback samples",
    )
    db_session.add(cand_model)
    db_session.commit()

    # 3. Transition to canary (25% traffic)
    res_canary = client.post("/v1/admin/models/stage", json={
        "model_id": cand_id,
        "target_stage": "canary",
        "traffic_pct": 25.0,
    })
    assert res_canary.status_code == 200
    assert res_canary.json()["model"]["stage"] == "canary"
    assert res_canary.json()["model"]["active_traffic_pct"] == 25.0

    # 4. Promote candidate to production
    res_prod = client.post("/v1/admin/models/stage", json={
        "model_id": cand_id,
        "target_stage": "production",
    })
    assert res_prod.status_code == 200
    assert res_prod.json()["model"]["stage"] == "production"
    assert res_prod.json()["model"]["active_traffic_pct"] == 100.0

    # Verify previous cls-0.5.0 was demoted to archived
    old_prod = db_session.query(ModelVersion).filter(ModelVersion.id == "cls-0.5.0").first()
    assert old_prod.stage == "archived"

    # 5. Rollback drill: Restore cls-0.5.0 back to production
    res_rollback = client.post("/v1/admin/models/stage", json={
        "model_id": "cls-0.5.0",
        "target_stage": "production",
    })
    assert res_rollback.status_code == 200
    assert res_rollback.json()["model"]["stage"] == "production"

    db_session.refresh(cand_model)
    assert cand_model.stage == "archived"

def test_non_retraining_identity_map_update(db_session):
    # Test ADR-009 / SDD 23.5 online weight adjustment
    res = client.post("/v1/admin/identity-map/update", json={
        "visual_class_id": "yellow_dal",
        "food_variant_id": "dal_tadka:restaurant_rich",
        "weight": 0.35,
        "is_default": False,
    })
    assert res.status_code == 200
    data = res.json()["mapping"]
    assert data["visual_class_id"] == "yellow_dal"
    assert data["food_variant_id"] == "dal_tadka:restaurant_rich"
    assert data["weight"] == 0.35

def test_error_analytics(db_session):
    res = client.get("/v1/admin/analytics/errors")
    assert res.status_code == 200
    data = res.json()["analytics"]
    assert "review_status_breakdown" in data
    assert "correction_type_breakdown" in data
    assert "top_confusion_pairs" in data
    assert "portion_bias_mean_pct_error" in data

def test_user_training_consent_endpoint(db_session):
    # Register/login a user
    email = f"consent_user_{uuid.uuid4().hex[:6]}@example.com"
    reg_res = client.post("/v1/auth/register", json={
        "email": email,
        "password": "Password123!",
        "display_name": "Consent Tester",
    })
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Toggle consent to true
    res = client.patch(
        "/v1/users/me/consent",
        json={"training_consent": True},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["training_consent"] is True

    # Toggle consent to false
    res_false = client.patch(
        "/v1/users/me/consent",
        json={"training_consent": False},
        headers=headers,
    )
    assert res_false.status_code == 200
    assert res_false.json()["training_consent"] is False
