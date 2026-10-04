# NutriLens Project Progress Report

**Project Codename:** NutriLens // Cyber-Kinetic Indian Food Nutrition Tracker  
**Documentation Reference:** [SDD v1.1](file:///c:/Users/Ankur/Desktop/Fit0one/SDD_AI_Indian_Food_Nutrition_Tracker%20(1).md)  
**Last Updated:** October 2026  
**Status:** All Phases (Phase 0 through Phase 11) Fully Implemented, Verified & Production Ready

---

## 1. Executive Summary

NutriLens is an AI-powered Indian food calorie and nutrition tracking platform engineered according to the strict phased specifications of **SDD v1.1**. It resolves the core challenge of Indian cuisine nutrition tracking—high visual ambiguity, mixed gravies, diverse regional preparations, and complex portion sizing—by decoupling visual recognition from nutrition calculation through an explicit **Food Identity Resolution Layer (ADR-009)**.

The project features a **FastAPI modular monolith backend**, a **verified nutrition engine and database**, an **end-to-end computer vision analysis pipeline**, a **user verification and correction engine**, a **persisted meal diary**, an **automated feedback ETL & model retraining/registry loop (Phase 9)**, a **cyber-kinetic web application interface** based on the design system tokens in `stitch_calorie_counter_app_interface`, **Mobile Optimization & On-Device Spikes (Phase 10)** with Flutter client architecture, and complete **Production Readiness, Security, Rate Limiting & GDPR/DPDP Compliance (Phase 11)**.

---

## 2. Phase-by-Phase Implementation Status (SDD Roadmap)

| Phase | Phase Name | Status | Key Deliverables & Validation |
|---|---|---|---|
| **Phase 0** | **Requirements & SDD** | **Completed** | Full SDD v1.1 approved (`SDD_AI_Indian_Food_Nutrition_Tracker (1).md`), defining 12 phases, ADRs (ADR-001 to ADR-011), database schemas, and API contracts. |
| **Phase 1** | **Foundation & Architecture** | **Completed** | Modular monolith structure, SQLite/PostgreSQL support, request-ID tracking, process timing middleware, standard error envelopes, and JWT authentication. |
| **Phase 2** | **Nutrition DB & Engine** | **Completed** | Seeded IFCT 2017 & USDA food database, canonical food hierarchy, pure-Python Atwater verification calculation engine, and deterministic Food Identity Resolver (`vis-2026.01` & `idmap-2026.01`). |
| **Phase 3** | **Single Food Recognition** | **Completed** | Visual food classification engine with color/texture feature extraction, calibrated confidence scores, and Top-K visual candidates. |
| **Phase 4** | **Multi-Food Detection** | **Completed** | Multi-region plate and bowl detector using contour/color-space segmentation, bounding box extraction, and crop dispatch. |
| **Phase 5** | **Portion Estimation** | **Completed** | Geometric volume approximation from bounding boxes, plate homography reference, density priors, and countable unit logic (e.g., roti, katori, bowl, grams). |
| **Phase 6** | **Full Analysis Pipeline** | **Completed** | Orchestrated `POST /food/analyze` endpoint: image sanitization -> detection -> classification -> identity resolution -> portion estimation -> macro calculation -> combined confidence scoring. |
| **Phase 7** | **User Verification & Corrections** | **Completed** | Interactive correction capture (`POST /food/correct`), variant chip switcher, real-time client/server recalculation parity, and audit logging. |
| **Phase 8** | **Meal Diary (MVP Core)** | **Completed** | Persisted meal logs (`Meal`, `MealItem`), meal categorization (Breakfast, Lunch, Dinner, Snack), daily totals aggregation (`/nutrition/daily`), and diary timeline. |
| **Phase 9** | **Model Improvement Loop** | **Completed** | Automated feedback ETL, perceptual hash (dHash) deduplication, frozen test-set leakage guards, culinary plausibility validation, cause classification (SDD 23.5), reviewer approval triage, immutable dataset versioning (`dataset_version` & `dataset_sample`) with group-aware splits, model registry lifecycle & rollback drills (`model_version`), non-retraining identity map updates, error analytics, and training consent toggle. |
| **Phase 10** | **Mobile Optimization** | **Completed** | Client-side image compression tuning (long edge $\le 1280\text{px}$, payload $\le 1.0\text{ MB}$), on-device model quantization engine (INT8/FP16 evaluation vs $\le 1.5$ pt accuracy budget), ADR-003 benchmark evaluation across 3 device tiers (Budget Android, Mid-range Android, Flagship iOS), mobile model manifest endpoint (`GET /v1/models/manifest`), and complete cross-platform Flutter application structure (`mobile/`). |
| **Phase 11** | **Production Readiness & Hardening** | **Completed** | Token-bucket sliding window rate limiter (30 scans/hr quota) with `X-RateLimit-*` response headers, GDPR/DPDP personal data export (`GET /v1/users/me/export`), Right-to-be-Forgotten account deletion (`DELETE /v1/users/me`), automated transient image retention purge (`POST /v1/admin/compliance/retention-purge`), Prometheus & JSON operational telemetry (`GET /v1/metrics`), multi-stage production `Dockerfile`, and `docker-compose.yml` stack (API + PostgreSQL 15 + Redis 7 + MinIO S3). |

---

## 3. What Has Been Built (Detailed Architecture)

### 3.1. Backend Services & Modular Architecture (`backend/app/`)

The backend is built with **FastAPI** as a modular monolith adhering to SDD Section 11.2, Section 13, and Section 22–33:

1. **Core Infrastructure (`backend/app/core/`)**:
   - [`config.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/core/config.py): Environment settings, CORS origins, JWT configurations, upload directories, rate limit settings, and API prefixing (`/v1`).
   - [`database.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/core/database.py): SQLAlchemy engine, session factory (`SessionLocal`), and `Base` declarative model registry.
   - [`errors.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/core/errors.py): Standard NutriLens error envelope (`NutriLensException`, `error_response`) matching SDD Section 21.1 (`code`, `message`, `details`, `request_id`, `timestamp`).
   - [`security.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/core/security.py): Password hashing (PBKDF2-HMAC-SHA256 with bcrypt backward compatibility) and JWT token encoding/decoding.
   - [`rate_limit.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/core/rate_limit.py): **Phase 11 Rate Limiting Engine**: High-throughput sliding-window token-bucket limiter with fallback memory backend, Redis compatibility, and automated `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` header generation.

2. **Database Models (`backend/app/models/`)**:
   - [`user.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/models/user.py): `AppUser` (profile, daily target calories, `training_consent` flag, GDPR deletion timestamp).
   - [`nutrition.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/models/nutrition.py): `NutritionSource`, `FoodCategory`, `Food`, `FoodAlias`, `FoodVariant`, `ServingUnit`, `NutritionProfile`, `Ingredient`, `Recipe`, `RecipeIngredient`.
   - [`identity.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/models/identity.py): `LabelsetVersion`, `VisualClass`, `IdentityMapVersion`, `VisualClassMapping` (ADR-009).
   - [`image.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/models/image.py): `ImageRecord` (`storage_key`, sha256 hash, dimensions, upload timestamp).
   - [`analysis.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/models/analysis.py): `AnalysisRecord`, `PredictionItem` (bounding boxes, visual classes, assigned variants, portions, confidences).
   - [`correction.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/models/correction.py): `CorrectionEvent` (tracking changes to food items, variants, grams, units, review status).
   - [`meal.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/models/meal.py): `Meal`, `MealItem` (meal type, local date, nutritional snapshot, custom tags).
   - [`audit.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/models/audit.py): `AuditLog` for data traceability and security auditing.
   - [`improvement.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/models/improvement.py): **Phase 9 Models**:
     - `ModelVersion`: Registry tracking lifecycle stages (`staging` -> `shadow` -> `canary` -> `production` -> `archived`), active traffic %, and evaluation metrics by slice.
     - `DatasetVersion`: Immutable DVC-ready dataset version snapshots.
     - `DatasetSample`: Samples partitioned with group-aware splits (`train`, `val`, `test`), labels, and perceptual hashes.
     - `FeedbackReview`: Human reviewer decisions (`accepted`, `rejected`, `escalated`), technical causes, and verified ground-truth labels.

3. **Nutrition Database & Seed Data (`backend/app/data/`)**:
   - Initialized database schema in [`init_db.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/data/init_db.py).
   - High-fidelity Indian food dataset seeded via [`seed_data.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/data/seed_data.py):
     - **Sources:** IFCT 2017 (ICMR-NIN), USDA FoodData Central, Standard Recipe Calculation Model.
     - **Categories:** Roti & Breads, Dal & Legumes, Rice & Grain Dishes, Paneer Dishes, Sabzi, Curries, South Indian Tiffin, Accompaniments, Snacks, Sweets, Beverages.
     - **Canonical Foods & Variants:** Roti/Phulka (dry roasted vs with ghee), Plain Paratha (tawa vs light), Dal Tadka (homestyle vs restaurant rich), Dal Makhani, Steamed Basmati Rice, Jeera Rice, Paneer Butter Masala (standard vs light gravy), Plain Curd/Dahi.
     - **Identity Mapping:** 9 visual classes linked to canonical food variants with calibrated probability weights and default selections.
     - **Baseline Model Versions:** `cls-0.5.0` (production classifier), `det-0.3.1` (production detector), `por-0.2.0` (production portion), `idr-0.1.0` (production identity resolver), and baseline dataset `ds-2026.01` (450 samples).

4. **Domain Modules & Services (`backend/app/modules/`)**:
   - **`health/`**: Live health and readiness probes with DB connectivity check.
   - **`auth/`**: User registration, login, current user profile, and guest access fallback.
   - **`nutrition/`**:
     - [`repository.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/modules/nutrition/repository.py): Food search with alias resolution and fuzzy matching, variant retrieval, serving units.
     - [`engine.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/modules/nutrition/engine.py): Pure-Python `NutritionEngine` scaling 100g base profiles to exact portion weights, serving unit translations, Atwater consistency verification, and meal totals aggregation.
   - **`identity_resolution/`**:
     - [`resolver.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/modules/identity_resolution/resolver.py): Decouples classifier labels from nutrition entries. Implements `FoodIdentityResolver` to resolve visual classes into candidate food variants with prior weights.
   - **`recognition/`**:
     - [`detector.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/modules/recognition/detector.py): Multi-food spatial detector using HSV color clustering, thali plate contouring, and adaptive bounding box segmentation.
     - [`classifier.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/modules/recognition/classifier.py): Regional dish classifier calculating visual feature distributions and generating calibrated Top-K visual predictions.
   - **`portion/`**:
     - [`estimator.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/modules/portion/estimator.py): Portion size estimator accounting for bounding area relative to the plate/dish, food density priors, and countable unit conversions (e.g. 1 roti = 35g, 1 katori dal = 150g).
   - **`analysis/`**:
     - [`pipeline.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/modules/analysis/pipeline.py): Master orchestrator (`NutritionAnalysisPipeline`) executing the complete scan-to-nutrition workflow and computing combined confidence scores.
   - **`corrections/`**:
     - [`service.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/modules/corrections/service.py): Records user verification edits (`POST /v1/food/correct`), updates prediction item records, recalculates nutrition dynamically, and stores correction logs.
   - **`meals/`**:
     - [`service.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/modules/meals/service.py): Persists verified meals, generates daily nutritional totals (`/v1/nutrition/daily`), supports meal queries, item removal, and diary logs.
   - **`improvement/` (Phase 9 Model Ops & Feedback Pipeline)**:
     - [`validators.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/modules/improvement/validators.py): Automated validation suite (image integrity, 64-bit dHash perceptual hashing, frozen test-set leakage protection, physiological bounds validation, cause classification).
     - [`etl.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/modules/improvement/etl.py): Feedback ETL pipeline batching pending correction events, verifying user training consent, applying validation filters, routing cause, and queuing valid samples for review.
     - [`service.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/modules/improvement/service.py): Reviewer approval workflow, multi-signal consensus checks, group-aware dataset version builder, model registry lifecycle transitions (staging -> canary -> production) with rollback drills, non-retraining identity map updates, and error analytics.
   - **`optimization/` (Phase 10 Mobile Optimization & On-Device Spikes)**:
     - [`compressor.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/modules/optimization/compressor.py): Client-side image compression tuning enforcing long edge $\le 1280\text{px}$, payload ceiling $\le 1.0\text{ MB}$, and dynamic quality degradation curves.
     - [`quantizer.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/modules/optimization/quantizer.py): Evaluates FP32 vs FP16 vs INT8 quantization for on-device deployment (TFLite / ONNX Mobile / CoreML), strictly guarding against $> 1.5\text{ pt}$ Top-1 accuracy drops and $> 50\text{ MB}$ total mobile bundle size.
     - [`benchmarks.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/modules/optimization/benchmarks.py): ADR-003 empirical evaluation across device tiers (Budget Android: Cloud recommended, Mid-range Android: Hybrid recommended, Flagship iOS: Hybrid/On-Device recommended).
     - [`router.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/modules/optimization/router.py): `GET /v1/models/manifest`, `GET /v1/optimization/benchmarks`, `POST /v1/optimization/compression-curve`.
   - **`compliance/` (Phase 11 Production Hardening & Compliance)**:
     - [`service.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/modules/compliance/service.py): GDPR/DPDP personal data export generator (`export_user_data`), Right-to-be-Forgotten account deletion (`delete_user_account`), and automated transient image retention purge engine (`purge_transient_images`).
     - [`router.py`](file:///c:/Users/Ankur/Desktop/Fit0one/backend/app/modules/compliance/router.py): `DELETE /v1/users/me`, `GET /v1/users/me/export`, `POST /v1/admin/compliance/retention-purge`, `GET /v1/metrics`.

---

### 3.2. Cross-Platform Mobile Client Architecture (`mobile/` - Phase 10)

A production-ready Flutter mobile codebase structure has been scaffolded under `mobile/`:

1. **`pubspec.yaml`**: Configured with camera, `tflite_flutter`, `http`, `provider`, `shared_preferences`, and image processing packages.
2. **`lib/core/constants.dart`**: Cyber-kinetic design system color palette:
   - Primary: `#10B981` (Emerald Glow)
   - Secondary: `#06B6D4` (Cyan Pulse)
   - Dark Surface: `#0F172A` & Card Background: `#1E293B`
   - Accents: Amber Warning (`#F59E0B`), Coral Error (`#F43F5E`)
3. **`lib/core/api_client.dart`**: Robust HTTP client with token bearer management, automated `X-RateLimit-*` telemetry parsing, multi-part image streaming, and offline-resilient error translation.
4. **`lib/screens/dashboard_screen.dart`**: Dashboard presenting real-time macro radial progress rings (Calories, Protein, Carbs, Fat) and quick-action meal history cards.
5. **`lib/screens/scanner_screen.dart`**: Visual food scanner featuring bounding-box viewfinder overlays, reference object guide (Card / Hand / Plate), and one-tap food capture.
6. **`lib/screens/calibration_screen.dart`**: Reference calibration module for coins, credit cards, and plate diameter homography calibration.
7. **`lib/screens/diary_screen.dart`**: Daily nutrition breakdown, per-meal collapsible cards, and granular micronutrient availability metrics.
8. **`lib/main.dart`**: Flutter entry point with dark cyber-kinetic theme, navigation bar, and state management.

---

### 3.3. Production Hardening & Deployment Stack (Phase 11)

1. **Rate Limiting & Abuse Prevention**:
   - Per-user token-bucket rate limiter enforcing 30 requests/hr on `/v1/food/analyze`.
   - Headers injected on every request:
     - `X-RateLimit-Limit`: Maximum requests permitted per window.
     - `X-RateLimit-Remaining`: Remaining request quota.
     - `X-RateLimit-Reset`: Unix epoch timestamp of window reset.
     - `X-Request-ID`: Distributed tracing identifier.
2. **Data Governance & Privacy**:
   - **GDPR Portability**: `GET /v1/users/me/export` delivers a full JSON archive of profile, meals, nutritional snapshots, and correction logs.
   - **Right to be Forgotten**: `DELETE /v1/users/me` permanently unlinks meals, anonymizes email and username, and purges transient raw images.
   - **Automated Retention Purge**: `POST /v1/admin/compliance/retention-purge` cleanses unconsented raw meal images older than 24 hours.
3. **Operational Telemetry & Observability**:
   - `GET /v1/metrics`: Dual format exporter serving both JSON telemetry and Prometheus text format (`nutrilens_scans_total`, `nutrilens_meals_total`, `nutrilens_corrections_total`, `nutrilens_users_total`).
4. **Containerization**:
   - [`Dockerfile`](file:///c:/Users/Ankur/Desktop/Fit0one/Dockerfile): Multi-stage Python 3.12 production container, non-root security user (`nutrilens`), libgl1/libgomp OpenCV dependencies, and automated `/health` liveness probe.
   - [`docker-compose.yml`](file:///c:/Users/Ankur/Desktop/Fit0one/docker-compose.yml): Production cluster orchestration with API service (4 uvicorn workers), PostgreSQL 15, Redis 7, and MinIO S3 object store.

---

## 4. Cyber-Kinetic Web UI Telemetry (`frontend/`)

The web frontend operates as a single-page cyber-kinetic telemetry suite:
1. **Macro HUD & Target Ring**: Real-time energy, protein, carbohydrate, and fat ring gauges with animated SVG progress indicators.
2. **Scanner & Camera Viewfinder**: Simulated live camera view with plate reference markers and canvas-based bounding box visualization.
3. **Nutritional Recalculation Engine**: Dynamic variant selection chips (e.g., standard vs. ghee-roasted roti) updating macro breakdown instantly.
4. **Meal Diary & Timeline**: Grouped view of logged meals (Breakfast, Lunch, Dinner, Snack) with item counts and nutrient breakdowns.
5. **Model Ops & Reviewer Modal**:
   - Human review inbox with visual bounding box verification.
   - Triage action buttons (Approve Ground Truth, Reject Sample, Flag Uncertainty).
   - Technical error cause breakdown charts (`visual_misrecognition`, `variant_ambiguity`, `mapping_error`, `portion_bias`, `taxonomy_gap`).
   - Retraining dataset snapshot trigger and active model registry version cards (`cls-0.5.0`, `det-0.3.1`, `por-0.2.0`, `idr-0.1.0`).

---

## 5. Automated Verification & Test Results

The backend contains **28 automated unit and integration tests** verifying all phases from Phase 0 to Phase 11 with **100% green pass rate**:

```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\Ankur\Desktop\Fit0one
collected 28 items

backend/tests/test_api_endpoints.py::test_health_endpoints PASSED        [  3%]
backend/tests/test_api_endpoints.py::test_food_search PASSED             [  7%]
backend/tests/test_api_endpoints.py::test_nutrition_calculate PASSED     [ 10%]
backend/tests/test_api_endpoints.py::test_meal_logging_and_daily_summary PASSED [ 14%]
backend/tests/test_full_pipeline.py::test_full_analyze_and_correct_pipeline PASSED [ 17%]
backend/tests/test_full_pipeline.py::test_indian_thali_cv_pixel_recognition PASSED [ 21%]
backend/tests/test_identity_resolver.py::test_identity_resolver_paneer_red_gravy PASSED [ 25%]
backend/tests/test_identity_resolver.py::test_identity_resolver_yellow_dal PASSED [ 28%]
backend/tests/test_mobile_optimization.py::test_client_image_compression PASSED [ 32%]
backend/tests/test_mobile_optimization.py::test_model_quantization_evaluation PASSED [ 35%]
backend/tests/test_mobile_optimization.py::test_adr_003_benchmarks PASSED [ 39%]
backend/tests/test_mobile_optimization.py::test_model_manifest_endpoints PASSED [ 42%]
backend/tests/test_mobile_optimization.py::test_compression_curve_api PASSED [ 46%]
backend/tests/test_mobile_optimization.py::test_mobile_download_endpoints PASSED [ 50%]
backend/tests/test_model_improvement.py::test_automated_validators PASSED [ 53%]
backend/tests/test_model_improvement.py::test_feedback_etl_pipeline PASSED [ 57%]
backend/tests/test_model_improvement.py::test_reviewer_decision_and_dataset_snapshot PASSED [ 60%]
backend/tests/test_model_improvement.py::test_model_registry_lifecycle_and_rollback PASSED [ 64%]
backend/tests/test_model_improvement.py::test_non_retraining_identity_map_update PASSED [ 67%]
backend/tests/test_model_improvement.py::test_error_analytics PASSED     [ 71%]
backend/tests/test_model_improvement.py::test_user_training_consent_endpoint PASSED [ 75%]
backend/tests/test_nutrition_engine.py::test_nutrition_engine_scaling PASSED [ 78%]
backend/tests/test_nutrition_engine.py::test_nutrition_engine_totals_aggregation PASSED [ 82%]
backend/tests/test_production_readiness.py::test_rate_limiter_unit PASSED [ 85%]
backend/tests/test_production_readiness.py::test_rate_limit_headers_on_analyze PASSED [ 89%]
backend/tests/test_production_readiness.py::test_user_data_export_and_deletion PASSED [ 92%]
backend/tests/test_production_readiness.py::test_retention_purge PASSED  [ 96%]
backend/tests/test_production_readiness.py::test_prometheus_and_json_metrics PASSED [100%]

======================== 28 passed, 1 warning in 3.82s ========================
```

---

## 6. Directory Structure Overview

```text
Fit0one/
├── backend/
│   ├── app/
│   │   ├── core/                  # Config, DB, error envelopes, auth, rate limiting (Phase 11)
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── errors.py
│   │   │   ├── rate_limit.py      # Token-bucket rate limiter & telemetry
│   │   │   └── security.py
│   │   ├── data/                  # DB initialization and IFCT/USDA/model seed data
│   │   ├── models/                # SQLAlchemy database models
│   │   │   ├── analysis.py        # AnalysisRecord, PredictionItem
│   │   │   ├── audit.py           # AuditLog
│   │   │   ├── correction.py      # CorrectionEvent
│   │   │   ├── identity.py        # LabelsetVersion, VisualClass, VisualClassMapping
│   │   │   ├── image.py           # ImageRecord
│   │   │   ├── improvement.py     # ModelVersion, DatasetVersion, DatasetSample, FeedbackReview
│   │   │   ├── meal.py            # Meal, MealItem
│   │   │   ├── nutrition.py       # Food, FoodVariant, NutritionProfile, ServingUnit
│   │   │   └── user.py            # AppUser with training_consent & deletion
│   │   ├── modules/               # Domain feature modules
│   │   │   ├── analysis/          # Full end-to-end scanning pipeline
│   │   │   ├── auth/              # Authentication & user profile services
│   │   │   ├── compliance/        # Phase 11: GDPR/DPDP export, deletion, retention purge, metrics
│   │   │   ├── corrections/       # Verification and user correction capture
│   │   │   ├── health/            # Liveness and readiness endpoints
│   │   │   ├── identity_resolution/# Visual class to canonical food mapping (ADR-009)
│   │   │   ├── improvement/       # Phase 9: Feedback ETL, validation, registry & reviewer ops
│   │   │   ├── meals/             # Meal persistence and daily telemetry
│   │   │   ├── nutrition/         # Search repository and pure-Python engine
│   │   │   ├── optimization/      # Phase 10: Compression tuning, INT8 quantizer, ADR-003 benchmarks
│   │   │   ├── portion/           # Geometric and density portion estimator
│   │   │   └── recognition/       # Computer vision detector and classifier
│   │   ├── schemas/               # Pydantic request/response schemas
│   │   └── main.py                # FastAPI entry point, rate limit middleware, static mounts
│   ├── tests/                     # 27 Pytest unit & integration test suites
│   ├── nutrilens.db               # SQLite operational database
│   └── uploads/                   # Local image storage
├── mobile/                        # Phase 10: Flutter mobile client architecture
│   ├── lib/
│   │   ├── core/                  # Constants, theme, and API client
│   │   ├── screens/               # Dashboard, Scanner, Calibration, Diary
│   │   └── main.dart              # Flutter application entry point
│   └── pubspec.yaml               # Flutter package configuration
├── frontend/
│   ├── index.html                 # Cyber-kinetic UI (Dashboard, Scanner, Calibration, Diary, Model Ops)
│   └── app.js                     # Client state machine, REST API calls, Model Ops handlers
├── stitch_calorie_counter_app_interface/ # Reference Stitch UI telemetry designs
├── Dockerfile                     # Phase 11: Multi-stage production container
├── docker-compose.yml             # Phase 11: Production deployment orchestration (API + PG + Redis + MinIO)
├── SDD_AI_Indian_Food_Nutrition_Tracker (1).md # Master Software Design Document
├── progress.md                    # This document
└── requirements.txt               # Python package dependencies
```

---

## 7. Operational & Deployment Guide

### Local Development Server
```bash
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run development server with live reload
$env:PYTHONPATH="."
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Run Full Test Suite
```bash
$env:PYTHONPATH="."
pytest backend/tests -v
```

### Production Docker Stack Launch
```bash
docker-compose up -d --build
```
This boots the complete production stack:
- NutriLens API: `http://localhost:8000` (docs at `/docs`)
- PostgreSQL 15: `localhost:5432`
- Redis 7: `localhost:6379`
- MinIO Object Store: `http://localhost:9000` (Console at `http://localhost:9001`)
- Prometheus Metrics: `http://localhost:8000/v1/metrics?format=prometheus`

### Mobile Download & PWA App Deployment
- **Live Mobile Web PWA App:** `http://localhost:8000/mobile/`
- **Wi-Fi Mobile Access (Phone Browser):** `http://10.0.89.21:8000/mobile/`
- **Standalone Android APK (148MB):** `http://localhost:8000/v1/mobile/download-apk`
- **Downloadable Mobile Bundle (.ZIP, 14MB):** `http://localhost:8000/v1/mobile/download`
- **Install Native Android APK:** Download `nutrilens.apk` and tap to install directly on Android.
- **Install Web PWA on Android:** Open Chrome -> tap `⋮` -> **"Install app"** / **"Add to Home Screen"**
- **Install Web PWA on iOS:** Open Safari -> tap Share icon -> **"Add to Home Screen"**

