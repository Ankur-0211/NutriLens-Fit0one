import 'package:flutter/material.dart';
import '../../core/constants.dart';
import '../../core/api_client.dart';

class CalibrationScreen extends StatefulWidget {
  final NutriLensApiClient apiClient;
  final Map<String, dynamic> analysisResult;

  const CalibrationScreen({Key? key, required this.apiClient, required this.analysisResult}) : super(key: key);

  @override
  State<CalibrationScreen> createState() => _CalibrationScreenState();
}

class _CalibrationScreenState extends State<CalibrationScreen> {
  late List<dynamic> items;
  late Map<String, dynamic> totals;
  String selectedMealType = 'lunch';
  bool isSaving = false;

  @override
  void initState() {
    super.initState();
    items = List.from(widget.analysisResult['items'] ?? []);
    totals = Map.from(widget.analysisResult['totals'] ?? {});
  }

  Future<void> _updateItemQuantity(int index, double newGrams) async {
    setState(() {
      items[index]['portion_g'] = newGrams;
    });

    // Recompute via backend API
    try {
      final payload = items.map((item) {
        return {
          'food_id': item['food_id'],
          'variant_id': item['variant_id'],
          'quantity': item['portion_g'],
          'unit': 'g',
        };
      }).toList();

      final res = await widget.apiClient.calculateNutrition(payload);
      setState(() {
        totals = res['totals'] ?? totals;
      });
    } catch (_) {}
  }

  Future<void> _confirmAndSave() async {
    setState(() => isSaving = true);
    try {
      final now = DateTime.now();
      final mealPayload = {
        'meal_type': selectedMealType,
        'eaten_at': now.toIso8601String(),
        'local_date': now.toIso8601String().split('T')[0],
        'analysis_id': widget.analysisResult['analysis_id'],
        'items': items.map((item) {
          return {
            'food_id': item['food_id'],
            'variant_id': item['variant_id'],
            'grams': item['portion_g'] ?? 100.0,
            'unit': 'g',
            'unit_qty': item['portion_g'] ?? 100.0,
            'source': 'ai_verified',
            'nutrition_snapshot': item['nutrition'] ?? {},
          };
        }).toList(),
      };

      await widget.apiClient.saveMeal(mealPayload);

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Meal successfully saved to diary!'),
          backgroundColor: AppConstants.primaryContainer,
        ),
      );
      Navigator.popUntil(context, (route) => route.isFirst);
    } catch (e) {
      if (!mounted) return;
      setState(() => isSaving = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Save error: $e'), backgroundColor: AppConstants.error),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final kcal = (totals['energy_kcal']?['value'] ?? 0).round();
    final p = (totals['protein_g']?['value'] ?? 0).toStringAsFixed(1);
    final c = (totals['carbs_g']?['value'] ?? 0).toStringAsFixed(1);
    final f = (totals['fat_g']?['value'] ?? 0).toStringAsFixed(1);

    return Scaffold(
      backgroundColor: AppConstants.surface,
      appBar: AppBar(
        backgroundColor: AppConstants.surface,
        elevation: 0,
        title: const Text(
          'CALIBRATION // VERIFY AI',
          style: TextStyle(fontFamily: 'monospace', fontSize: 13, fontWeight: FontWeight.bold, letterSpacing: 1.2),
        ),
      ),
      body: Column(
        children: [
          // Total Calorie & Macro Banner
          Container(
            padding: const EdgeInsets.all(16.0),
            color: AppConstants.surfaceContainerHigh,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('ESTIMATED ENERGY', style: TextStyle(color: AppConstants.outline, fontSize: 10, letterSpacing: 1.0)),
                    Text('$kcal KCAL', style: const TextStyle(color: AppConstants.primaryContainer, fontSize: 24, fontWeight: FontWeight.bold)),
                  ],
                ),
                Row(
                  children: [
                    _macroBadge('P', '$p g', AppConstants.primaryContainer),
                    const SizedBox(width: 8),
                    _macroBadge('C', '$c g', AppConstants.secondary),
                    const SizedBox(width: 8),
                    _macroBadge('F', '$f g', AppConstants.primaryFixedDim),
                  ],
                ),
              ],
            ),
          ),

          // Detected Food Items List
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.all(16.0),
              itemCount: items.length,
              itemBuilder: (ctx, i) {
                final item = items[i];
                final foodName = item['resolved_food']?['name'] ?? item['food_id'] ?? 'Food Item';
                final grams = (item['portion_g'] ?? 100.0).toDouble();
                final itemKcal = (item['nutrition']?['energy_kcal']?['value'] ?? 0).round();

                return Card(
                  color: AppConstants.surfaceContainerLow,
                  margin: const EdgeInsets.only(bottom: 12.0),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(foodName, style: const TextStyle(color: AppConstants.textOnSurface, fontSize: 15, fontWeight: FontWeight.bold)),
                            Text('$itemKcal kcal', style: const TextStyle(color: AppConstants.primaryContainer, fontFamily: 'monospace', fontWeight: FontWeight.bold)),
                          ],
                        ),
                        const SizedBox(height: 12),
                        Row(
                          children: [
                            Text('${grams.toInt()}g', style: const TextStyle(color: AppConstants.textVariant, fontFamily: 'monospace', fontWeight: FontWeight.bold)),
                            Expanded(
                              child: Slider(
                                value: grams.clamp(20.0, 500.0),
                                min: 20.0,
                                max: 500.0,
                                divisions: 48,
                                activeColor: AppConstants.primaryContainer,
                                inactiveColor: AppConstants.surfaceContainerHighest,
                                onChanged: (val) => _updateItemQuantity(i, val),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),

          // Confirm & Save Bottom Bar
          Container(
            padding: const EdgeInsets.all(16.0),
            color: AppConstants.surfaceContainer,
            child: SafeArea(
              child: ElevatedButton(
                onPressed: isSaving ? null : _confirmAndSave,
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppConstants.primaryContainer,
                  minimumSize: const Size.fromHeight(50),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                child: isSaving
                    ? const CircularProgressIndicator(color: AppConstants.onPrimary)
                    : const Text('CONFIRM & LOG TO DIARY', style: TextStyle(color: AppConstants.onPrimary, fontWeight: FontWeight.bold, letterSpacing: 1.2)),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _macroBadge(String label, String value, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(color: AppConstants.surfaceContainer, borderRadius: BorderRadius.circular(6)),
      child: Column(
        children: [
          Text(label, style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.bold)),
          Text(value, style: const TextStyle(color: AppConstants.textOnSurface, fontSize: 11, fontFamily: 'monospace')),
        ],
      ),
    );
  }
}
