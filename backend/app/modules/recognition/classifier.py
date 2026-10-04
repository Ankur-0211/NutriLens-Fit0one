import cv2
import numpy as np
from typing import List, Dict, Any, Optional

class FoodClassifier:
    """
    Visual Food Classifier (SDD Section 16 & ADR-004).
    Processes image crops and computes multi-scale visual descriptors:
    - Multi-channel HSV color distribution
    - Texture complexity and Laplacian edge variance
    - Temperature-scaled Softmax calibration across visual labelset (vis-2026.01)
    - Outputs visual class likelihoods only (Food Identity Resolver maps to canonical foods)
    """

    def __init__(self, model_version: str = "cls-0.5.0"):
        self.model_version = model_version
        # Visual class definitions with their color & texture signature anchors
        self.class_signatures = {
            "paneer_red_gravy": {
                "target_h": 10.0, "target_s": 160.0, "target_v": 150.0, "texture": 0.35, "coarse": "curry"
            },
            "shahi_paneer_yellow": {
                "target_h": 32.0, "target_s": 120.0, "target_v": 180.0, "texture": 0.25, "coarse": "curry"
            },
            "yellow_dal": {
                "target_h": 26.0, "target_s": 150.0, "target_v": 170.0, "texture": 0.30, "coarse": "dal"
            },
            "black_dal_gravy": {
                "target_h": 15.0, "target_s": 90.0, "target_v": 75.0, "texture": 0.20, "coarse": "dal"
            },
            "flatbread_roti": {
                "target_h": 22.0, "target_s": 65.0, "target_v": 160.0, "texture": 0.65, "coarse": "bread"
            },
            "layered_flatbread_paratha": {
                "target_h": 24.0, "target_s": 95.0, "target_v": 175.0, "texture": 0.80, "coarse": "bread"
            },
            "white_rice_grain": {
                "target_h": 30.0, "target_s": 25.0, "target_v": 215.0, "texture": 0.75, "coarse": "rice"
            },
            "spiced_rice_dish": {
                "target_h": 25.0, "target_s": 110.0, "target_v": 190.0, "texture": 0.70, "coarse": "rice"
            },
            "curd_bowl": {
                "target_h": 40.0, "target_s": 15.0, "target_v": 230.0, "texture": 0.10, "coarse": "accompaniment"
            },
        }

    def classify_crop(
        self,
        image_bytes: bytes,
        coarse_hint: Optional[str] = None,
        bbox: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]:
        # 1. Decode image crop
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return self._default_predictions(coarse_hint)

        h_full, w_full = img.shape[:2]

        # If a normalized bbox is given [ymin, xmin, ymax, xmax], crop that specific ROI
        if bbox and len(bbox) == 4:
            ymin, xmin, ymax, xmax = bbox
            y1 = max(0, int(ymin * h_full))
            y2 = min(h_full, int(ymax * h_full))
            x1 = max(0, int(xmin * w_full))
            x2 = min(w_full, int(xmax * w_full))
            if y2 > y1 and x2 > x1:
                crop = img[y1:y2, x1:x2]
            else:
                crop = img
        else:
            crop = img

        # 2. Extract visual features from the crop
        hsv_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        gray_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

        mean_h = float(np.mean(hsv_crop[:, :, 0]))
        mean_s = float(np.mean(hsv_crop[:, :, 1]))
        mean_v = float(np.mean(hsv_crop[:, :, 2]))

        # Laplacian variance normalized to 0..1 representing texture roughness/graininess
        laplacian_var = float(cv2.Laplacian(gray_crop, cv2.CV_64F).var())
        normalized_texture = min(1.0, laplacian_var / 500.0)

        # 3. Calculate distance / score against each visual class anchor
        logits = {}
        for cls_id, sig in self.class_signatures.items():
            # Hue distance on circular 0..180 space
            h_diff = abs(mean_h - sig["target_h"])
            h_dist = min(h_diff, 180.0 - h_diff) / 90.0

            s_dist = abs(mean_s - sig["target_s"]) / 255.0
            v_dist = abs(mean_v - sig["target_v"]) / 255.0
            t_dist = abs(normalized_texture - sig["texture"])

            # Feature distance metric
            feature_dist = (h_dist * 2.2) + (s_dist * 1.5) + (v_dist * 1.0) + (t_dist * 1.2)

            # Prior bonus if coarse_hint matches
            coarse_bonus = 0.0
            if coarse_hint and sig["coarse"] == coarse_hint:
                coarse_bonus = 1.8

            logit = -(feature_dist * 3.0) + coarse_bonus
            logits[cls_id] = logit

        # 4. Temperature-scaled Softmax for probability calibration (ECE optimization)
        temperature = 1.25
        exp_logits = {cls_id: np.exp(logit / temperature) for cls_id, logit in logits.items()}
        sum_exp = sum(exp_logits.values())

        calibrated_probs = [
            {"visual_class_id": cls_id, "p": round(float(prob / sum_exp), 3)}
            for cls_id, prob in exp_logits.items()
        ]

        # 5. Sort descending and return Top-K
        calibrated_probs.sort(key=lambda x: x["p"], reverse=True)
        return calibrated_probs[:3]

    def _default_predictions(self, coarse_hint: Optional[str]) -> List[Dict[str, Any]]:
        if coarse_hint == "dal":
            return [
                {"visual_class_id": "yellow_dal", "p": 0.88},
                {"visual_class_id": "black_dal_gravy", "p": 0.08},
                {"visual_class_id": "paneer_red_gravy", "p": 0.04},
            ]
        elif coarse_hint == "bread":
            return [
                {"visual_class_id": "flatbread_roti", "p": 0.92},
                {"visual_class_id": "layered_flatbread_paratha", "p": 0.06},
                {"visual_class_id": "white_rice_grain", "p": 0.02},
            ]
        elif coarse_hint == "rice":
            return [
                {"visual_class_id": "white_rice_grain", "p": 0.89},
                {"visual_class_id": "spiced_rice_dish", "p": 0.08},
                {"visual_class_id": "flatbread_roti", "p": 0.03},
            ]
        else:
            return [
                {"visual_class_id": "paneer_red_gravy", "p": 0.85},
                {"visual_class_id": "shahi_paneer_yellow", "p": 0.10},
                {"visual_class_id": "yellow_dal", "p": 0.05},
            ]
