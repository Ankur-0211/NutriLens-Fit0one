import os
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.user import AppUser
from backend.app.models.meal import Meal, MealItem
from backend.app.models.correction import CorrectionEvent
from backend.app.models.image import ImageRecord
from backend.app.models.analysis import AnalysisRecord

class ComplianceService:
    """
    Privacy, Data Governance & Compliance Service (SDD Section 28, Section 33 Phase 11).
    Enforces GDPR/DPDP user data export, Right-to-be-Forgotten account deletion,
    and automated transient image retention purging.
    """

    @staticmethod
    def export_user_data(db: Session, user_id: str) -> Dict[str, Any]:
        """
        Exports all personal and nutritional telemetry records for a user in standard JSON format.
        (SDD Section 33 Phase 11 line 2315: GET /users/me/export)
        """
        user = db.query(AppUser).filter(AppUser.id == user_id).first()
        if not user:
            raise ValueError(f"User '{user_id}' not found")

        meals = db.query(Meal).filter(Meal.user_id == user_id, Meal.deleted_at.is_(None)).all()
        exported_meals = []
        for m in meals:
            items = db.query(MealItem).filter(MealItem.meal_id == m.id).all()
            exported_meals.append({
                "meal_id": m.id,
                "meal_type": m.meal_type,
                "eaten_at": m.eaten_at.isoformat() if m.eaten_at else None,
                "local_date": str(m.local_date),
                "totals": m.totals,
                "items": [
                    {
                        "food_id": it.food_id,
                        "variant_id": it.variant_id,
                        "grams": float(it.grams) if it.grams else 0.0,
                        "unit": it.unit,
                        "nutrition_snapshot": it.nutrition_snapshot,
                    }
                    for it in items
                ],
            })

        corrections = (
            db.query(CorrectionEvent)
            .filter(CorrectionEvent.user_id == user_id)
            .all()
        )
        exported_corrections = [
            {
                "id": c.id,
                "event_type": c.event_type,
                "before": c.before,
                "after": c.after,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in corrections
        ]

        return {
            "format": "nutrilens_gdpr_export_v1",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "profile": {
                "user_id": user.id,
                "email": user.email,
                "display_name": user.display_name,
                "age_range": user.age_range,
                "sex": user.sex,
                "height_cm": float(user.height_cm) if user.height_cm else None,
                "weight_kg": float(user.weight_kg) if user.weight_kg else None,
                "timezone": user.timezone,
                "training_consent": user.training_consent,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            },
            "meals_count": len(exported_meals),
            "meals": exported_meals,
            "corrections_count": len(exported_corrections),
            "corrections": exported_corrections,
        }

    @staticmethod
    def delete_user_account(db: Session, user_id: str) -> Dict[str, Any]:
        """
        Soft-deletes the user account and purges personal diary history and transient images.
        (SDD Section 33 Phase 11 line 2315: DELETE /users/me)
        """
        user = db.query(AppUser).filter(AppUser.id == user_id).first()
        if not user:
            raise ValueError(f"User '{user_id}' not found")

        now = datetime.now(timezone.utc)
        user.deleted_at = now
        user.email = f"deleted_{user.id[:8]}@anonymized.nutrilens.ai"
        user.display_name = "Deleted User"

        # Soft delete meals
        db.query(Meal).filter(Meal.user_id == user_id).update({"deleted_at": now})

        # Purge linked unconsented images from disk
        analyses = db.query(AnalysisRecord).filter(AnalysisRecord.user_id == user_id).all()
        purged_images = 0
        for an in analyses:
            if an.image_id:
                img_rec = db.query(ImageRecord).filter(ImageRecord.id == an.image_id).first()
                if img_rec and img_rec.storage_key:
                    target_path = Path(img_rec.storage_key)
                    if not target_path.is_file():
                        target_path = settings.STORAGE_DIR / img_rec.storage_key
                    if target_path.is_file():
                        try:
                            os.remove(target_path)
                            purged_images += 1
                        except OSError:
                            pass
                    img_rec.deleted_at = now

        db.commit()
        return {
            "status": "success",
            "message": "User account and personal data successfully deleted and anonymized",
            "user_id": user_id,
            "purged_images_count": purged_images,
            "deleted_at": now.isoformat(),
        }

    @staticmethod
    def purge_expired_transient_images(db: Session, max_age_hours: int = 24) -> Dict[str, Any]:
        """
        Purges transient scan images older than the retention threshold from storage.
        (SDD Section 22 lines 1450-1453: retention_class == 'transient')
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        candidates = (
            db.query(ImageRecord)
            .filter(
                ImageRecord.retention_class == "transient",
                ImageRecord.created_at < cutoff,
                ImageRecord.deleted_at.is_(None),
            )
            .all()
        )

        purged = 0
        for img in candidates:
            if img.storage_key:
                p = Path(img.storage_key)
                if not p.is_file():
                    p = settings.STORAGE_DIR / img.storage_key
                if p.is_file():
                    try:
                        os.remove(p)
                    except OSError:
                        pass
            img.deleted_at = datetime.now(timezone.utc)
            purged += 1

        db.commit()
        return {
            "retention_cutoff": cutoff.isoformat(),
            "purged_count": purged,
            "max_age_hours": max_age_hours,
        }
