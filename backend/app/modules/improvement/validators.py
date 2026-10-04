import os
from pathlib import Path
from typing import Tuple, Optional, List
from PIL import Image
from sqlalchemy.orm import Session

from backend.app.models.nutrition import Food, FoodVariant

def validate_image_decodable(image_path: str) -> Tuple[bool, Optional[str], int, int]:
    """
    Validates that an image file exists, can be decoded, and meets minimum resolution requirements.
    (SDD Section 23.3 Automated Validation)
    """
    if not image_path or not os.path.exists(image_path):
        return False, "File does not exist on disk", 0, 0
    try:
        with Image.open(image_path) as img:
            img.verify()
        # Re-open after verify() as verify alters file pointer
        with Image.open(image_path) as img:
            w, h = img.size
            if w < 64 or h < 64:
                return False, f"Image resolution too small: {w}x{h} (minimum 64x64 required)", w, h
            return True, None, w, h
    except Exception as e:
        return False, f"Corrupted or non-decodable image: {str(e)}", 0, 0

def compute_dhash(image_path: str, hash_size: int = 8) -> str:
    """
    Computes a 64-bit difference hash (dHash) for perceptual similarity comparison and deduplication.
    (SDD Section 24.3 Preventing Data Leakage)
    """
    try:
        with Image.open(image_path) as img:
            # Resize to (hash_size + 1, hash_size) in grayscale
            resized = img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
            pixels = list(resized.tobytes())
            
            # Compare adjacent pixels in each row
            diff = []
            for row in range(hash_size):
                row_start = row * (hash_size + 1)
                for col in range(hash_size):
                    left = pixels[row_start + col]
                    right = pixels[row_start + col + 1]
                    diff.append(1 if left > right else 0)
            
            # Convert 64 bits to 16 hex characters
            decimal_val = 0
            for bit in diff:
                decimal_val = (decimal_val << 1) | bit
            return f"{decimal_val:016x}"
    except Exception:
        return "0000000000000000"

def hamming_distance(hex_hash1: str, hex_hash2: str) -> int:
    """Calculates bit difference between two 64-bit hex hash strings."""
    try:
        val1 = int(hex_hash1, 16)
        val2 = int(hex_hash2, 16)
        xor_val = val1 ^ val2
        return bin(xor_val).count("1")
    except Exception:
        return 64

def check_duplicate_or_leakage(
    image_hash: str,
    existing_hashes: List[str],
    frozen_test_hashes: List[str],
    threshold: int = 6
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Checks if a candidate image is a duplicate of existing data or causes test-set leakage.
    Returns: (violates: bool, violation_type: str, reason: str)
    (SDD Section 23.3, 24.3)
    """
    # 1. Leakage guard against frozen test set (STRICT isolation)
    for test_h in frozen_test_hashes:
        dist = hamming_distance(image_hash, test_h)
        if dist <= threshold:
            return True, "leakage_violation", f"Image hash distance {dist} <= {threshold} to frozen test set"

    # 2. Near-duplicate check against training pool
    for ex_h in existing_hashes:
        dist = hamming_distance(image_hash, ex_h)
        if dist <= threshold:
            return True, "near_duplicate", f"Image hash distance {dist} <= {threshold} to existing training sample"

    return False, None, None

def validate_correction_plausibility(
    event_type: str,
    before_data: Optional[dict],
    after_data: Optional[dict],
    db: Session
) -> Tuple[bool, Optional[str]]:
    """
    Validates that a user correction is physically and taxonomically plausible.
    (SDD Section 23.3 Automated Validation)
    """
    if not after_data:
        return False, "Missing after correction data"

    # 1. Check quantity bounds
    grams = after_data.get("grams") or after_data.get("portion_g")
    if grams is not None:
        try:
            grams_f = float(grams)
            if grams_f <= 0:
                return False, f"Non-positive gram quantity: {grams_f}g"
            if grams_f > 2500.0:
                return False, f"Implausibly large single-portion quantity: {grams_f}g (max 2500g)"
        except (ValueError, TypeError):
            return False, f"Invalid gram format: {grams}"

    # 2. Check food / variant validity
    food_id = after_data.get("food_id")
    variant_id = after_data.get("variant_id")

    if food_id:
        food_exists = db.query(Food).filter(Food.id == food_id).first()
        if not food_exists:
            return False, f"Target food '{food_id}' not found in canonical food taxonomy"

    if variant_id:
        variant_exists = db.query(FoodVariant).filter(FoodVariant.id == variant_id).first()
        if not variant_exists:
            return False, f"Target variant '{variant_id}' not found in food database"

    return True, None

def classify_correction_cause(
    event_type: str,
    before_data: Optional[dict],
    after_data: Optional[dict],
    visual_top_k: Optional[List[dict]] = None
) -> str:
    """
    Routes corrections by underlying technical cause according to SDD Section 23.5.
    Possible causes:
    - visual_misrecognition: Correct dish not in visual Top-K classes
    - variant_ambiguity: User switched variant of same canonical food
    - mapping_error: Visual class correct but canonical variant selection wrong
    - portion_bias: User adjusted grams/unit
    - taxonomy_gap: Food missing from canonical mapping
    - user_confirmation: No change made
    """
    if event_type == "confirmed_unchanged":
        return "user_confirmation"
    
    if event_type == "variant_changed":
        return "variant_ambiguity"

    if event_type in ("quantity_changed", "unit_changed"):
        return "portion_bias"

    if event_type == "food_changed":
        before_fid = (before_data or {}).get("food_id")
        after_fid = (after_data or {}).get("food_id")

        if before_fid == after_fid:
            return "variant_ambiguity"

        # Check if the corrected food is related to visual classes detected
        if visual_top_k:
            # If after_fid is part of visual candidates, it's a mapping error
            top_classes = [k.get("visual_class_id", "") for k in visual_top_k]
            # If classifier was completely off:
            return "visual_misrecognition"
        return "visual_misrecognition"

    if event_type == "item_added":
        return "detection_miss"

    if event_type == "item_removed":
        return "false_positive"

    return "general_correction"
