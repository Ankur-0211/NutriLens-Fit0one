from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from backend.app.models.identity import VisualClass, VisualClassMapping, IdentityMapVersion
from backend.app.models.nutrition import Food, FoodVariant, NutritionProfile
from backend.app.schemas.analysis import (
    FoodIdentityResult,
    VisualInfo,
    IdentityInfo,
    VariantAlternative,
    FoodAlternative,
    ConfidenceInfo,
)

class FoodIdentityResolver:
    """
    Food Identity Resolution Layer (SDD Section 16A and ADR-009).
    Decouples visual classification from the canonical nutrition database.
    Deterministic, map-driven, with explicit ambiguity flags and variant candidates.
    """

    def __init__(self, db: Session, identity_map_version: str = "idmap-2026.01"):
        self.db = db
        self.map_version = identity_map_version

    def resolve(
        self,
        visual_class_id: str,
        visual_score: float = 0.90,
        visual_top_k: Optional[List[Dict[str, Any]]] = None,
    ) -> FoodIdentityResult:
        # 1. Query mapping table for this visual class in current map version
        mappings = (
            self.db.query(VisualClassMapping)
            .filter(
                VisualClassMapping.visual_class_id == visual_class_id,
                VisualClassMapping.identity_map_version == self.map_version,
            )
            .order_by(VisualClassMapping.weight.desc())
            .all()
        )

        if not mappings:
            # Fallback for unmapped visual class -> direct slug or unknown
            food = self.db.query(Food).filter(Food.id == visual_class_id).first()
            if food:
                food_id = food.id
                food_name = food.display_name
                variant_id = f"{food_id}:default"
                ambiguity = "none"
            else:
                food_id = "unknown_food"
                food_name = visual_class_id.replace("_", " ").title()
                variant_id = "unknown_food:default"
                ambiguity = "food"

            return FoodIdentityResult(
                visual=VisualInfo(visual_class_id=visual_class_id, score=round(visual_score, 2)),
                food_id=food_id,
                variant_id=variant_id,
                name=food_name,
                identity=IdentityInfo(
                    resolver="idr-0.1.0",
                    ambiguity=ambiguity,
                    variant_alternatives=[],
                ),
                confidence=ConfidenceInfo(
                    level="low",
                    score=round(visual_score * 0.7, 2),
                ),
                alternatives=[],
            )

        # 2. Pick primary mapping (highest weight or marked default)
        primary_mapping = next((m for m in mappings if m.is_default), mappings[0])
        variant = self.db.query(FoodVariant).filter(FoodVariant.id == primary_mapping.food_variant_id).first()
        food = self.db.query(Food).filter(Food.id == variant.food_id).first() if variant else None

        food_id = food.id if food else "unknown_food"
        food_name = food.display_name if food else visual_class_id.replace("_", " ").title()
        variant_id = variant.id if variant else f"{food_id}:default"

        # 3. Detect ambiguity and gather variant alternatives
        all_variants_for_food = (
            self.db.query(FoodVariant)
            .filter(FoodVariant.food_id == food_id)
            .all()
        )

        variant_alternatives = []
        for v in all_variants_for_food:
            if v.id != variant_id:
                prof = (
                    self.db.query(NutritionProfile)
                    .filter(NutritionProfile.food_variant_id == v.id, NutritionProfile.is_current == True)
                    .first()
                )
                variant_alternatives.append(
                    VariantAlternative(
                        variant_id=v.id,
                        label=v.label,
                        kcal=float(prof.energy_kcal) if prof else None,
                    )
                )

        # Determine ambiguity status
        distinct_foods = {m.food_variant_id.split(":")[0] for m in mappings}
        if len(distinct_foods) > 1:
            ambiguity = "food"
        elif len(all_variants_for_food) > 1:
            ambiguity = "variant"
        else:
            ambiguity = "none"

        # 4. Resolve alternative foods if visual_top_k provided
        alternatives: List[FoodAlternative] = []
        if visual_top_k:
            for alt in visual_top_k:
                alt_cls = alt.get("visual_class_id")
                alt_p = alt.get("p", 0.0)
                if alt_cls and alt_cls != visual_class_id:
                    alt_map = (
                        self.db.query(VisualClassMapping)
                        .filter(VisualClassMapping.visual_class_id == alt_cls)
                        .first()
                    )
                    if alt_map and alt_map.food_variant_id:
                        alt_fid = alt_map.food_variant_id.split(":")[0]
                        alt_food = self.db.query(Food).filter(Food.id == alt_fid).first()
                        if alt_food and not any(a.food_id == alt_fid for a in alternatives):
                            alternatives.append(
                                FoodAlternative(
                                    food_id=alt_fid,
                                    name=alt_food.display_name,
                                    score=round(float(alt_p), 2),
                                )
                            )

        mapping_weight = float(primary_mapping.weight)
        combined_score = round(visual_score * mapping_weight, 2)
        conf_level = "high" if combined_score >= 0.8 else ("medium" if combined_score >= 0.5 else "low")

        return FoodIdentityResult(
            visual=VisualInfo(visual_class_id=visual_class_id, score=round(visual_score, 2)),
            food_id=food_id,
            variant_id=variant_id,
            name=food_name,
            identity=IdentityInfo(
                resolver="idr-0.1.0",
                ambiguity=ambiguity,
                variant_alternatives=variant_alternatives,
            ),
            confidence=ConfidenceInfo(
                level=conf_level,
                score=combined_score,
            ),
            alternatives=alternatives[:3],
        )
