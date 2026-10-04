import 'dart:convert';
import 'dart:math';
import 'package:shared_preferences/shared_preferences.dart';

/// Autonomous On-Device Nutrition Engine for NutriLens Mobile
/// Provides 100% offline functionality without requiring an active backend or laptop.
class OfflineNutritionEngine {
  static const String _diaryKey = "nutrilens_offline_diary";

  // Curated IFCT 2017 & ICMR-NIN Indian Food Nutritional Profiles (per 100g)
  static final Map<String, Map<String, dynamic>> canonicalDatabase = {
    'roti': {
      'name': 'Roti / Phulka',
      'category': 'Breads',
      'default_g': 60.0,
      'unit': 'piece',
      'unit_weight_g': 30.0,
      'variants': ['Dry Roasted', 'With Ghee'],
      'energy_100g': 297.0,
      'protein_100g': 9.6,
      'carbs_100g': 55.4,
      'fat_100g': 3.2,
    },
    'dal_tadka': {
      'name': 'Dal Tadka (Yellow Lentils)',
      'category': 'Dal & Legumes',
      'default_g': 150.0,
      'unit': 'katori',
      'unit_weight_g': 150.0,
      'variants': ['Homestyle Light', 'Restaurant Tadka'],
      'energy_100g': 112.0,
      'protein_100g': 5.6,
      'carbs_100g': 12.1,
      'fat_100g': 4.1,
    },
    'dal_makhani': {
      'name': 'Dal Makhani',
      'category': 'Dal & Legumes',
      'default_g': 150.0,
      'unit': 'katori',
      'unit_weight_g': 150.0,
      'variants': ['Standard Cream', 'Light Gravy'],
      'energy_100g': 145.0,
      'protein_100g': 5.1,
      'carbs_100g': 14.2,
      'fat_100g': 7.8,
    },
    'rice': {
      'name': 'Steamed Basmati Rice',
      'category': 'Grains',
      'default_g': 150.0,
      'unit': 'bowl',
      'unit_weight_g': 150.0,
      'variants': ['Plain Steamed', 'Jeera Flavored'],
      'energy_100g': 130.0,
      'protein_100g': 2.6,
      'carbs_100g': 28.3,
      'fat_100g': 0.4,
    },
    'paneer_butter_masala': {
      'name': 'Paneer Butter Masala',
      'category': 'Curries',
      'default_g': 140.0,
      'unit': 'portion',
      'unit_weight_g': 140.0,
      'variants': ['Rich Makhani Gravy', 'Homestyle Light'],
      'energy_100g': 228.0,
      'protein_100g': 9.5,
      'carbs_100g': 6.5,
      'fat_100g': 19.0,
    },
    'aloo_gobi': {
      'name': 'Aloo Gobi Matar Sabzi',
      'category': 'Sabzi',
      'default_g': 130.0,
      'unit': 'katori',
      'unit_weight_g': 130.0,
      'variants': ['Dry Roasted', 'Light Gravy'],
      'energy_100g': 95.0,
      'protein_100g': 2.2,
      'carbs_100g': 12.5,
      'fat_100g': 4.0,
    },
    'chana_masala': {
      'name': 'Chana Masala (Chickpeas)',
      'category': 'Curries',
      'default_g': 150.0,
      'unit': 'katori',
      'unit_weight_g': 150.0,
      'variants': ['Punjabi Spicy', 'Low-Oil Homestyle'],
      'energy_100g': 135.0,
      'protein_100g': 6.0,
      'carbs_100g': 18.0,
      'fat_100g': 4.0,
    },
    'curd': {
      'name': 'Plain Dahi / Curd',
      'category': 'Accompaniments',
      'default_g': 100.0,
      'unit': 'katori',
      'unit_weight_g': 100.0,
      'variants': ['Whole Milk', 'Skimmed Milk'],
      'energy_100g': 61.0,
      'protein_100g': 3.5,
      'carbs_100g': 4.7,
      'fat_100g': 3.1,
    },
  };

  /// Generates an on-device CV scan result simulating intelligent Indian thali recognition
  static Map<String, dynamic> generateScanResult() {
    final rand = Random();
    final mealCombos = [
      ['roti', 'dal_tadka', 'rice', 'paneer_butter_masala'],
      ['roti', 'dal_makhani', 'aloo_gobi', 'curd'],
      ['rice', 'chana_masala', 'roti', 'curd'],
    ];

    final chosenKeys = mealCombos[rand.nextInt(mealCombos.length)];
    final items = <Map<String, dynamic>>[];
    double totalKcal = 0;
    double totalProtein = 0;
    double totalCarbs = 0;
    double totalFat = 0;

    for (int i = 0; i < chosenKeys.length; i++) {
      final key = chosenKeys[i];
      final profile = canonicalDatabase[key]!;
      final grams = (profile['default_g'] as double);

      final ratio = grams / 100.0;
      final kcal = (profile['energy_100g'] as double) * ratio;
      final protein = (profile['protein_100g'] as double) * ratio;
      final carbs = (profile['carbs_100g'] as double) * ratio;
      final fat = (profile['fat_100g'] as double) * ratio;

      totalKcal += kcal;
      totalProtein += protein;
      totalCarbs += carbs;
      totalFat += fat;

      items.add({
        'item_id': 'local_item_${i + 1}',
        'food_id': key,
        'variant_id': '${key}_var_1',
        'food_name': profile['name'],
        'portion_g': grams,
        'confidence': 0.94 - (i * 0.03),
        'is_offline': true,
        'nutrition': {
          'energy_kcal': {'value': double.parse(kcal.toStringAsFixed(1))},
          'protein_g': {'value': double.parse(protein.toStringAsFixed(1))},
          'carbs_g': {'value': double.parse(carbs.toStringAsFixed(1))},
          'fat_g': {'value': double.parse(fat.toStringAsFixed(1))},
        },
      });
    }

    return {
      'analysis_id': 'offline_scan_${DateTime.now().millisecondsSinceEpoch}',
      'mode': 'on_device_autonomous',
      'items': items,
      'totals': {
        'energy_kcal': {'value': double.parse(totalKcal.toStringAsFixed(1))},
        'protein_g': {'value': double.parse(totalProtein.toStringAsFixed(1))},
        'carbs_g': {'value': double.parse(totalCarbs.toStringAsFixed(1))},
        'fat_g': {'value': double.parse(totalFat.toStringAsFixed(1))},
      },
    };
  }

  /// Calculates dynamic nutrition for modified portions offline
  static Map<String, dynamic> recalculate(List<dynamic> items) {
    double totalKcal = 0;
    double totalProtein = 0;
    double totalCarbs = 0;
    double totalFat = 0;

    for (var item in items) {
      final foodId = item['food_id'] ?? 'roti';
      final grams = (item['quantity'] ?? item['portion_g'] ?? 100.0).toDouble();
      final profile = canonicalDatabase[foodId] ?? canonicalDatabase['roti']!;

      final ratio = grams / 100.0;
      final kcal = (profile['energy_100g'] as double) * ratio;
      final protein = (profile['protein_100g'] as double) * ratio;
      final carbs = (profile['carbs_100g'] as double) * ratio;
      final fat = (profile['fat_100g'] as double) * ratio;

      totalKcal += kcal;
      totalProtein += protein;
      totalCarbs += carbs;
      totalFat += fat;
    }

    return {
      'totals': {
        'energy_kcal': {'value': double.parse(totalKcal.toStringAsFixed(1))},
        'protein_g': {'value': double.parse(totalProtein.toStringAsFixed(1))},
        'carbs_g': {'value': double.parse(totalCarbs.toStringAsFixed(1))},
        'fat_g': {'value': double.parse(totalFat.toStringAsFixed(1))},
      }
    };
  }

  /// Persists a logged meal to on-device SharedPreferences
  static Future<void> saveLocalMeal(Map<String, dynamic> mealData) async {
    final prefs = await SharedPreferences.getInstance();
    final existingJson = prefs.getString(_diaryKey);
    List<dynamic> diary = [];
    if (existingJson != null && existingJson.isNotEmpty) {
      try {
        diary = jsonDecode(existingJson);
      } catch (_) {
        diary = [];
      }
    }

    // Ensure meal has an ID and timestamp
    final meal = Map<String, dynamic>.from(mealData);
    meal['id'] ??= 'local_meal_${DateTime.now().millisecondsSinceEpoch}';
    meal['local_date'] ??= DateTime.now().toIso8601String().split('T')[0];
    meal['created_at'] ??= DateTime.now().toIso8601String();

    diary.insert(0, meal);
    await prefs.setString(_diaryKey, jsonEncode(diary));
  }

  /// Loads daily totals and meals for the specified date directly from device storage
  static Future<Map<String, dynamic>> getLocalDailyTelemetry(String dateStr) async {
    final prefs = await SharedPreferences.getInstance();
    final existingJson = prefs.getString(_diaryKey);
    List<dynamic> allMeals = [];
    if (existingJson != null && existingJson.isNotEmpty) {
      try {
        allMeals = jsonDecode(existingJson);
      } catch (_) {
        allMeals = [];
      }
    }

    final dateMeals = allMeals.where((m) => (m['local_date'] ?? '').toString().startsWith(dateStr)).toList();

    double totalKcal = 0;
    double totalProtein = 0;
    double totalCarbs = 0;
    double totalFat = 0;

    for (var m in dateMeals) {
      final items = (m['items'] as List?) ?? [];
      for (var it in items) {
        final snap = it['nutrition_snapshot'] ?? it['nutrition'] ?? {};
        totalKcal += ((snap['energy_kcal']?['value'] ?? 0) as num).toDouble();
        totalProtein += ((snap['protein_g']?['value'] ?? 0) as num).toDouble();
        totalCarbs += ((snap['carbs_g']?['value'] ?? 0) as num).toDouble();
        totalFat += ((snap['fat_g']?['value'] ?? 0) as num).toDouble();
      }
    }

    return {
      'date': dateStr,
      'mode': 'on_device_local',
      'meals': dateMeals,
      'totals': {
        'energy_kcal': {'value': double.parse(totalKcal.toStringAsFixed(1))},
        'protein_g': {'value': double.parse(totalProtein.toStringAsFixed(1))},
        'carbs_g': {'value': double.parse(totalCarbs.toStringAsFixed(1))},
        'fat_g': {'value': double.parse(totalFat.toStringAsFixed(1))},
      }
    };
  }
}
