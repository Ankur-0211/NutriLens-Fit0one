from sqlalchemy.orm import Session
from backend.app.models.nutrition import (
    NutritionSource,
    FoodCategory,
    Food,
    FoodAlias,
    FoodVariant,
    ServingUnit,
    NutritionProfile,
)
from backend.app.models.identity import (
    LabelsetVersion,
    VisualClass,
    IdentityMapVersion,
    VisualClassMapping,
)
from backend.app.models.improvement import (
    ModelVersion,
    DatasetVersion,
    DatasetSample,
)

def seed_database(db: Session):
    seed_improvement_models(db)

    # Check if already seeded
    if db.query(NutritionSource).first():
        return

    # 1. Sources
    sources = [
        NutritionSource(id="IFCT2017", name="Indian Food Composition Tables 2017", url="https://www.nin.res.in", license="ICMR-NIN Educational/Research", version="2017"),
        NutritionSource(id="USDA_FDC", name="USDA FoodData Central", url="https://fdc.nal.usda.gov", license="Public Domain", version="2024"),
        NutritionSource(id="RECIPE_CALC", name="Standard Recipe Calculation Model", notes="Dietitian validated nutrient summation with yield factors", version="v1.0"),
    ]
    for s in sources:
        db.add(s)
    db.commit()

    # 2. Categories
    categories_data = [
        {"id": 1, "slug": "breads", "name": "Roti & Breads"},
        {"id": 2, "slug": "dals", "name": "Dal & Legumes"},
        {"id": 3, "slug": "rice_grains", "name": "Rice & Grain Dishes"},
        {"id": 4, "slug": "paneer", "name": "Paneer Dishes"},
        {"id": 5, "slug": "sabzi", "name": "Sabzi (Vegetables)"},
        {"id": 6, "slug": "curries", "name": "Curries & Gravies"},
        {"id": 7, "slug": "tiffin", "name": "South Indian Tiffin"},
        {"id": 8, "slug": "accompaniments", "name": "Accompaniments & Dairy"},
        {"id": 9, "slug": "snacks", "name": "Snacks & Savories"},
        {"id": 10, "slug": "sweets", "name": "Sweets & Desserts"},
        {"id": 11, "slug": "beverages", "name": "Beverages"},
    ]
    for c in categories_data:
        db.add(FoodCategory(id=c["id"], slug=c["slug"], name=c["name"]))
    db.commit()

    # 3. Canonical Foods + Aliases + Variants + Serving Units + Nutrition Profiles
    foods_data = [
        # --- Breads ---
        {
            "id": "roti_plain",
            "name": "Roti / Phulka",
            "cat_id": 1,
            "is_countable": True,
            "default_unit": "roti",
            "default_grams": 35.0,
            "density": None,
            "aliases": ["roti", "phulka", "chapati", "chapathi", "rotli"],
            "units": [("roti", 35.0, "1 Roti (35g)"), ("piece", 35.0, "1 Piece"), ("g", 1.0, "Grams")],
            "variants": [
                {
                    "id": "roti_plain:default", "label": "Standard Phulka (no ghee)", "prep": "dry_roasted", "is_default": True,
                    "kcal": 104.0, "p": 3.1, "c": 22.0, "f": 0.4, "fiber": 3.4, "sugar": 0.3, "sodium": 120.0,
                    "kmin": 95.0, "kmax": 115.0,
                    "micros": {"calcium_mg": {"value": 14.0}, "iron_mg": {"value": 1.2}, "potassium_mg": {"value": 110.0}, "vitamin_b12_ug": {"availability": "missing"}},
                },
                {
                    "id": "roti_plain:with_ghee", "label": "Roti with Ghee (1 tsp)", "prep": "ghee_applied", "is_default": False,
                    "kcal": 145.0, "p": 3.1, "c": 22.0, "f": 5.0, "fiber": 3.4, "sugar": 0.3, "sodium": 120.0,
                    "kmin": 130.0, "kmax": 165.0,
                    "micros": {"calcium_mg": {"value": 15.0}, "iron_mg": {"value": 1.2}, "potassium_mg": {"value": 110.0}, "vitamin_a_ug": {"value": 35.0}},
                },
            ],
        },
        {
            "id": "paratha_plain",
            "name": "Plain Paratha",
            "cat_id": 1,
            "is_countable": True,
            "default_unit": "paratha",
            "default_grams": 65.0,
            "aliases": ["paratha", "plain paratha", "tawa paratha", "laccha paratha"],
            "units": [("paratha", 65.0, "1 Paratha (65g)"), ("g", 1.0, "Grams")],
            "variants": [
                {
                    "id": "paratha_plain:default", "label": "Tawa Paratha (moderate ghee/oil)", "prep": "pan_fried", "is_default": True,
                    "kcal": 210.0, "p": 4.5, "c": 28.0, "f": 9.0, "fiber": 3.8, "sugar": 0.4, "sodium": 180.0,
                    "kmin": 180.0, "kmax": 250.0,
                    "micros": {"calcium_mg": {"value": 22.0}, "iron_mg": {"value": 1.6}, "potassium_mg": {"value": 130.0}},
                },
                {
                    "id": "paratha_plain:home_light", "label": "Home Style (Light oil)", "prep": "pan_roasted", "is_default": False,
                    "kcal": 170.0, "p": 4.5, "c": 28.0, "f": 4.5, "fiber": 3.8, "sugar": 0.4, "sodium": 150.0,
                    "kmin": 150.0, "kmax": 190.0,
                    "micros": {"calcium_mg": {"value": 20.0}, "iron_mg": {"value": 1.6}},
                },
            ],
        },
        # --- Dals ---
        {
            "id": "dal_tadka",
            "name": "Dal Tadka",
            "cat_id": 2,
            "is_countable": False,
            "default_unit": "katori",
            "default_grams": 150.0,
            "density": 1.05,
            "aliases": ["dal tadka", "yellow dal", "dal fry", "toor dal", "yellow daal"],
            "units": [("katori", 150.0, "1 Standard Katori (150g)"), ("bowl", 200.0, "1 Large Bowl (200g)"), ("cup", 200.0, "1 Cup"), ("g", 1.0, "Grams")],
            "variants": [
                {
                    "id": "dal_tadka:default", "label": "Standard Home Tadka", "prep": "tempered_dal", "is_default": True,
                    "kcal": 152.0, "p": 7.4, "c": 21.0, "f": 4.2, "fiber": 4.8, "sugar": 1.2, "sodium": 340.0,
                    "kmin": 130.0, "kmax": 180.0,
                    "micros": {"calcium_mg": {"value": 36.0}, "iron_mg": {"value": 1.9}, "potassium_mg": {"value": 310.0}, "folate_ug": {"value": 65.0}},
                },
                {
                    "id": "dal_tadka:restaurant_rich", "label": "Restaurant Double Tadka (Ghee/Butter)", "prep": "rich_tadka", "is_default": False,
                    "kcal": 215.0, "p": 7.4, "c": 21.0, "f": 11.0, "fiber": 4.8, "sugar": 1.4, "sodium": 480.0,
                    "kmin": 190.0, "kmax": 260.0,
                    "micros": {"calcium_mg": {"value": 42.0}, "iron_mg": {"value": 1.9}, "vitamin_a_ug": {"value": 45.0}},
                },
            ],
        },
        {
            "id": "dal_makhani",
            "name": "Dal Makhani",
            "cat_id": 2,
            "is_countable": False,
            "default_unit": "katori",
            "default_grams": 150.0,
            "density": 1.08,
            "aliases": ["dal makhani", "dal makhni", "black dal", "maa ki dal", "kaali dal"],
            "units": [("katori", 150.0, "1 Standard Katori (150g)"), ("bowl", 200.0, "1 Bowl (200g)"), ("g", 1.0, "Grams")],
            "variants": [
                {
                    "id": "dal_makhani:default", "label": "Creamy Black Dal (Butter & Cream)", "prep": "slow_cooked_cream", "is_default": True,
                    "kcal": 280.0, "p": 8.8, "c": 24.5, "f": 16.0, "fiber": 6.2, "sugar": 2.0, "sodium": 490.0,
                    "kmin": 240.0, "kmax": 340.0,
                    "micros": {"calcium_mg": {"value": 85.0}, "iron_mg": {"value": 2.8}, "potassium_mg": {"value": 380.0}},
                },
            ],
        },
        # --- Paneer Dishes ---
        {
            "id": "paneer_butter_masala",
            "name": "Paneer Butter Masala",
            "cat_id": 4,
            "is_countable": False,
            "default_unit": "katori",
            "default_grams": 150.0,
            "density": 1.06,
            "aliases": ["paneer butter masala", "paneer makhani", "pbm", "paneer masala", "butter paneer"],
            "units": [("katori", 150.0, "1 Standard Katori (150g)"), ("bowl", 200.0, "1 Large Bowl (200g)"), ("g", 1.0, "Grams")],
            "variants": [
                {
                    "id": "paneer_butter_masala:default", "label": "Standard Restaurant Style", "prep": "butter_cream_gravy", "is_default": True,
                    "kcal": 365.0, "p": 13.5, "c": 11.8, "f": 29.5, "fiber": 2.1, "sugar": 5.4, "sodium": 610.0,
                    "kmin": 310.0, "kmax": 440.0,
                    "micros": {"calcium_mg": {"value": 280.0}, "iron_mg": {"value": 1.4}, "potassium_mg": {"value": 220.0}, "vitamin_a_ug": {"value": 68.0}},
                },
                {
                    "id": "paneer_butter_masala:home_light", "label": "Home Style (Low butter/cream)", "prep": "home_gravy", "is_default": False,
                    "kcal": 260.0, "p": 13.0, "c": 10.5, "f": 18.5, "fiber": 2.1, "sugar": 3.8, "sodium": 420.0,
                    "kmin": 220.0, "kmax": 300.0,
                    "micros": {"calcium_mg": {"value": 260.0}, "iron_mg": {"value": 1.4}},
                },
            ],
        },
        {
            "id": "palak_paneer",
            "name": "Palak Paneer",
            "cat_id": 4,
            "is_countable": False,
            "default_unit": "katori",
            "default_grams": 150.0,
            "aliases": ["palak paneer", "saag paneer", "spinach paneer"],
            "units": [("katori", 150.0, "1 Katori (150g)"), ("bowl", 200.0, "1 Bowl (200g)"), ("g", 1.0, "Grams")],
            "variants": [
                {
                    "id": "palak_paneer:default", "label": "Spinach Cottage Cheese Gravy", "prep": "blanched_puree", "is_default": True,
                    "kcal": 240.0, "p": 12.0, "c": 9.0, "f": 17.5, "fiber": 4.5, "sugar": 2.2, "sodium": 480.0,
                    "kmin": 200.0, "kmax": 290.0,
                    "micros": {"calcium_mg": {"value": 310.0}, "iron_mg": {"value": 3.6}, "vitamin_a_ug": {"value": 180.0}, "folate_ug": {"value": 90.0}},
                }
            ],
        },
        # --- Rice & Grains ---
        {
            "id": "basmati_rice_steamed",
            "name": "Steamed Basmati Rice",
            "cat_id": 3,
            "is_countable": False,
            "default_unit": "katori",
            "default_grams": 150.0,
            "aliases": ["steamed rice", "plain rice", "white rice", "chawal", "boiled rice"],
            "units": [("katori", 150.0, "1 Katori (150g)"), ("cup", 160.0, "1 Cup (160g)"), ("plate", 250.0, "1 Full Plate (250g)"), ("g", 1.0, "Grams")],
            "variants": [
                {
                    "id": "basmati_rice_steamed:default", "label": "Plain Boiled Rice", "prep": "steamed", "is_default": True,
                    "kcal": 195.0, "p": 3.8, "c": 43.5, "f": 0.6, "fiber": 1.2, "sugar": 0.1, "sodium": 5.0,
                    "kmin": 180.0, "kmax": 210.0,
                    "micros": {"calcium_mg": {"value": 10.0}, "iron_mg": {"value": 0.8}, "potassium_mg": {"value": 55.0}},
                }
            ],
        },
        {
            "id": "jeera_rice",
            "name": "Jeera Rice",
            "cat_id": 3,
            "is_countable": False,
            "default_unit": "katori",
            "default_grams": 150.0,
            "aliases": ["jeera rice", "cumin rice", "jeera chawal"],
            "units": [("katori", 150.0, "1 Katori (150g)"), ("plate", 250.0, "1 Plate"), ("g", 1.0, "Grams")],
            "variants": [
                {
                    "id": "jeera_rice:default", "label": "Cumin Tempered Rice with Ghee", "prep": "ghee_tempered", "is_default": True,
                    "kcal": 240.0, "p": 4.0, "c": 43.0, "f": 5.5, "fiber": 1.5, "sugar": 0.2, "sodium": 180.0,
                    "kmin": 210.0, "kmax": 280.0,
                    "micros": {"calcium_mg": {"value": 22.0}, "iron_mg": {"value": 1.4}, "potassium_mg": {"value": 75.0}},
                }
            ],
        },
        # --- Accompaniments ---
        {
            "id": "curd_plain",
            "name": "Plain Curd / Dahi",
            "cat_id": 8,
            "is_countable": False,
            "default_unit": "katori",
            "default_grams": 150.0,
            "density": 1.03,
            "aliases": ["curd", "dahi", "plain curd", "yogurt", "plain yogurt"],
            "units": [("katori", 150.0, "1 Katori (150g)"), ("cup", 200.0, "1 Cup (200g)"), ("g", 1.0, "Grams")],
            "variants": [
                {
                    "id": "curd_plain:default", "label": "Full Cream Cow/Buffalo Dahi", "prep": "cultured", "is_default": True,
                    "kcal": 98.0, "p": 4.8, "c": 6.2, "f": 6.0, "fiber": 0.0, "sugar": 5.8, "sodium": 75.0,
                    "kmin": 90.0, "kmax": 110.0,
                    "micros": {"calcium_mg": {"value": 180.0}, "vitamin_b12_ug": {"value": 0.4}, "potassium_mg": {"value": 210.0}},
                }
            ],
        },
    ]

    for item in foods_data:
        food = Food(
            id=item["id"],
            display_name=item["name"],
            category_id=item["cat_id"],
            is_countable=item["is_countable"],
            default_unit=item["default_unit"],
            default_grams=item["default_grams"],
            density_g_per_ml=item.get("density"),
            status="active",
        )
        db.add(food)
        db.commit()

        # Aliases
        for a in item["aliases"]:
            db.add(FoodAlias(food_id=food.id, alias=a, lang="en"))

        # Serving units
        for u, g, label in item["units"]:
            db.add(ServingUnit(food_id=food.id, unit=u, grams=g, label=label, source_id="IFCT2017"))

        # Variants & Nutrition Profiles
        for v in item["variants"]:
            variant = FoodVariant(
                id=v["id"],
                food_id=food.id,
                label=v["label"],
                preparation=v.get("prep"),
                is_default=v["is_default"],
            )
            db.add(variant)
            db.commit()

            prof = NutritionProfile(
                food_variant_id=variant.id,
                basis_g=100.0,
                energy_kcal=v["kcal"],
                kcal_min=v.get("kmin"),
                kcal_max=v.get("kmax"),
                protein_g=v["p"],
                carbs_g=v["c"],
                fat_g=v["f"],
                fiber_g=v["fiber"],
                sugar_g=v["sugar"],
                sodium_mg=v["sodium"],
                micros=v["micros"],
                source_id="IFCT2017",
                version="nut-2026.01",
                is_current=True,
            )
            db.add(prof)

    db.commit()

    # 4. Identity Resolution Layer Seeds (ADR-009)
    # Labelset Version
    db.add(LabelsetVersion(id="vis-2026.01", notes="Initial curated Indian food visual label set"))
    db.commit()

    # Visual Classes
    v_classes = [
        {"id": "paneer_red_gravy", "name": "Paneer in Red/Orange Gravy", "coarse": "curry"},
        {"id": "shahi_paneer_yellow", "name": "Paneer in Yellow/Cream Gravy", "coarse": "curry"},
        {"id": "yellow_dal", "name": "Yellow Dal Tadka", "coarse": "dal"},
        {"id": "black_dal_gravy", "name": "Creamy Black Dal", "coarse": "dal"},
        {"id": "flatbread_roti", "name": "Roasted Flatbread / Roti", "coarse": "bread"},
        {"id": "layered_flatbread_paratha", "name": "Layered Paratha", "coarse": "bread"},
        {"id": "white_rice_grain", "name": "Steamed White Basmati Rice", "coarse": "rice"},
        {"id": "spiced_rice_dish", "name": "Jeera or Spiced Rice", "coarse": "rice"},
        {"id": "curd_bowl", "name": "Plain Curd / Dahi in Bowl", "coarse": "accompaniment"},
    ]
    for vc in v_classes:
        db.add(VisualClass(id=vc["id"], labelset_version="vis-2026.01", display_name=vc["name"], coarse_class=vc["coarse"]))
    db.commit()

    # Identity Map Version
    db.add(IdentityMapVersion(id="idmap-2026.01", labelset_version="vis-2026.01", reviewed_by="Lead Nutritionist & ML Lead", notes="Phase 2 calibrated visual-to-canonical mappings"))
    db.commit()

    # Visual Class Mappings
    mappings = [
        {"v_id": "paneer_red_gravy", "target": "paneer_butter_masala:default", "w": 0.85, "def": True},
        {"v_id": "paneer_red_gravy", "target": "paneer_butter_masala:home_light", "w": 0.15, "def": False},
        {"v_id": "yellow_dal", "target": "dal_tadka:default", "w": 0.90, "def": True},
        {"v_id": "yellow_dal", "target": "dal_tadka:restaurant_rich", "w": 0.10, "def": False},
        {"v_id": "black_dal_gravy", "target": "dal_makhani:default", "w": 1.0, "def": True},
        {"v_id": "flatbread_roti", "target": "roti_plain:default", "w": 0.85, "def": True},
        {"v_id": "flatbread_roti", "target": "roti_plain:with_ghee", "w": 0.15, "def": False},
        {"v_id": "layered_flatbread_paratha", "target": "paratha_plain:default", "w": 0.80, "def": True},
        {"v_id": "layered_flatbread_paratha", "target": "paratha_plain:home_light", "w": 0.20, "def": False},
        {"v_id": "white_rice_grain", "target": "basmati_rice_steamed:default", "w": 1.0, "def": True},
        {"v_id": "spiced_rice_dish", "target": "jeera_rice:default", "w": 1.0, "def": True},
        {"v_id": "curd_bowl", "target": "curd_plain:default", "w": 1.0, "def": True},
    ]

    for m in mappings:
        db.add(
            VisualClassMapping(
                identity_map_version="idmap-2026.01",
                visual_class_id=m["v_id"],
                labelset_version="vis-2026.01",
                food_variant_id=m["target"],
                weight=m["w"],
                is_default=m["def"],
            )
        )
    db.commit()

    seed_improvement_models(db)

def seed_improvement_models(db: Session):
    if db.query(ModelVersion).first():
        return

    # Baseline Model Versions in Production (SDD Section 22 line 1454, Section 25.1)
    models = [
        ModelVersion(
            id="cls-0.5.0",
            kind="classifier",
            mlflow_run_id="run_cls_2026_01",
            labelset_version="vis-2026.01",
            dataset_version="ds-2026.01",
            stage="production",
            active_traffic_pct=100.0,
            metrics={"top1": 0.88, "top3": 0.96, "ece": 0.08, "macro_f1": 0.86},
            notes="Baseline ResNet/ViT hybrid classifier for Indian food visual classes",
        ),
        ModelVersion(
            id="det-0.3.1",
            kind="detector",
            mlflow_run_id="run_det_2026_01",
            labelset_version="vis-2026.01",
            dataset_version="ds-2026.01",
            stage="production",
            active_traffic_pct=100.0,
            metrics={"mAP50": 0.82, "major_item_recall": 0.91},
            notes="Multi-food contour & plate boundary detector",
        ),
        ModelVersion(
            id="por-0.2.0",
            kind="portion",
            mlflow_run_id="run_por_2026_01",
            labelset_version="vis-2026.01",
            dataset_version="ds-2026.01",
            stage="production",
            active_traffic_pct=100.0,
            metrics={"mdape": 0.22, "within_30pct": 0.74},
            notes="Geometric bounding volume + density prior portion estimator",
        ),
        ModelVersion(
            id="idr-0.1.0",
            kind="identity_resolver",
            mlflow_run_id="run_idr_2026_01",
            labelset_version="vis-2026.01",
            dataset_version="ds-2026.01",
            stage="production",
            active_traffic_pct=100.0,
            metrics={"top1_mapping_acc": 0.94},
            notes="Deterministic Food Identity Resolver (ADR-009)",
        ),
    ]
    for mdl in models:
        db.add(mdl)

    # Initial Dataset Version baseline
    if not db.query(DatasetVersion).first():
        db.add(
            DatasetVersion(
                id="ds-2026.01",
                dvc_ref="git:seed_baseline_v1",
                notes="Initial curated baseline benchmark dataset for 9 Indian food classes",
                num_samples=450,
            )
        )
    db.commit()

