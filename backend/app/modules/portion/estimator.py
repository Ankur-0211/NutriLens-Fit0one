from typing import Dict, Any, List, Optional
from backend.app.schemas.analysis import PortionResult, PortionUnit, ConfidenceInfo

class PortionEstimator:
    """
    Portion Estimation Service (SDD Section 17 & ADR-008).
    Implements geometric area estimation, plate/bowl-scale priors, and countable-item logic.
    Inputs:
    - coarse_class: 'curry', 'dal', 'bread', 'rice', 'accompaniment'
    - food_id: canonical food slug
    - bbox: normalized [ymin, xmin, ymax, xmax]
    - is_countable: boolean indicating countable items
    """

    def __init__(self, model_version: str = "por-0.2.0"):
        self.model_version = model_version

    def estimate(
        self,
        coarse_class: str,
        food_id: str,
        bbox: Optional[List[float]] = None,
        is_countable: bool = False,
    ) -> PortionResult:
        # Calculate bounding box normalized area (0..1)
        area = 0.16  # standard default area ~ 16% of plate
        aspect_ratio = 1.0
        if bbox and len(bbox) == 4:
            ymin, xmin, ymax, xmax = bbox
            w = max(0.05, xmax - xmin)
            h = max(0.05, ymax - ymin)
            area = min(1.0, max(0.01, w * h))
            aspect_ratio = w / h

        if is_countable or coarse_class == "bread" or "roti" in food_id or "paratha" in food_id or "puri" in food_id:
            # Countable item estimation
            # If bounding box area is large, multiple rotis are stacked or overlapping
            if "roti" in food_id or "phulka" in food_id or "chapati" in food_id:
                count = 2.0 if area > 0.12 else 1.0
                unit_name = "roti"
                unit_weight = 35.0
            elif "paratha" in food_id:
                count = 1.0 if area < 0.20 else 2.0
                unit_name = "paratha"
                unit_weight = 65.0
            elif "puri" in food_id:
                count = 3.0 if area > 0.15 else 2.0
                unit_name = "puri"
                unit_weight = 30.0
            else:
                count = 1.0
                unit_name = "piece"
                unit_weight = 50.0

            total_grams = round(count * unit_weight, 1)
            range_g = [round(total_grams * 0.85, 1), round(total_grams * 1.15, 1)]
            conf_score = round(min(0.94, max(0.75, 0.90 - abs(1.0 - aspect_ratio) * 0.15)), 2)

            return PortionResult(
                grams=total_grams,
                range_g=range_g,
                unit=PortionUnit(unit=unit_name, qty=count),
                confidence=ConfidenceInfo(level="high" if conf_score >= 0.8 else "medium", score=conf_score),
                method="countable_logic",
            )

        elif coarse_class == "dal" or "dal" in food_id or "sambar" in food_id:
            # Bowl food logic: Standard katori volume scaled by bounding box area fraction
            base_katori_g = 150.0
            scale_factor = min(1.4, max(0.75, area / 0.15))
            grams = round(base_katori_g * scale_factor, 1)
            range_g = [round(grams * 0.80, 1), round(grams * 1.20, 1)]
            qty = round(grams / 150.0, 1)

            return PortionResult(
                grams=grams,
                range_g=range_g,
                unit=PortionUnit(unit="katori", qty=qty),
                confidence=ConfidenceInfo(level="medium", score=0.74),
                method="bowl_fill+regressor",
            )

        elif coarse_class == "curry" or "paneer" in food_id or "sabzi" in food_id:
            # Curry / Gravy logic
            base_serving_g = 150.0
            scale_factor = min(1.4, max(0.75, area / 0.15))
            grams = round(base_serving_g * scale_factor, 1)
            range_g = [round(grams * 0.78, 1), round(grams * 1.25, 1)]
            qty = round(grams / 150.0, 1)

            return PortionResult(
                grams=grams,
                range_g=range_g,
                unit=PortionUnit(unit="katori", qty=qty),
                confidence=ConfidenceInfo(level="medium", score=0.76),
                method="bowl_fill+regressor",
            )

        elif coarse_class == "rice" or "rice" in food_id or "biryani" in food_id:
            # Heap / Area logic
            base_plate_g = 160.0
            scale_factor = min(1.5, max(0.70, area / 0.18))
            grams = round(base_plate_g * scale_factor, 1)
            range_g = [round(grams * 0.82, 1), round(grams * 1.22, 1)]
            qty = round(grams / 150.0, 1)

            return PortionResult(
                grams=grams,
                range_g=range_g,
                unit=PortionUnit(unit="katori", qty=qty),
                confidence=ConfidenceInfo(level="medium", score=0.72),
                method="heap_area+priors",
            )

        else:
            # Generic fallback
            grams = round(100.0 * min(2.0, max(0.5, area / 0.15)), 1)
            range_g = [round(grams * 0.70, 1), round(grams * 1.35, 1)]

            return PortionResult(
                grams=grams,
                range_g=range_g,
                unit=PortionUnit(unit="g", qty=grams),
                confidence=ConfidenceInfo(level="low", score=0.55),
                method="default_prior",
            )
