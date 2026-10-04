import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.models.analysis import AnalysisRecord, PredictionItem
from backend.app.models.correction import CorrectionEvent
from backend.app.modules.nutrition.engine import NutritionEngine
from backend.app.modules.nutrition.repository import FoodRepository
from backend.app.schemas.correction import CorrectionRequest, CorrectionResponse
from backend.app.schemas.analysis import AnalysisResponse, AnalysisItem, RegionSchema, FoodIdentityResult, PortionResult, PortionUnit, ConfidenceInfo, VisualInfo, IdentityInfo, ImageQualityInfo
from backend.app.core.config import settings
from backend.app.core.errors import NutriLensException

class CorrectionService:
    def __init__(self, db: Session):
        self.db = db
        self.food_repo = FoodRepository(db)
        self.engine = NutritionEngine()

    def apply_corrections(self, payload: CorrectionRequest, user_id: str = None) -> CorrectionResponse:
        analysis = self.db.query(AnalysisRecord).filter(AnalysisRecord.id == payload.analysis_id).first()
        if not analysis:
            raise NutriLensException(
                status_code=404,
                code="ANALYSIS_NOT_FOUND",
                message=f"Analysis with ID '{payload.analysis_id}' was not found",
            )

        batch_id = f"cb_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        # 1. Store all events
        for ev in payload.events:
            event_rec = CorrectionEvent(
                id=str(uuid.uuid4()),
                batch_id=batch_id,
                analysis_id=payload.analysis_id,
                user_id=user_id,
                item_key=ev.item_id,
                event_type=ev.type,
                before=ev.from_,
                after=ev.to or {"food_id": ev.food_id, "variant_id": ev.variant_id, "grams": ev.grams, "quantity": ev.quantity, "unit": ev.unit},
                client_ts=now,
                review_status="pending",
            )
            self.db.add(event_rec)

        self.db.commit()

        # 2. Reconstruct items state and recalculate
        prediction_items = self.db.query(PredictionItem).filter(PredictionItem.analysis_id == payload.analysis_id).all()
        items_map: Dict[str, Dict[str, Any]] = {}
        for p in prediction_items:
            items_map[p.item_key] = {
                "item_id": p.item_key,
                "bbox": p.bbox or [0.1, 0.1, 0.5, 0.5],
                "food_id": p.food_id,
                "variant_id": p.variant_id or f"{p.food_id}:default",
                "grams": float(p.portion_g or 100.0),
                "unit": "katori" if "dal" in (p.food_id or "") else ("roti" if "roti" in (p.food_id or "") else "g"),
                "qty": 1.0,
            }

        # Apply events to items_map
        for ev in payload.events:
            if ev.type == "item_removed" and ev.item_id in items_map:
                del items_map[ev.item_id]
            elif ev.type == "item_added":
                new_key = f"i_add_{uuid.uuid4().hex[:6]}"
                items_map[new_key] = {
                    "item_id": new_key,
                    "bbox": ev.region_hint or [0.3, 0.3, 0.6, 0.6],
                    "food_id": ev.food_id or "roti_plain",
                    "variant_id": ev.variant_id or f"{ev.food_id}:default",
                    "grams": float(ev.grams or 70.0),
                    "unit": ev.unit or "piece",
                    "qty": float(ev.quantity or 1.0),
                }
            elif ev.item_id in items_map:
                it = items_map[ev.item_id]
                if ev.type == "food_changed":
                    new_food = ev.to.get("food_id") if ev.to else ev.food_id
                    if new_food:
                        it["food_id"] = new_food
                        it["variant_id"] = f"{new_food}:default"
                elif ev.type == "variant_changed":
                    new_var = ev.to.get("variant_id") if ev.to else ev.variant_id
                    if new_var:
                        it["variant_id"] = new_var
                elif ev.type == "quantity_changed":
                    new_g = ev.to.get("grams") if ev.to else ev.grams
                    if new_g:
                        it["grams"] = float(new_g)
                elif ev.type == "unit_changed":
                    if ev.unit and ev.quantity:
                        it["grams"] = self.food_repo.convert_to_grams(it["food_id"], float(ev.quantity), ev.unit)
                        it["unit"] = ev.unit
                        it["qty"] = float(ev.quantity)

        # 3. Recalculate nutrition
        recalculated_items: List[AnalysisItem] = []
        items_nutrition = []

        for k, v in items_map.items():
            food_detail = self.food_repo.get_food_detail(v["food_id"])
            variant, profile = self.food_repo.get_variant_profile(v["food_id"], v["variant_id"])

            if profile:
                profile_dict = {
                    "basis_g": float(profile.basis_g),
                    "energy_kcal": float(profile.energy_kcal),
                    "kcal_min": float(profile.kcal_min) if profile.kcal_min else None,
                    "kcal_max": float(profile.kcal_max) if profile.kcal_max else None,
                    "protein_g": float(profile.protein_g),
                    "carbs_g": float(profile.carbs_g),
                    "fat_g": float(profile.fat_g),
                    "fiber_g": float(profile.fiber_g),
                    "sugar_g": float(profile.sugar_g),
                    "sodium_mg": float(profile.sodium_mg),
                    "micros": profile.micros or {},
                }
                nut = self.engine.calculate_item_nutrition(
                    profile=profile_dict,
                    grams=v["grams"],
                    source_name=profile.source_id or "IFCT 2017",
                    confidence_score=0.98,  # User-verified confidence is high!
                )
            else:
                nut = self.engine.calculate_item_nutrition(
                    profile={"energy_kcal": 150.0, "protein_g": 5.0, "carbs_g": 20.0, "fat_g": 5.0},
                    grams=v["grams"],
                    confidence_score=0.9,
                )

            items_nutrition.append(nut)

            food_name = food_detail.display_name if food_detail else v["food_id"].replace("_", " ").title()

            analysis_item = AnalysisItem(
                item_id=v["item_id"],
                region=RegionSchema(bbox=v["bbox"], mask_rle=None),
                food=FoodIdentityResult(
                    visual=VisualInfo(visual_class_id=v["food_id"], score=0.95),
                    food_id=v["food_id"],
                    variant_id=v["variant_id"],
                    name=food_name,
                    identity=IdentityInfo(resolver="idr-0.1.0", ambiguity="none", variant_alternatives=[]),
                    confidence=ConfidenceInfo(level="high", score=0.98),
                    alternatives=[],
                ),
                portion=PortionResult(
                    grams=round(v["grams"], 1),
                    range_g=[round(v["grams"] * 0.9, 1), round(v["grams"] * 1.1, 1)],
                    unit=PortionUnit(unit=v.get("unit", "g"), qty=v.get("qty", 1.0)),
                    confidence=ConfidenceInfo(level="high", score=0.98),
                    method="user_verified",
                ),
                nutrition=nut,
                flags=["user_verified"],
            )
            recalculated_items.append(analysis_item)

        totals = self.engine.aggregate_totals(items_nutrition)

        recalculated_resp = AnalysisResponse(
            schema_version=settings.SCHEMA_VERSION,
            analysis_id=payload.analysis_id,
            image_id=analysis.image_id,
            model_versions=analysis.model_versions,
            image_quality=ImageQualityInfo(score=0.95, warnings=[]),
            items=recalculated_items,
            totals=totals,
            disclaimer="Recalculated with user verified items and quantities.",
        )

        return CorrectionResponse(
            correction_batch_id=batch_id,
            recalculated=recalculated_resp,
        )
