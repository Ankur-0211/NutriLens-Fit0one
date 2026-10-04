import 'package:flutter/material.dart';
import '../../core/constants.dart';
import '../../core/api_client.dart';
import 'food_picker_dialog.dart';

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

  void _recalculateTotalsLocally() {
    double totalKcal = 0;
    double totalProtein = 0;
    double totalCarbs = 0;
    double totalFat = 0;

    for (var item in items) {
      final snap = item['nutrition'] ?? {};
      totalKcal += ((snap['energy_kcal']?['value'] ?? 0) as num).toDouble();
      totalProtein += ((snap['protein_g']?['value'] ?? 0) as num).toDouble();
      totalCarbs += ((snap['carbs_g']?['value'] ?? 0) as num).toDouble();
      totalFat += ((snap['fat_g']?['value'] ?? 0) as num).toDouble();
    }

    setState(() {
      totals = {
        'energy_kcal': {'value': double.parse(totalKcal.toStringAsFixed(1))},
        'protein_g': {'value': double.parse(totalProtein.toStringAsFixed(1))},
        'carbs_g': {'value': double.parse(totalCarbs.toStringAsFixed(1))},
        'fat_g': {'value': double.parse(totalFat.toStringAsFixed(1))},
      };
    });
  }

  Future<void> _updateItemQuantity(int index, double newGrams) async {
    final item = items[index];
    final oldGrams = (item['portion_g'] ?? 100.0).toDouble();
    final factor = oldGrams > 0 ? (newGrams / oldGrams) : 1.0;

    final snap = item['nutrition'] ?? {};
    final currentKcal = ((snap['energy_kcal']?['value'] ?? 0) as num).toDouble();
    final currentP = ((snap['protein_g']?['value'] ?? 0) as num).toDouble();
    final currentC = ((snap['carbs_g']?['value'] ?? 0) as num).toDouble();
    final currentF = ((snap['fat_g']?['value'] ?? 0) as num).toDouble();

    setState(() {
      items[index]['portion_g'] = newGrams;
      items[index]['nutrition'] = {
        'energy_kcal': {'value': double.parse((currentKcal * factor).toStringAsFixed(1))},
        'protein_g': {'value': double.parse((currentP * factor).toStringAsFixed(1))},
        'carbs_g': {'value': double.parse((currentC * factor).toStringAsFixed(1))},
        'fat_g': {'value': double.parse((currentF * factor).toStringAsFixed(1))},
      };
    });

    _recalculateTotalsLocally();

    // Also attempt backend calculation if online
    try {
      final payload = items.map((it) {
        return {
          'food_id': it['food_id'],
          'variant_id': it['variant_id'],
          'quantity': it['portion_g'],
          'unit': 'g',
        };
      }).toList();

      final res = await widget.apiClient.calculateNutrition(payload);
      if (mounted && res['totals'] != null) {
        setState(() {
          totals = res['totals'];
        });
      }
    } catch (_) {}
  }

  void _removeItem(int index) {
    setState(() {
      items.removeAt(index);
    });
    _recalculateTotalsLocally();
  }

  void _openFoodPicker() {
    showDialog(
      context: context,
      builder: (ctx) => FoodPickerDialog(
        onFoodSelected: (food, grams) {
          final ratio = grams / 100.0;
          final kcal = ((food['energy_100g'] as double? ?? 0) * ratio);
          final p = ((food['protein_100g'] as double? ?? 0) * ratio);
          final c = ((food['carbs_100g'] as double? ?? 0) * ratio);
          final f = ((food['fat_100g'] as double? ?? 0) * ratio);

          setState(() {
            items.add({
              'item_id': 'manual_${DateTime.now().millisecondsSinceEpoch}',
              'food_id': food['food_id'],
              'food_name': food['name'],
              'resolved_food': {'name': food['name']},
              'portion_g': grams,
              'is_manual': true,
              'nutrition': {
                'energy_kcal': {'value': double.parse(kcal.toStringAsFixed(1))},
                'protein_g': {'value': double.parse(p.toStringAsFixed(1))},
                'carbs_g': {'value': double.parse(c.toStringAsFixed(1))},
                'fat_g': {'value': double.parse(f.toStringAsFixed(1))},
              },
            });
          });
          _recalculateTotalsLocally();
        },
      ),
    );
  }

  Future<void> _confirmAndSave() async {
    if (items.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please add at least one food item before logging.'),
          backgroundColor: AppConstants.secondary,
        ),
      );
      return;
    }

    setState(() => isSaving = true);
    try {
      final now = DateTime.now();
      final mealPayload = {
        'meal_type': selectedMealType,
        'eaten_at': now.toIso8601String(),
        'local_date': now.toIso8601String().split('T')[0],
        'analysis_id': widget.analysisResult['analysis_id'] ?? 'scan_${now.millisecondsSinceEpoch}',
        'items': items.map((item) {
          return {
            'food_id': item['food_id'] ?? 'food_custom',
            'variant_id': item['variant_id'] ?? '${item['food_id']}_var',
            'grams': (item['portion_g'] ?? 100.0).toDouble(),
            'unit': 'g',
            'unit_qty': (item['portion_g'] ?? 100.0).toDouble(),
            'source': item['is_manual'] == true ? 'user_selected' : 'ai_verified',
            'nutrition_snapshot': item['nutrition'] ?? {},
          };
        }).toList(),
      };

      await widget.apiClient.saveMeal(mealPayload);

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Meal logged successfully!'),
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
    final kcal = ((totals['energy_kcal']?['value'] ?? 0) as num).round();
    final p = ((totals['protein_g']?['value'] ?? 0) as num).toStringAsFixed(1);
    final c = ((totals['carbs_g']?['value'] ?? 0) as num).toStringAsFixed(1);
    final f = ((totals['fat_g']?['value'] ?? 0) as num).toStringAsFixed(1);

    return Scaffold(
      backgroundColor: AppConstants.surface,
      appBar: AppBar(
        backgroundColor: AppConstants.surface,
        elevation: 0,
        title: const Text(
          'CALIBRATION // FOOD VERIFY',
          style: TextStyle(fontFamily: 'monospace', fontSize: 13, fontWeight: FontWeight.bold, letterSpacing: 1.2),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.add_circle_outline, color: AppConstants.primaryContainer),
            tooltip: 'Add Food Item',
            onPressed: _openFoodPicker,
          ),
        ],
      ),
      body: Column(
        children: [
          // Total Calorie & Macro Banner
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
            color: AppConstants.surfaceContainerHigh,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('TOTAL MEAL ENERGY', style: TextStyle(color: AppConstants.outline, fontSize: 10, letterSpacing: 1.0, fontFamily: 'monospace')),
                    Text('$kcal KCAL', style: const TextStyle(color: AppConstants.primaryContainer, fontSize: 22, fontWeight: FontWeight.bold, fontFamily: 'monospace')),
                  ],
                ),
                Row(
                  children: [
                    _macroBadge('P', '$p g', AppConstants.primaryContainer),
                    const SizedBox(width: 6),
                    _macroBadge('C', '$c g', AppConstants.secondary),
                    const SizedBox(width: 6),
                    _macroBadge('F', '$f g', Colors.amberAccent),
                  ],
                ),
              ],
            ),
          ),

          // Meal Type Selector
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
            color: AppConstants.surfaceContainerLow,
            child: Row(
              children: [
                const Text('MEAL:', style: TextStyle(fontFamily: 'monospace', fontSize: 11, color: AppConstants.outline, fontWeight: FontWeight.bold)),
                const SizedBox(width: 10),
                Expanded(
                  child: SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: ['breakfast', 'lunch', 'snack', 'dinner'].map((type) {
                        final isSel = selectedMealType == type;
                        return Padding(
                          padding: const EdgeInsets.only(right: 6.0),
                          child: ChoiceChip(
                            label: Text(type.toUpperCase()),
                            selected: isSel,
                            selectedColor: AppConstants.primaryContainer.withOpacity(0.2),
                            backgroundColor: AppConstants.surfaceContainer,
                            labelStyle: TextStyle(
                              fontSize: 10,
                              fontFamily: 'monospace',
                              fontWeight: FontWeight.bold,
                              color: isSel ? AppConstants.primaryContainer : AppConstants.textVariant,
                            ),
                            onSelected: (_) => setState(() => selectedMealType = type),
                          ),
                        );
                      }).toList(),
                    ),
                  ),
                ),
              ],
            ),
          ),

          // Detected or Selected Food Items List
          Expanded(
            child: items.isEmpty
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24.0),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Container(
                            width: 68,
                            height: 68,
                            decoration: BoxDecoration(
                              color: AppConstants.surfaceContainerHigh,
                              shape: BoxShape.circle,
                              border: Border.all(color: AppConstants.outline.withOpacity(0.3)),
                            ),
                            child: const Icon(Icons.no_meals, color: AppConstants.secondary, size: 34),
                          ),
                          const SizedBox(height: 16),
                          const Text(
                            'NO FOOD DETECTED IN IMAGE',
                            style: TextStyle(
                              color: AppConstants.textOnSurface,
                              fontFamily: 'monospace',
                              fontWeight: FontWeight.bold,
                              fontSize: 13,
                              letterSpacing: 1.0,
                            ),
                          ),
                          const SizedBox(height: 8),
                          const Text(
                            'The camera did not find any recognizable food on the plate. You can pick your Indian meal items manually below.',
                            textAlign: TextAlign.center,
                            style: TextStyle(color: AppConstants.textVariant, fontSize: 12, height: 1.4),
                          ),
                          const SizedBox(height: 20),
                          ElevatedButton.icon(
                            onPressed: _openFoodPicker,
                            icon: const Icon(Icons.add, color: AppConstants.onPrimary),
                            label: const Text(
                              'SEARCH & PICK FOOD',
                              style: TextStyle(fontFamily: 'monospace', fontWeight: FontWeight.bold, color: AppConstants.onPrimary, letterSpacing: 1.1),
                            ),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: AppConstants.primaryContainer,
                              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                            ),
                          ),
                        ],
                      ),
                    ),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.all(16.0),
                    itemCount: items.length + 1,
                    itemBuilder: (ctx, i) {
                      if (i == items.length) {
                        return Padding(
                          padding: const EdgeInsets.only(top: 4.0, bottom: 16.0),
                          child: OutlinedButton.icon(
                            onPressed: _openFoodPicker,
                            icon: const Icon(Icons.add, size: 18),
                            label: const Text(
                              '+ ADD ANOTHER FOOD ITEM',
                              style: TextStyle(fontFamily: 'monospace', fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 1.0),
                            ),
                            style: OutlinedButton.styleFrom(
                              foregroundColor: AppConstants.primaryContainer,
                              side: BorderSide(color: AppConstants.primaryContainer.withOpacity(0.5)),
                              padding: const EdgeInsets.symmetric(vertical: 12),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                            ),
                          ),
                        );
                      }

                      final item = items[i];
                      final foodName = item['food_name'] ?? item['resolved_food']?['name'] ?? item['food_id'] ?? 'Food Item';
                      final grams = ((item['portion_g'] ?? 100.0) as num).toDouble();
                      final itemKcal = ((item['nutrition']?['energy_kcal']?['value'] ?? 0) as num).round();

                      return Card(
                        color: AppConstants.surfaceContainerLow,
                        margin: const EdgeInsets.only(bottom: 12.0),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                          side: BorderSide(color: AppConstants.surfaceContainerHighest.withOpacity(0.5)),
                        ),
                        child: Padding(
                          padding: const EdgeInsets.all(14.0),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Expanded(
                                    child: Text(
                                      foodName,
                                      style: const TextStyle(color: AppConstants.textOnSurface, fontSize: 14, fontWeight: FontWeight.bold),
                                    ),
                                  ),
                                  Row(
                                    children: [
                                      Text(
                                        '$itemKcal kcal',
                                        style: const TextStyle(color: AppConstants.primaryContainer, fontFamily: 'monospace', fontWeight: FontWeight.bold, fontSize: 13),
                                      ),
                                      const SizedBox(width: 4),
                                      IconButton(
                                        icon: const Icon(Icons.delete_outline, color: AppConstants.error, size: 18),
                                        onPressed: () => _removeItem(i),
                                        padding: EdgeInsets.zero,
                                        constraints: const BoxConstraints(),
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                              const SizedBox(height: 8),
                              Row(
                                children: [
                                  Text(
                                    '${grams.round()}g',
                                    style: const TextStyle(color: AppConstants.textVariant, fontFamily: 'monospace', fontWeight: FontWeight.bold, fontSize: 12),
                                  ),
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
                onPressed: (isSaving || items.isEmpty) ? null : _confirmAndSave,
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppConstants.primaryContainer,
                  minimumSize: const Size.fromHeight(50),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                child: isSaving
                    ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: AppConstants.onPrimary, strokeWidth: 2))
                    : const Text(
                        'CONFIRM & LOG TO DIARY',
                        style: TextStyle(color: AppConstants.onPrimary, fontWeight: FontWeight.bold, letterSpacing: 1.2),
                      ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _macroBadge(String label, String value, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
      decoration: BoxDecoration(color: AppConstants.surfaceContainer, borderRadius: BorderRadius.circular(6)),
      child: Column(
        children: [
          Text(label, style: TextStyle(color: color, fontSize: 9, fontWeight: FontWeight.bold)),
          Text(value, style: const TextStyle(color: AppConstants.textOnSurface, fontSize: 10, fontFamily: 'monospace')),
        ],
      ),
    );
  }
}
