import 'package:flutter/material.dart';
import '../../core/constants.dart';
import '../../core/api_client.dart';

class DiaryScreen extends StatefulWidget {
  final NutriLensApiClient apiClient;

  const DiaryScreen({Key? key, required this.apiClient}) : super(key: key);

  @override
  State<DiaryScreen> createState() => _DiaryScreenState();
}

class _DiaryScreenState extends State<DiaryScreen> {
  DateTime selectedDate = DateTime.now();
  List<dynamic> meals = [];
  bool isLoading = false;

  @override
  void initState() {
    super.initState();
    _loadDiary();
  }

  Future<void> _loadDiary() async {
    setState(() => isLoading = true);
    try {
      final dateStr = selectedDate.toIso8601String().split('T')[0];
      final res = await widget.apiClient.fetchDailyTelemetry(dateStr);
      setState(() {
        meals = res['meals'] ?? [];
        isLoading = false;
      });
    } catch (_) {
      setState(() => isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final dateStr = selectedDate.toIso8601String().split('T')[0];

    return Scaffold(
      backgroundColor: AppConstants.surface,
      appBar: AppBar(
        backgroundColor: AppConstants.surface,
        elevation: 0,
        title: Text(
          'DIARY // $dateStr',
          style: const TextStyle(fontFamily: 'monospace', fontSize: 13, fontWeight: FontWeight.bold, letterSpacing: 1.2),
        ),
      ),
      body: isLoading
          ? const Center(child: CircularProgressIndicator(color: AppConstants.primaryContainer))
          : RefreshIndicator(
              onRefresh: _loadDiary,
              color: AppConstants.primaryContainer,
              child: meals.isEmpty
                  ? Center(
                      child: Text(
                        'No meals logged for $dateStr\nTap Scan to add meal',
                        textAlign: TextAlign.center,
                        style: const TextStyle(color: AppConstants.outline, fontFamily: 'monospace'),
                      ),
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.all(16.0),
                      itemCount: meals.length,
                      itemBuilder: (ctx, i) {
                        final m = meals[i];
                        final mealType = (m['meal_type'] ?? 'meal').toString().toUpperCase();
                        final kcal = (m['totals']?['energy_kcal']?['value'] ?? 0).round();
                        final itemsCount = (m['items'] as List?)?.length ?? 0;

                        return Card(
                          color: AppConstants.surfaceContainerLow,
                          margin: const EdgeInsets.only(bottom: 12.0),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                          child: ListTile(
                            leading: Container(
                              padding: const EdgeInsets.all(8),
                              decoration: BoxDecoration(color: AppConstants.surfaceContainerHigh, borderRadius: BorderRadius.circular(8)),
                              child: const Icon(Icons.restaurant, color: AppConstants.primaryContainer, size: 20),
                            ),
                            title: Text(mealType, style: const TextStyle(color: AppConstants.textOnSurface, fontWeight: FontWeight.bold)),
                            subtitle: Text('$itemsCount items logged', style: const TextStyle(color: AppConstants.outline, fontSize: 12)),
                            trailing: Text('$kcal kcal', style: const TextStyle(color: AppConstants.primaryContainer, fontFamily: 'monospace', fontWeight: FontWeight.bold)),
                          ),
                        );
                      },
                    ),
            ),
    );
  }
}
