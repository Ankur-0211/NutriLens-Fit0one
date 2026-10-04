import io
from pathlib import Path
from typing import Dict, Any, Tuple
from PIL import Image

class ClientImageCompressor:
    """
    Client-side Image Compression Optimizer (SDD Section 29.1, 29.2).
    Tunes camera resolution and quality to meet the production payload budget:
    <= 1.0 MB upload size, 1024-1280px long-edge, preserving food recognition accuracy.
    """
    TARGET_LONG_EDGE_MAX = 1280
    TARGET_LONG_EDGE_MIN = 1024
    MAX_FILE_SIZE_BYTES = 1024 * 1024  # 1 MB

    @classmethod
    def compress(
        cls,
        image_input,
        max_long_edge: int = 1280,
        quality: int = 82,
        format: str = "JPEG",
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Resizes and compresses an image for fast network transmission.
        Returns (compressed_bytes, metadata).
        """
        if isinstance(image_input, (str, Path)):
            img = Image.open(str(image_input))
        elif isinstance(image_input, bytes):
            img = Image.open(io.BytesIO(image_input))
        else:
            img = image_input

        # Convert palette/RGBA to RGB for standard JPEG
        if img.mode != "RGB":
            img = img.convert("RGB")

        orig_w, orig_h = img.size
        long_edge = max(orig_w, orig_h)

        # Scale down if long edge exceeds maximum
        if long_edge > max_long_edge:
            scale = max_long_edge / float(long_edge)
            new_w = int(orig_w * scale)
            new_h = int(orig_h * scale)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        else:
            new_w, new_h = orig_w, orig_h

        out_io = io.BytesIO()
        img.save(out_io, format=format, quality=quality, optimize=True)
        compressed_bytes = out_io.getvalue()

        # If still over budget, iteratively adjust quality
        current_quality = quality
        while len(compressed_bytes) > cls.MAX_FILE_SIZE_BYTES and current_quality > 60:
            current_quality -= 5
            out_io = io.BytesIO()
            img.save(out_io, format=format, quality=current_quality, optimize=True)
            compressed_bytes = out_io.getvalue()

        size_kb = len(compressed_bytes) / 1024.0
        return compressed_bytes, {
            "original_resolution": [orig_w, orig_h],
            "compressed_resolution": [new_w, new_h],
            "final_quality": current_quality,
            "format": format,
            "bytes": len(compressed_bytes),
            "size_kb": round(size_kb, 2),
            "within_production_budget": len(compressed_bytes) <= cls.MAX_FILE_SIZE_BYTES,
        }

    @classmethod
    def evaluate_curve(cls, image_path: str) -> Dict[str, Any]:
        """
        Computes the compression trade-off curve across resolution and quality levels (SDD Section 10).
        """
        points = []
        for edge in [800, 1024, 1280]:
            for q in [70, 82, 90]:
                _, meta = cls.compress(image_path, max_long_edge=edge, quality=q)
                points.append({
                    "long_edge": edge,
                    "quality": q,
                    "size_kb": meta["size_kb"],
                    "within_budget": meta["within_production_budget"],
                })

        return {
            "recommended_preset": {"max_long_edge": 1280, "quality": 82, "format": "JPEG"},
            "curve_samples": points,
            "production_target_max_kb": 1024.0,
        }
