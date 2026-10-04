import 'package:flutter/material.dart';
import '../../core/constants.dart';
import '../../core/offline_engine.dart';

class FoodPickerDialog extends StatefulWidget {
  final Function(Map<String, dynamic> selectedFood, double grams) onFoodSelected;

  const FoodPickerDialog({Key? key, required this.onFoodSelected}) : super(key: key);

  @override
  State<FoodPickerDialog> createState() => _FoodPickerDialogState();
}

class _FoodPickerDialogState extends State<FoodPickerDialog> {
  final TextEditingController _searchController = TextEditingController();
  List<Map<String, dynamic>> _filteredFoods = [];
  Map<String, dynamic>? _selectedFood;
  double _portionG = 150.0;

  @override
  void initState() {
    super.initState();
    _filteredFoods = OfflineNutritionEngine.searchFoods('');
    if (_filteredFoods.isNotEmpty) {
      _selectedFood = _filteredFoods.first;
      _portionG = ((_selectedFood!['default_g'] ?? 150.0) as num).toDouble();
    }
  }

  void _onSearch(String query) {
    setState(() {
      _filteredFoods = OfflineNutritionEngine.searchFoods(query);
      if (_filteredFoods.isNotEmpty && !_filteredFoods.contains(_selectedFood)) {
        _selectedFood = _filteredFoods.first;
        _portionG = ((_selectedFood!['default_g'] ?? 150.0) as num).toDouble();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: AppConstants.surfaceContainer,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      insetPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 24),
      child: Container(
        height: 540,
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Title Bar
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    const Icon(Icons.restaurant, color: AppConstants.primaryContainer, size: 20),
                    const SizedBox(width: 8),
                    const Text(
                      'SELECT INDIAN FOOD',
                      style: TextStyle(
                        fontFamily: 'monospace',
                        fontWeight: FontWeight.bold,
                        fontSize: 13,
                        color: AppConstants.textOnSurface,
                        letterSpacing: 1.2,
                      ),
                    ),
                  ],
                ),
                IconButton(
                  icon: const Icon(Icons.close, color: AppConstants.outline, size: 20),
                  onPressed: () => Navigator.pop(context),
                ),
              ],
            ),

            const SizedBox(height: 10),

            // Search Bar
            TextField(
              controller: _searchController,
              onChanged: _onSearch,
              style: const TextStyle(color: AppConstants.textOnSurface, fontFamily: 'monospace', fontSize: 13),
              decoration: InputDecoration(
                hintText: 'Search Roti, Dal, Paneer, Dosa...',
                hintStyle: const TextStyle(color: AppConstants.outline, fontSize: 12),
                filled: true,
                fillColor: AppConstants.surfaceContainerLow,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
                prefixIcon: const Icon(Icons.search, color: AppConstants.primaryContainer, size: 20),
                contentPadding: const EdgeInsets.symmetric(vertical: 10),
              ),
            ),

            const SizedBox(height: 12),

            // Food Items List
            Expanded(
              child: _filteredFoods.isEmpty
                  ? Center(
                      child: Text(
                        'No matching foods found.\nTry "roti", "dal", "rice", or "paneer".',
                        textAlign: TextAlign.center,
                        style: const TextStyle(color: AppConstants.textVariant, fontSize: 12),
                      ),
                    )
                  : ListView.builder(
                      itemCount: _filteredFoods.length,
                      itemBuilder: (ctx, i) {
                        final food = _filteredFoods[i];
                        final isSelected = _selectedFood?['food_id'] == food['food_id'];
                        final kcal = food['energy_100g'] ?? 0;

                        return Container(
                          margin: const EdgeInsets.only(bottom: 6),
                          decoration: BoxDecoration(
                            color: isSelected ? AppConstants.primaryContainer.withOpacity(0.15) : AppConstants.surfaceContainerLow,
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(
                              color: isSelected ? AppConstants.primaryContainer.withOpacity(0.5) : Colors.transparent,
                            ),
                          ),
                          child: ListTile(
                            dense: true,
                            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 2),
                            title: Text(
                              food['name'] ?? '',
                              style: TextStyle(
                                color: isSelected ? AppConstants.primaryContainer : AppConstants.textOnSurface,
                                fontWeight: FontWeight.bold,
                                fontSize: 13,
                              ),
                            ),
                            subtitle: Text(
                              '${food['category']} • ${kcal.round()} kcal/100g',
                              style: const TextStyle(color: AppConstants.outline, fontSize: 11),
                            ),
                            trailing: isSelected
                                ? const Icon(Icons.check_circle, color: AppConstants.primaryContainer, size: 20)
                                : null,
                            onTap: () {
                              setState(() {
                                _selectedFood = food;
                                _portionG = (food['default_g'] as double?) ?? 150.0;
                              });
                            },
                          ),
                        );
                      },
                    ),
            ),

            const Divider(color: AppConstants.surfaceContainerHighest),

            // Selected Food Portion Adjuster
            if (_selectedFood != null) ...[
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'PORTION SIZE: ${_portionG.round()}g',
                    style: const TextStyle(fontFamily: 'monospace', fontWeight: FontWeight.bold, fontSize: 12, color: AppConstants.textOnSurface),
                  ),
                  Text(
                    '${(((_selectedFood!['energy_100g'] as double? ?? 0) * _portionG) / 100).round()} KCAL',
                    style: const TextStyle(fontFamily: 'monospace', fontWeight: FontWeight.bold, fontSize: 13, color: AppConstants.primaryContainer),
                  ),
                ],
              ),
              Slider(
                value: _portionG.clamp(20.0, 500.0),
                min: 20.0,
                max: 500.0,
                divisions: 48,
                activeColor: AppConstants.primaryContainer,
                inactiveColor: AppConstants.surfaceContainerHighest,
                onChanged: (val) => setState(() => _portionG = val),
              ),
              const SizedBox(height: 6),
            ],

            // Add Button
            ElevatedButton.icon(
              onPressed: _selectedFood == null
                  ? null
                  : () {
                      widget.onFoodSelected(_selectedFood!, _portionG);
                      Navigator.pop(context);
                    },
              icon: const Icon(Icons.add, color: AppConstants.onPrimary, size: 18),
              label: const Text(
                'ADD TO MEAL',
                style: TextStyle(fontFamily: 'monospace', fontWeight: FontWeight.bold, fontSize: 12, color: AppConstants.onPrimary, letterSpacing: 1.1),
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppConstants.primaryContainer,
                padding: const EdgeInsets.symmetric(vertical: 12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
