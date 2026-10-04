import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

class UserProfile {
  final String name;
  final int targetCalories;
  final double targetProteinG;
  final double targetCarbsG;
  final double targetFatG;
  final String dietaryPreference; // 'Vegetarian', 'Non-Vegetarian', 'Vegan', 'Jain', 'Eggetarian'
  final bool hasCompletedOnboarding;

  const UserProfile({
    this.name = 'Nutrition Cadet',
    this.targetCalories = 2100,
    this.targetProteinG = 120.0,
    this.targetCarbsG = 240.0,
    this.targetFatG = 60.0,
    this.dietaryPreference = 'Vegetarian',
    this.hasCompletedOnboarding = false,
  });

  Map<String, dynamic> toJson() => {
    'name': name,
    'target_calories': targetCalories,
    'target_protein_g': targetProteinG,
    'target_carbs_g': targetCarbsG,
    'target_fat_g': targetFatG,
    'dietary_preference': dietaryPreference,
    'has_completed_onboarding': hasCompletedOnboarding,
  };

  factory UserProfile.fromJson(Map<String, dynamic> json) {
    return UserProfile(
      name: json['name'] ?? 'Nutrition Cadet',
      targetCalories: (json['target_calories'] ?? 2100) as int,
      targetProteinG: ((json['target_protein_g'] ?? 120.0) as num).toDouble(),
      targetCarbsG: ((json['target_carbs_g'] ?? 240.0) as num).toDouble(),
      targetFatG: ((json['target_fat_g'] ?? 60.0) as num).toDouble(),
      dietaryPreference: json['dietary_preference'] ?? 'Vegetarian',
      hasCompletedOnboarding: json['has_completed_onboarding'] ?? false,
    );
  }

  UserProfile copyWith({
    String? name,
    int? targetCalories,
    double? targetProteinG,
    double? targetCarbsG,
    double? targetFatG,
    String? dietaryPreference,
    bool? hasCompletedOnboarding,
  }) {
    return UserProfile(
      name: name ?? this.name,
      targetCalories: targetCalories ?? this.targetCalories,
      targetProteinG: targetProteinG ?? this.targetProteinG,
      targetCarbsG: targetCarbsG ?? this.targetCarbsG,
      targetFatG: targetFatG ?? this.targetFatG,
      dietaryPreference: dietaryPreference ?? this.dietaryPreference,
      hasCompletedOnboarding: hasCompletedOnboarding ?? this.hasCompletedOnboarding,
    );
  }
}

class UserProfileService {
  static const String _key = 'nutrilens_user_profile';

  static Future<UserProfile> loadProfile() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    if (raw != null && raw.isNotEmpty) {
      try {
        return UserProfile.fromJson(jsonDecode(raw));
      } catch (_) {}
    }
    return const UserProfile();
  }

  static Future<void> saveProfile(UserProfile profile) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, jsonEncode(profile.toJson()));
  }

  static Future<void> updateTargets({
    required int calories,
    double? protein,
    double? carbs,
    double? fat,
  }) async {
    final current = await loadProfile();
    // Auto-calculate macros if not explicitly provided (Protein: 25%, Carbs: 50%, Fat: 25%)
    final p = protein ?? ((calories * 0.25) / 4.0);
    final c = carbs ?? ((calories * 0.50) / 4.0);
    final f = fat ?? ((calories * 0.25) / 9.0);

    final updated = current.copyWith(
      targetCalories: calories,
      targetProteinG: double.parse(p.toStringAsFixed(1)),
      targetCarbsG: double.parse(c.toStringAsFixed(1)),
      targetFatG: double.parse(f.toStringAsFixed(1)),
    );
    await saveProfile(updated);
  }
}
