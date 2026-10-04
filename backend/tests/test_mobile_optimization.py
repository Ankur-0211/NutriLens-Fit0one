import io
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.modules.optimization.compressor import ClientImageCompressor
from backend.app.modules.optimization.quantizer import ModelQuantizationEngine
from backend.app.modules.optimization.benchmarks import InferenceBenchmarkSuite

client = TestClient(app)

def test_client_image_compression():
    # Create large synthetic image (2400 x 1800 px)
    img = Image.new("RGB", (2400, 1800), color=(180, 120, 60))
    img_io = io.BytesIO()
    img.save(img_io, format="JPEG", quality=95)
    raw_bytes = img_io.getvalue()

    compressed_bytes, meta = ClientImageCompressor.compress(raw_bytes, max_long_edge=1280, quality=82)

    assert meta["within_production_budget"] is True
    assert len(compressed_bytes) <= 1024 * 1024  # <= 1 MB
    assert max(meta["compressed_resolution"]) <= 1280
    assert meta["format"] == "JPEG"

    # Evaluate compression curve
    curve_data = ClientImageCompressor.evaluate_curve(img)
    assert len(curve_data["curve_samples"]) == 9
    assert curve_data["production_target_max_kb"] == 1024.0

def test_model_quantization_evaluation():
    # Test INT8 quantization for classifier
    cls_eval = ModelQuantizationEngine.evaluate_quantization("cls-0.5.0", target_precision="INT8", target_runtime="tflite")
    assert cls_eval["quantized_size_mb"] < cls_eval["fp32_size_mb"]
    assert cls_eval["compression_ratio"] >= 3.0
    assert cls_eval["passes_accuracy_budget"] is True
    assert cls_eval["estimated_acc_drop_pts"] <= 1.5

    # Test FP16 quantization for detector
    det_eval = ModelQuantizationEngine.evaluate_quantization("det-0.3.1", target_precision="FP16", target_runtime="coreml")
    assert det_eval["compression_ratio"] >= 1.8
    assert det_eval["passes_accuracy_budget"] is True

    # Test full on-device bundle size
    bundle = ModelQuantizationEngine.get_full_suite_bundle(precision="INT8")
    assert bundle["fits_mobile_budget"] is True
    assert bundle["total_bundle_size_mb"] <= 50.0
    assert len(bundle["models"]) == 3

def test_adr_003_benchmarks():
    cloud_report = InferenceBenchmarkSuite.evaluate_strategy("cloud")
    assert "budget_android" in cloud_report["tiers"]
    assert cloud_report["tiers"]["budget_android"]["offline_support"] is False

    on_device_report = InferenceBenchmarkSuite.evaluate_strategy("on_device")
    assert on_device_report["tiers"]["budget_android"]["offline_support"] is True
    assert on_device_report["tiers"]["flagship_ios"]["e2e_scan_latency_ms"] < 300

    hybrid_report = InferenceBenchmarkSuite.evaluate_strategy("hybrid")
    assert hybrid_report["tiers"]["midrange_android"]["offline_support"] == "lite_mode"

    adr_rec = InferenceBenchmarkSuite.get_adr_003_decision_record()
    assert adr_rec["decision_record"] == "ADR-003"
    assert "recommendation" in adr_rec

def test_model_manifest_endpoints():
    # Android TFLite manifest
    res_android = client.get("/v1/models/manifest?platform=android&precision=INT8")
    assert res_android.status_code == 200
    data_android = res_android.json()
    assert data_android["runtime"] == "tflite"
    assert data_android["fits_mobile_budget"] is True
    assert len(data_android["models"]) == 3
    assert all("download_url" in m for m in data_android["models"])

    # iOS Core ML manifest
    res_ios = client.get("/v1/models/manifest?platform=ios&precision=FP16")
    assert res_ios.status_code == 200
    data_ios = res_ios.json()
    assert data_ios["runtime"] == "coreml"

    # Optimization benchmarks endpoint
    res_bench = client.get("/v1/optimization/benchmarks")
    assert res_bench.status_code == 200
    assert "evaluated_strategies" in res_bench.json()

def test_compression_curve_api():
    img = Image.new("RGB", (1600, 1200), color=(100, 150, 200))
    io_buf = io.BytesIO()
    img.save(io_buf, format="JPEG")
    io_buf.seek(0)

    res = client.post(
        "/v1/optimization/compression-curve",
        files={"file": ("test_plate.jpg", io_buf.getvalue(), "image/jpeg")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["optimization"]["within_production_budget"] is True
    assert max(data["optimization"]["compressed_resolution"]) <= 1280

def test_mobile_download_endpoints():
    # Test Mobile PWA Zip Download
    res_zip = client.get("/v1/mobile/download")
    assert res_zip.status_code == 200
    assert res_zip.headers.get("content-type") == "application/zip"
    assert int(res_zip.headers.get("content-length", 0)) > 1000000

    # Test Mobile Standalone APK Download (supports 302 redirect to cloud CDN or 200 local file)
    res_apk = client.get("/v1/mobile/download-apk", follow_redirects=False)
    assert res_apk.status_code in (200, 302)
    if res_apk.status_code == 302:
        assert "releases/download" in res_apk.headers.get("location", "")
    else:
        assert "application/vnd.android.package-archive" in res_apk.headers.get("content-type", "")
        assert int(res_apk.headers.get("content-length", 0)) > 10000000
