import 'package:flutter/material.dart';
import '../../core/constants.dart';
import '../../core/user_profile.dart';

class OnboardingScreen extends StatefulWidget {
  final VoidCallback onSetupCompleted;

  const OnboardingScreen({Key? key, required this.onSetupCompleted}) : super(key: key);

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final TextEditingController _nameController = TextEditingController(text: 'Warrior');
  int _targetCalories = 2100;
  double _proteinG = 120.0;
  double _carbsG = 240.0;
  double _fatG = 60.0;
  String _dietPreference = 'Vegetarian';
  bool _isSaving = false;

  void _onCalorieChanged(int kcal) {
    setState(() {
      _targetCalories = kcal;
      // Auto-rebalance macros (Protein 25%, Carbs 50%, Fat 25%)
      _proteinG = double.parse(((kcal * 0.25) / 4.0).toStringAsFixed(1));
      _carbsG = double.parse(((kcal * 0.50) / 4.0).toStringAsFixed(1));
      _fatG = double.parse(((kcal * 0.25) / 9.0).toStringAsFixed(1));
    });
  }

  Future<void> _completeSetup() async {
    setState(() => _isSaving = true);
    final profile = UserProfile(
      name: _nameController.text.trim().isNotEmpty ? _nameController.text.trim() : 'Warrior',
      targetCalories: _targetCalories,
      targetProteinG: _proteinG,
      targetCarbsG: _carbsG,
      targetFatG: _fatG,
      dietaryPreference: _dietPreference,
      hasCompletedOnboarding: true,
    );
    await UserProfileService.saveProfile(profile);
    if (!mounted) return;
    widget.onSetupCompleted();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppConstants.surface,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header Brand
              Row(
                children: [
                  Container(
                    width: 38,
                    height: 38,
                    decoration: BoxDecoration(
                      color: AppConstants.primaryContainer,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.bolt, color: AppConstants.onPrimary, size: 24),
                  ),
                  const SizedBox(width: 12),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: const [
                      Text(
                        'NUTRILENS AI',
                        style: TextStyle(
                          fontFamily: 'monospace',
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: AppConstants.primaryContainer,
                          letterSpacing: 1.5,
                        ),
                      ),
                      Text(
                        'INITIAL CALIBRATION & GOALS',
                        style: TextStyle(
                          color: AppConstants.outline,
                          fontSize: 10,
                          letterSpacing: 1.2,
                          fontFamily: 'monospace',
                        ),
                      ),
                    ],
                  ),
                ],
              ),

              const SizedBox(height: 24),

              // Welcome Intro Card
              Container(
                padding: const EdgeInsets.all(16.0),
                decoration: BoxDecoration(
                  color: AppConstants.surfaceContainerLow,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: AppConstants.primaryContainer.withOpacity(0.3)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: const [
                    Text(
                      'Welcome to Autonomous Nutrition Tracking',
                      style: TextStyle(
                        color: AppConstants.textOnSurface,
                        fontWeight: FontWeight.bold,
                        fontSize: 15,
                      ),
                    ),
                    SizedBox(height: 6),
                    Text(
                      'Configure your daily nutritional targets below. NutriLens will use these to calibrate your Indian meals, macro distribution, and bio-telemetry.',
                      style: TextStyle(color: AppConstants.textVariant, fontSize: 12, height: 1.4),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 20),

              // Section 1: Name / Profile
              const Text(
                'YOUR NAME',
                style: TextStyle(fontFamily: 'monospace', fontSize: 11, color: AppConstants.outline, letterSpacing: 1.0, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _nameController,
                style: const TextStyle(color: AppConstants.textOnSurface, fontFamily: 'monospace', fontSize: 14),
                decoration: InputDecoration(
                  hintText: 'Enter your name',
                  hintStyle: const TextStyle(color: AppConstants.outline),
                  filled: true,
                  fillColor: AppConstants.surfaceContainerLow,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
                  prefixIcon: const Icon(Icons.person, color: AppConstants.primaryContainer, size: 20),
                ),
              ),

              const SizedBox(height: 24),

              // Section 2: Daily Calorie Goal
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'DAILY CALORIE TARGET',
                    style: TextStyle(fontFamily: 'monospace', fontSize: 11, color: AppConstants.outline, letterSpacing: 1.0, fontWeight: FontWeight.bold),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                    decoration: BoxDecoration(
                      color: AppConstants.primaryContainer.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: AppConstants.primaryContainer.withOpacity(0.4)),
                    ),
                    child: Text(
                      '$_targetCalories KCAL',
                      style: const TextStyle(
                        fontFamily: 'monospace',
                        fontWeight: FontWeight.bold,
                        fontSize: 14,
                        color: AppConstants.primaryContainer,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),

              // Preset Quick Buttons
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _presetChip('1600 kcal (Fat Loss)', 1600),
                  _presetChip('2000 kcal (Balanced)', 2000),
                  _presetChip('2400 kcal (Active)', 2400),
                  _presetChip('2800 kcal (Muscle Gain)', 2800),
                ],
              ),

              const SizedBox(height: 12),

              Slider(
                value: _targetCalories.toDouble().clamp(1200.0, 4000.0),
                min: 1200.0,
                max: 4000.0,
                divisions: 56,
                activeColor: AppConstants.primaryContainer,
                inactiveColor: AppConstants.surfaceContainerHighest,
                onChanged: (val) => _onCalorieChanged(val.round()),
              ),

              const SizedBox(height: 20),

              // Section 3: Macro Nutrient Breakdown
              Container(
                padding: const EdgeInsets.all(16.0),
                decoration: BoxDecoration(
                  color: AppConstants.surfaceContainerLow,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: AppConstants.surfaceContainerHigh),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'CUSTOM MACRO BREAKDOWN',
                      style: TextStyle(fontFamily: 'monospace', fontSize: 11, color: AppConstants.outline, letterSpacing: 1.0, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 14),
                    _macroSlider('PROTEIN', _proteinG, 40, 250, AppConstants.primaryContainer, (val) => setState(() => _proteinG = val)),
                    const SizedBox(height: 12),
                    _macroSlider('CARBOHYDRATES', _carbsG, 60, 450, AppConstants.secondary, (val) => setState(() => _carbsG = val)),
                    const SizedBox(height: 12),
                    _macroSlider('HEALTHY FATS', _fatG, 20, 150, Colors.amberAccent, (val) => setState(() => _fatG = val)),
                  ],
                ),
              ),

              const SizedBox(height: 20),

              // Section 4: Dietary Preference
              const Text(
                'DIETARY PREFERENCE',
                style: TextStyle(fontFamily: 'monospace', fontSize: 11, color: AppConstants.outline, letterSpacing: 1.0, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  'Vegetarian',
                  'Non-Vegetarian',
                  'Eggetarian',
                  'Vegan',
                  'Jain',
                ].map((pref) {
                  final isSelected = _dietPreference == pref;
                  return ChoiceChip(
                    label: Text(pref),
                    selected: isSelected,
                    selectedColor: AppConstants.primaryContainer.withOpacity(0.2),
                    backgroundColor: AppConstants.surfaceContainerLow,
                    labelStyle: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      color: isSelected ? AppConstants.primaryContainer : AppConstants.textOnSurface,
                    ),
                    onSelected: (_) => setState(() => _dietPreference = pref),
                  );
                }).toList(),
              ),

              const SizedBox(height: 32),

              // Complete Button
              ElevatedButton.icon(
                onPressed: _isSaving ? null : _completeSetup,
                icon: const Icon(Icons.rocket_launch, color: AppConstants.onPrimary, size: 20),
                label: _isSaving
                    ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: AppConstants.onPrimary))
                    : const Text(
                        'SAVE GOALS & ENTER APP',
                        style: TextStyle(
                          fontFamily: 'monospace',
                          fontWeight: FontWeight.bold,
                          fontSize: 13,
                          color: AppConstants.onPrimary,
                          letterSpacing: 1.2,
                        ),
                      ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppConstants.primaryContainer,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  elevation: 6,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _presetChip(String label, int kcal) {
    final isSelected = _targetCalories == kcal;
    return ChoiceChip(
      label: Text(label),
      selected: isSelected,
      selectedColor: AppConstants.primaryContainer.withOpacity(0.25),
      backgroundColor: AppConstants.surfaceContainerHigh,
      labelStyle: TextStyle(
        fontSize: 11,
        fontFamily: 'monospace',
        fontWeight: FontWeight.bold,
        color: isSelected ? AppConstants.primaryContainer : AppConstants.textVariant,
      ),
      onSelected: (_) => _onCalorieChanged(kcal),
    );
  }

  Widget _macroSlider(String name, double value, double min, double max, Color color, ValueChanged<double> onChanged) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(name, style: const TextStyle(color: AppConstants.textOnSurface, fontSize: 11, fontFamily: 'monospace')),
            Text('${value.toStringAsFixed(0)}g', style: TextStyle(color: color, fontSize: 12, fontFamily: 'monospace', fontWeight: FontWeight.bold)),
          ],
        ),
        Slider(
          value: value.clamp(min, max),
          min: min,
          max: max,
          divisions: (max - min).toInt(),
          activeColor: color,
          inactiveColor: AppConstants.surfaceContainerHighest,
          onChanged: (val) => onChanged(double.parse(val.toStringAsFixed(0))),
        ),
      ],
    );
  }
}
