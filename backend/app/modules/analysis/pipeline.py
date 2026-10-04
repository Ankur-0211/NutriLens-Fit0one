import io
import os
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.errors import NutriLensException
from backend.app.models.image import ImageRecord
from backend.app.models.analysis import AnalysisRecord, PredictionItem
from backend.app.modules.recognition.detector import FoodDetector
from backend.app.modules.recognition.classifier import FoodClassifier
from backend.app.modules.identity_resolution.resolver import FoodIdentityResolver
from backend.app.modules.portion.estimator import PortionEstimator
from backend.app.modules.nutrition.engine import NutritionEngine
from backend.app.modules.nutrition.repository import FoodRepository
from backend.app.schemas.analysis import (
    AnalysisResponse,
    AnalysisItem,
    RegionSchema,
    ImageQualityInfo,
    AnalysisMetadata,
)

class AnalysisPipeline:
    def __init__(self, db: Session):
        self.db = db
        self.detector = FoodDetector(model_version=settings.DETECTOR_MODEL_VERSION)
        self.classifier = FoodClassifier(model_version=settings.CLASSIFIER_MODEL_VERSION)
        self.resolver = FoodIdentityResolver(db, identity_map_version=settings.IDENTITY_MAP_VERSION)
        self.portion_estimator = PortionEstimator(model_version=settings.PORTION_MODEL_VERSION)
        self.nutrition_engine = NutritionEngine()
        self.food_repo = FoodRepository(db)

    def validate_and_preprocess_image(self, image_bytes: bytes) -> Tuple[Image.Image, ImageRecord, ImageQualityInfo]:
        if len(image_bytes) > settings.MAX_IMAGE_SIZE_BYTES:
            raise NutriLensException(
                status_code=413,
                code="IMAGE_TOO_LARGE",
                message="Image exceeds maximum permitted size of 8 MB",
                details={"max_bytes": settings.MAX_IMAGE_SIZE_BYTES, "received_bytes": len(image_bytes)},
            )

        try:
            img = Image.open(io.BytesIO(image_bytes))
            img.verify()
            # Reopen after verify
            img = Image.open(io.BytesIO(image_bytes))
        except Exception:
            raise NutriLensException(
                status_code=400,
                code="INVALID_IMAGE",
                message="Image is corrupt or not in a supported decodable format",
            )

        width, height = img.size
        if width < settings.MIN_IMAGE_DIMENSION or height < settings.MIN_IMAGE_DIMENSION:
            raise NutriLensException(
                status_code=422,
                code="LOW_QUALITY_IMAGE",
                message=f"Image dimensions ({width}x{height}) are smaller than minimum allowed ({settings.MIN_IMAGE_DIMENSION}px)",
            )

        # Sanitize and strip EXIF
        clean_img = Image.new("RGB", img.size)
        clean_img.paste(img.convert("RGB"))

        sha256 = hashlib.sha256(image_bytes).hexdigest()
        image_id = str(uuid.uuid4())
        filename = f"{image_id}.jpg"
        save_path = settings.STORAGE_DIR / filename
        clean_img.save(save_path, "JPEG", quality=85)

        img_record = ImageRecord(
            id=image_id,
            storage_key=str(save_path),
            sha256=sha256,
            width=width,
            height=height,
            bytes=len(image_bytes),
            retention_class="transient",
        )
        self.db.add(img_record)
        self.db.commit()
        self.db.refresh(img_record)

        quality = ImageQualityInfo(score=0.92, warnings=[])
        return clean_img, img_record, quality

    def run_pipeline(
        self,
        image_bytes: bytes,
        meta: Optional[AnalysisMetadata] = None,
        user_id: Optional[str] = None,
    ) -> AnalysisResponse:
        t0 = datetime.now()
        clean_img, img_record, quality = self.validate_and_preprocess_image(image_bytes)

        # Step 4: Detection
        detected_regions = self.detector.detect(image_bytes)

        analysis_id = f"an_{uuid.uuid4().hex[:12]}"
        analysis_record = AnalysisRecord(
            id=analysis_id,
            user_id=user_id,
            image_id=img_record.id,
            model_versions={
                "detector": self.detector.model_version,
                "segmenter": None,
                "classifier": self.classifier.model_version,
                "portion": self.portion_estimator.model_version,
                "visual_labelset": settings.VISUAL_LABELSET_VERSION,
                "identity_map": settings.IDENTITY_MAP_VERSION,
                "resolver": settings.RESOLVER_VERSION,
                "nutrition_db": settings.NUTRITION_DB_VERSION,
            },
            nutrition_db_version=settings.NUTRITION_DB_VERSION,
            visual_labelset_version=settings.VISUAL_LABELSET_VERSION,
            identity_map_version=settings.IDENTITY_MAP_VERSION,
            image_quality={"score": quality.score, "warnings": quality.warnings},
            status="completed",
        )
        self.db.add(analysis_record)

        analysis_items: List[AnalysisItem] = []
        items_nutrition = []

        for reg in detected_regions:
            item_key = reg["item_key"]
            bbox = reg["bbox"]
            coarse = reg["coarse_class"]

            # Step 5 & 6: Visual Classification
            visual_preds = self.classifier.classify_crop(image_bytes, coarse_hint=coarse, bbox=bbox)
            top_visual = visual_preds[0]
            visual_class_id = top_visual["visual_class_id"]
            visual_score = float(top_visual["p"])

            # Step 6b: Food Identity Resolution
            resolved_identity = self.resolver.resolve(
                visual_class_id=visual_class_id,
                visual_score=visual_score,
                visual_top_k=visual_preds,
            )

            # Check if food is countable
            food_detail = self.food_repo.get_food_detail(resolved_identity.food_id)
            is_countable = food_detail.is_countable if food_detail else False

            # Step 7: Portion Estimation
            portion_res = self.portion_estimator.estimate(
                coarse_class=coarse,
                food_id=resolved_identity.food_id,
                bbox=bbox,
                is_countable=is_countable,
            )

            # Step 8-10: Variant Profile binding & Nutrition calculation
            variant, profile = self.food_repo.get_variant_profile(
                food_id=resolved_identity.food_id,
                variant_id=resolved_identity.variant_id,
            )

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
                item_nut = self.nutrition_engine.calculate_item_nutrition(
                    profile=profile_dict,
                    grams=portion_res.grams,
                    source_name=profile.source_id or "IFCT2017",
                    confidence_score=resolved_identity.confidence.score * portion_res.confidence.score,
                )
            else:
                # Default generic calculation fallback
                item_nut = self.nutrition_engine.calculate_item_nutrition(
                    profile={"energy_kcal": 150.0, "protein_g": 5.0, "carbs_g": 20.0, "fat_g": 5.0},
                    grams=portion_res.grams,
                    confidence_score=0.5,
                )

            items_nutrition.append(item_nut)

            analysis_item = AnalysisItem(
                item_id=item_key,
                region=RegionSchema(bbox=bbox, mask_rle=None),
                food=resolved_identity,
                portion=portion_res,
                nutrition=item_nut,
                flags=["needs_verification"] if resolved_identity.confidence.level != "high" else [],
            )
            analysis_items.append(analysis_item)

            # Step 11: Save Prediction Item record
            pred_record = PredictionItem(
                id=str(uuid.uuid4()),
                analysis_id=analysis_record.id,
                item_key=item_key,
                bbox=bbox,
                coarse_class=coarse,
                detect_conf=reg["detect_conf"],
                visual_top_k=visual_preds,
                food_id=resolved_identity.food_id,
                variant_id=resolved_identity.variant_id,
                food_conf=visual_score,
                identity_conf=resolved_identity.confidence.score,
                identity_ambiguity=resolved_identity.identity.ambiguity,
                top_k=[{"food_id": a.food_id, "score": a.score} for a in resolved_identity.alternatives],
                portion_g=portion_res.grams,
                portion_lo=portion_res.range_g[0],
                portion_hi=portion_res.range_g[1],
                portion_conf=portion_res.confidence.score,
                portion_method=portion_res.method,
                nutrition=item_nut.model_dump(),
                nutrition_conf=item_nut.confidence.get("score", 0.8),
            )
            self.db.add(pred_record)

        totals = self.nutrition_engine.aggregate_totals(items_nutrition)

        t_end = datetime.now()
        analysis_record.timings_ms = {"total_ms": int((t_end - t0).total_seconds() * 1000)}
        self.db.commit()

        return AnalysisResponse(
            schema_version=settings.SCHEMA_VERSION,
            analysis_id=analysis_record.id,
            image_id=img_record.id,
            model_versions=analysis_record.model_versions,
            image_quality=quality,
            items=analysis_items,
            totals=totals,
            disclaimer="Nutrition values are estimates. Prediction + Confidence + Verification.",
        )
