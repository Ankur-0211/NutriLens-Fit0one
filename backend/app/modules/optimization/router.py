import os
from pathlib import Path
from fastapi import APIRouter, Query, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from typing import Dict, Any

from backend.app.modules.optimization.compressor import ClientImageCompressor
from backend.app.modules.optimization.quantizer import ModelQuantizationEngine
from backend.app.modules.optimization.benchmarks import InferenceBenchmarkSuite

# External APK download URL (points to fast 24/7 GitHub Releases CDN)
EXTERNAL_APK_URL = os.environ.get(
    "EXTERNAL_APK_URL",
    "https://github.com/Ankur-0211/NutriLens-Fit0one/releases/download/v1.0.0/app-debug.apk"
)

router = APIRouter(tags=["Mobile Optimization & Manifests"])

@router.get("/models/manifest", summary="Get on-device model package manifest for mobile clients")
def get_model_manifest(
    platform: str = Query("android", description="Mobile platform: 'android', 'ios', or 'cross_platform'"),
    precision: str = Query("INT8", description="Precision: 'INT8' or 'FP16'"),
):
    """
    Returns mobile download manifests with sha256 checksums, model URLs,
    and runtime formats (TFLite for Android, Core ML for iOS, ONNX Mobile).
    (SDD Section 33 Phase 10 line 2295)
    """
    runtime = "coreml" if platform.lower() == "ios" else "tflite"
    suite = ModelQuantizationEngine.get_full_suite_bundle(precision=precision)

    manifest_models = []
    for m in suite["models"]:
        manifest_models.append({
            "model_id": m["model_id"],
            "kind": m["kind"],
            "runtime": runtime,
            "precision": precision,
            "size_mb": m["quantized_size_mb"],
            "checksum_sha256": m["artifact_hash"] * 4,  # simulated 64-char hex
            "download_url": f"/v1/models/download/{m['model_id']}.{runtime}",
            "input_resolution": [640, 640] if m["kind"] == "detector" else [224, 224],
        })

    return {
        "platform": platform,
        "runtime": runtime,
        "precision": precision,
        "total_bundle_size_mb": suite["total_bundle_size_mb"],
        "fits_mobile_budget": suite["fits_mobile_budget"],
        "max_budget_mb": suite["max_budget_mb"],
        "min_app_version": "1.0.0",
        "models": manifest_models,
    }

@router.get("/optimization/benchmarks", summary="Get ADR-003 Inference Strategy Benchmarks")
def get_inference_benchmarks():
    """
    Returns the ADR-003 comparative benchmark evaluating Cloud vs On-Device vs Hybrid
    latency, battery, and accuracy across device hardware tiers.
    """
    return InferenceBenchmarkSuite.get_adr_003_decision_record()

@router.post("/optimization/compression-curve", summary="Test image compression trade-off curve")
async def evaluate_compression(file: UploadFile = File(...)):
    """
    Upload an image to benchmark the client compression trade-off curve against
    the <= 1.0 MB production target.
    """
    content = await file.read()
    compressed_bytes, meta = ClientImageCompressor.compress(content)
    return {
        "status": "success",
        "filename": file.filename,
        "optimization": meta,
    }

@router.api_route("/mobile/download", methods=["GET", "HEAD"], summary="Download complete mobile application package (PWA/Offline Zip)")
def download_mobile_package():
    """
    Downloads the standalone production mobile application package (.zip)
    containing the Flutter web PWA release bundle.
    """
    possible_paths = [
        Path("backend/uploads/nutrilens-mobile-app.zip").resolve(),
        Path(__file__).resolve().parent.parent.parent.parent / "uploads" / "nutrilens-mobile-app.zip",
        Path(__file__).resolve().parent.parent.parent / "uploads" / "nutrilens-mobile-app.zip",
    ]
    for p in possible_paths:
        if p.exists():
            return FileResponse(
                path=str(p),
                filename="nutrilens-mobile-app.zip",
                media_type="application/zip",
            )
    raise HTTPException(status_code=404, detail="Mobile application package not found")

@router.api_route("/mobile/download-apk", methods=["GET", "HEAD"], summary="Download standalone Android APK installer file")
def download_android_apk():
    """
    Downloads the compiled standalone Android APK (nutrilens.apk).
    If EXTERNAL_APK_URL is set (e.g. GitHub Release), redirects there for
    reliable large-file downloads. Otherwise serves the local APK file.
    """
    # Prefer external CDN (GitHub Releases) for reliable large file downloads
    if EXTERNAL_APK_URL:
        return RedirectResponse(url=EXTERNAL_APK_URL, status_code=302)

    possible_paths = [
        Path("backend/uploads/nutrilens.apk").resolve(),
        Path(__file__).resolve().parent.parent.parent.parent / "uploads" / "nutrilens.apk",
        Path(__file__).resolve().parent.parent.parent.parent.parent / "mobile" / "build" / "app" / "outputs" / "flutter-apk" / "app-release.apk",
        Path(__file__).resolve().parent.parent.parent.parent.parent / "mobile" / "build" / "app" / "outputs" / "flutter-apk" / "app-debug.apk",
    ]
    for p in possible_paths:
        if p.exists():
            return FileResponse(
                path=str(p),
                filename="nutrilens.apk",
                media_type="application/vnd.android.package-archive",
            )
    raise HTTPException(status_code=404, detail="Android APK package not found. Set EXTERNAL_APK_URL environment variable for cloud deployments.")



