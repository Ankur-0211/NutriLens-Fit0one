import pytest
from backend.app.core.database import SessionLocal
from backend.app.modules.identity_resolution.resolver import FoodIdentityResolver

def test_identity_resolver_paneer_red_gravy():
    db = SessionLocal()
    try:
        resolver = FoodIdentityResolver(db)
        res = resolver.resolve("paneer_red_gravy", visual_score=0.92)

        # Classifier outputs visual class; resolver maps to canonical food
        assert res.food_id == "paneer_butter_masala"
        assert res.variant_id == "paneer_butter_masala:default"
        assert res.name == "Paneer Butter Masala"
        # Should detect variant ambiguity and provide home_light alternative
        assert res.identity.ambiguity in ["variant", "food"]
        assert len(res.identity.variant_alternatives) >= 1
        assert any(v.variant_id == "paneer_butter_masala:home_light" for v in res.identity.variant_alternatives)
    finally:
        db.close()

def test_identity_resolver_yellow_dal():
    db = SessionLocal()
    try:
        resolver = FoodIdentityResolver(db)
        res = resolver.resolve("yellow_dal", visual_score=0.90)

        assert res.food_id == "dal_tadka"
        assert res.variant_id == "dal_tadka:default"
        assert res.name == "Dal Tadka"
    finally:
        db.close()
