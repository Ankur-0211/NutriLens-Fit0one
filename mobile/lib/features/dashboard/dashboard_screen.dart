import 'package:flutter/material.dart';
import '../../core/constants.dart';
import '../../core/api_client.dart';

class DashboardScreen extends StatefulWidget {
  final NutriLensApiClient apiClient;
  final VoidCallback onScanPressed;

  const DashboardScreen({Key? key, required this.apiClient, required this.onScanPressed}) : super(key: key);

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  int caloriesRemaining = 2500;
  int caloriesIntake = 0;
  int targetCalories = 2500;
  double proteinG = 0.0;
  double carbsG = 0.0;
  double fatG = 0.0;
  bool isLoading = false;
  String currentMode = 'local';

  @override
  void initState() {
    super.initState();
    _loadTelemetry();
  }

  Future<void> _loadTelemetry() async {
    setState(() => isLoading = true);
    try {
      final now = DateTime.now().toIso8601String().split('T')[0];
      final data = await widget.apiClient.fetchDailyTelemetry(now);
      final totals = data['totals'] ?? {};
      final intake = ((totals['energy_kcal']?['value'] ?? 0) as num).round();
      setState(() {
        caloriesIntake = intake;
        caloriesRemaining = (targetCalories - intake).clamp(0, targetCalories).toInt();
        proteinG = ((totals['protein_g']?['value'] ?? 0.0) as num).toDouble();
        carbsG = ((totals['carbs_g']?['value'] ?? 0.0) as num).toDouble();
        fatG = ((totals['fat_g']?['value'] ?? 0.0) as num).toDouble();
        isLoading = false;
        currentMode = widget.apiClient.isOfflineMode || widget.apiClient.lastUsedOffline ? 'offline' : 'online';
      });
    } catch (_) {
      setState(() => isLoading = false);
    }
  }

  void _showServerConfigSheet() {
    final controller = TextEditingController(text: widget.apiClient.baseUrl);
    String testStatus = '';
    bool isTesting = false;
    bool isSuccess = false;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppConstants.surfaceContainer,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setModalState) {
            return Padding(
              padding: EdgeInsets.only(
                left: 20,
                right: 20,
                top: 20,
                bottom: MediaQuery.of(context).viewInsets.bottom + 24,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: [
                          Container(
                            width: 10,
                            height: 10,
                            decoration: const BoxDecoration(
                              color: AppConstants.primaryContainer,
                              shape: BoxShape.circle,
                            ),
                          ),
                          const SizedBox(width: 8),
                          const Text(
                            'SERVER & CLOUD CONFIG',
                            style: TextStyle(
                              fontFamily: 'monospace',
                              fontWeight: FontWeight.bold,
                              fontSize: 14,
                              color: AppConstants.textOnSurface,
                              letterSpacing: 1.2,
                            ),
                          ),
                        ],
                      ),
                      IconButton(
                        icon: const Icon(Icons.close, color: AppConstants.outline, size: 20),
                        onPressed: () => Navigator.pop(ctx),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Run NutriLens 24/7 without keeping your laptop on! Choose Offline Standalone mode or point to a free Cloud server.',
                    style: TextStyle(color: AppConstants.textVariant, fontSize: 12),
                  ),
                  const SizedBox(height: 16),

                  // Quick Presets
                  const Text(
                    'QUICK PRESETS',
                    style: TextStyle(color: AppConstants.outline, fontSize: 10, letterSpacing: 1.0, fontFamily: 'monospace'),
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      ChoiceChip(
                        label: const Text('⚡ Standalone Offline (No Laptop)'),
                        selected: controller.text == 'OFFLINE',
                        selectedColor: AppConstants.primaryContainer.withOpacity(0.25),
                        backgroundColor: AppConstants.surfaceContainerHigh,
                        labelStyle: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: controller.text == 'OFFLINE' ? AppConstants.primaryContainer : AppConstants.textOnSurface,
                        ),
                        onSelected: (_) {
                          setModalState(() {
                            controller.text = 'OFFLINE';
                            testStatus = 'Autonomous on-device AI active. No network or laptop needed!';
                            isSuccess = true;
                          });
                        },
                      ),
                      ChoiceChip(
                        label: const Text('☁️ Cloud 24/7 (Render)'),
                        selected: controller.text.contains('onrender.com'),
                        selectedColor: AppConstants.secondary.withOpacity(0.25),
                        backgroundColor: AppConstants.surfaceContainerHigh,
                        labelStyle: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: controller.text.contains('onrender.com') ? AppConstants.secondary : AppConstants.textOnSurface,
                        ),
                        onSelected: (_) {
                          setModalState(() {
                            controller.text = 'https://nutrilens.onrender.com/v1';
                            testStatus = '';
                          });
                        },
                      ),
                      ChoiceChip(
                        label: const Text('💻 Local Wi-Fi (Laptop)'),
                        selected: controller.text.contains('10.0.89.21'),
                        selectedColor: Colors.blue.withOpacity(0.25),
                        backgroundColor: AppConstants.surfaceContainerHigh,
                        labelStyle: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: controller.text.contains('10.0.89.21') ? Colors.lightBlueAccent : AppConstants.textOnSurface,
                        ),
                        onSelected: (_) {
                          setModalState(() {
                            controller.text = 'http://10.0.89.21:8000/v1';
                            testStatus = '';
                          });
                        },
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),

                  // URL Input
                  TextField(
                    controller: controller,
                    style: const TextStyle(color: AppConstants.textOnSurface, fontFamily: 'monospace', fontSize: 13),
                    decoration: InputDecoration(
                      labelText: 'API BASE URL',
                      labelStyle: const TextStyle(color: AppConstants.outline, fontSize: 11),
                      filled: true,
                      fillColor: AppConstants.surface,
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
                      prefixIcon: const Icon(Icons.link, color: AppConstants.primaryContainer, size: 18),
                    ),
                  ),
                  const SizedBox(height: 12),

                  // Test Connection & Status
                  if (testStatus.isNotEmpty)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      margin: const EdgeInsets.only(bottom: 12),
                      decoration: BoxDecoration(
                        color: isSuccess ? AppConstants.primaryContainer.withOpacity(0.12) : AppConstants.error.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: isSuccess ? AppConstants.primaryContainer.withOpacity(0.4) : AppConstants.error.withOpacity(0.4)),
                      ),
                      child: Row(
                        children: [
                          Icon(isSuccess ? Icons.check_circle : Icons.error_outline, color: isSuccess ? AppConstants.primaryContainer : AppConstants.error, size: 16),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              testStatus,
                              style: TextStyle(
                                color: isSuccess ? AppConstants.primaryContainer : AppConstants.error,
                                fontSize: 11,
                                fontFamily: 'monospace',
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),

                  Row(
                    children: [
                      OutlinedButton.icon(
                        icon: isTesting
                            ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: AppConstants.outline))
                            : const Icon(Icons.network_check, size: 16),
                        label: const Text('TEST PING', style: TextStyle(fontFamily: 'monospace', fontSize: 11)),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: AppConstants.textOnSurface,
                          side: const BorderSide(color: AppConstants.outline),
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                        ),
                        onPressed: isTesting
                            ? null
                            : () async {
                                setModalState(() {
                                  isTesting = true;
                                  testStatus = 'Pinging...';
                                });
                                final res = await widget.apiClient.testConnection(controller.text);
                                setModalState(() {
                                  isTesting = false;
                                  isSuccess = res['success'] ?? false;
                                  testStatus = '${res['message']} (${res['latency_ms']}ms)';
                                });
                              },
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: ElevatedButton.icon(
                          icon: const Icon(Icons.save, size: 18, color: AppConstants.onPrimary),
                          label: const Text('APPLY & SAVE', style: TextStyle(color: AppConstants.onPrimary, fontWeight: FontWeight.bold, fontSize: 12, letterSpacing: 1.0)),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppConstants.primaryContainer,
                            padding: const EdgeInsets.symmetric(vertical: 12),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                          ),
                          onPressed: () async {
                            await widget.apiClient.updateBaseUrl(controller.text);
                            if (context.mounted) {
                              Navigator.pop(ctx);
                              _loadTelemetry();
                            }
                          },
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildConnectionPill() {
    final isOffline = widget.apiClient.isOfflineMode || widget.apiClient.lastUsedOffline;
    final isCloud = widget.apiClient.baseUrl.contains('https://') || widget.apiClient.baseUrl.contains('onrender.com');

    Color badgeColor;
    String badgeText;
    IconData badgeIcon;

    if (isOffline) {
      badgeColor = const Color(0xFFC084FC); // Purple / Offline Autonomous
      badgeText = 'ON-DEVICE AI';
      badgeIcon = Icons.offline_bolt;
    } else if (isCloud) {
      badgeColor = AppConstants.primaryContainer; // Green / Cloud 24/7
      badgeText = 'CLOUD 24/7';
      badgeIcon = Icons.cloud_done;
    } else {
      badgeColor = AppConstants.secondary; // Orange / Local Wi-Fi
      badgeText = 'LOCAL WI-FI';
      badgeIcon = Icons.wifi;
    }

    return GestureDetector(
      onTap: _showServerConfigSheet,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: badgeColor.withOpacity(0.15),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: badgeColor.withOpacity(0.5)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(badgeIcon, color: badgeColor, size: 12),
            const SizedBox(width: 4),
            Text(
              badgeText,
              style: TextStyle(color: badgeColor, fontSize: 10, fontWeight: FontWeight.bold, fontFamily: 'monospace'),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppConstants.surface,
      appBar: AppBar(
        backgroundColor: AppConstants.surface,
        elevation: 0,
        title: Row(
          children: [
            Container(
              width: 8,
              height: 8,
              decoration: const BoxDecoration(
                color: AppConstants.primaryContainer,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 8),
            const Text(
              'BIO-TELEMETRY',
              style: TextStyle(
                fontFamily: 'monospace',
                fontSize: 14,
                fontWeight: FontWeight.bold,
                color: AppConstants.textOnSurface,
                letterSpacing: 1.2,
              ),
            ),
          ],
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12.0),
            child: Center(child: _buildConnectionPill()),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadTelemetry,
        color: AppConstants.primaryContainer,
        backgroundColor: AppConstants.surfaceContainer,
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Offline Standalone Banner if applicable
              if (widget.apiClient.isOfflineMode || widget.apiClient.lastUsedOffline)
                Container(
                  margin: const EdgeInsets.only(bottom: 12.0),
                  padding: const EdgeInsets.symmetric(horizontal: 14.0, vertical: 10.0),
                  decoration: BoxDecoration(
                    color: const Color(0xFFC084FC).withOpacity(0.12),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFC084FC).withOpacity(0.35)),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.bolt, color: Color(0xFFC084FC), size: 18),
                      const SizedBox(width: 8),
                      const Expanded(
                        child: Text(
                          'Standalone Phone Mode: Operating 100% locally with on-device Indian food engine. Laptop can remain OFF.',
                          style: TextStyle(color: AppConstants.textOnSurface, fontSize: 11),
                        ),
                      ),
                      TextButton(
                        onPressed: _showServerConfigSheet,
                        child: const Text('CONFIG', style: TextStyle(color: Color(0xFFC084FC), fontSize: 10, fontWeight: FontWeight.bold)),
                      ),
                    ],
                  ),
                ),

              // Caloric Flux Dual-Arc HUD Card
              Container(
                padding: const EdgeInsets.all(20.0),
                decoration: BoxDecoration(
                  color: AppConstants.surfaceContainerLow,
                  borderRadius: BorderRadius.circular(16.0),
                  border: Border.all(color: AppConstants.surfaceContainerHigh),
                ),
                child: Column(
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'DAILY ENERGY FLUX',
                          style: TextStyle(
                            fontFamily: 'monospace',
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                            color: AppConstants.outline,
                            letterSpacing: 1.0,
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: AppConstants.surfaceContainerHigh,
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: const Text(
                            'TARGET: 2500 KCAL',
                            style: TextStyle(
                              fontFamily: 'monospace',
                              fontSize: 10,
                              color: AppConstants.textVariant,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 20),
                    Center(
                      child: Column(
                        children: [
                          Text(
                            '$caloriesRemaining',
                            style: const TextStyle(
                              fontSize: 48,
                              fontWeight: FontWeight.bold,
                              fontFamily: 'monospace',
                              color: AppConstants.primaryContainer,
                              letterSpacing: -1.0,
                            ),
                          ),
                          const Text(
                            'KCAL REMAINING',
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                              color: AppConstants.outline,
                              letterSpacing: 1.5,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 20),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        _buildStatColumn('INTAKE', '$caloriesIntake', AppConstants.textOnSurface),
                        Container(width: 1, height: 30, color: AppConstants.surfaceContainerHigh),
                        _buildStatColumn('BURN', '450', AppConstants.secondary),
                        Container(width: 1, height: 30, color: AppConstants.surfaceContainerHigh),
                        _buildStatColumn('REMAINING', '$caloriesRemaining', AppConstants.primaryContainer),
                      ],
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 16),

              // Macro Nutrient Telemetry Card
              Container(
                padding: const EdgeInsets.all(20.0),
                decoration: BoxDecoration(
                  color: AppConstants.surfaceContainerLow,
                  borderRadius: BorderRadius.circular(16.0),
                  border: Border.all(color: AppConstants.surfaceContainerHigh),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'MACRO-NUTRIENT MATRIX',
                      style: TextStyle(
                        fontFamily: 'monospace',
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                        color: AppConstants.outline,
                        letterSpacing: 1.0,
                      ),
                    ),
                    const SizedBox(height: 16),
                    _buildMacroMeter('PROTEIN', proteinG, 140.0, AppConstants.primaryContainer),
                    const SizedBox(height: 12),
                    _buildMacroMeter('CARBOHYDRATES', carbsG, 280.0, AppConstants.secondary),
                    const SizedBox(height: 12),
                    _buildMacroMeter('FAT', fatG, 65.0, Colors.amberAccent),
                  ],
                ),
              ),

              const SizedBox(height: 20),

              // Quick Action Button
              ElevatedButton.icon(
                onPressed: widget.onScanPressed,
                icon: const Icon(Icons.center_focus_strong, color: AppConstants.onPrimary),
                label: const Text(
                  'SCAN FOOD THALI',
                  style: TextStyle(
                    fontFamily: 'monospace',
                    fontWeight: FontWeight.bold,
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

  Widget _buildStatColumn(String label, String value, Color color) {
    return Column(
      children: [
        Text(label, style: const TextStyle(color: AppConstants.outline, fontSize: 10, letterSpacing: 1.0)),
        const SizedBox(height: 4),
        Text(value, style: TextStyle(color: color, fontSize: 16, fontWeight: FontWeight.bold, fontFamily: 'monospace')),
      ],
    );
  }

  Widget _buildMacroMeter(String name, double current, double target, Color barColor) {
    final pct = (current / target).clamp(0.0, 1.0);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(name, style: const TextStyle(color: AppConstants.textOnSurface, fontSize: 11, fontFamily: 'monospace')),
            Text('${current.toStringAsFixed(1)} / ${target.toStringAsFixed(0)}g', style: TextStyle(color: barColor, fontSize: 11, fontFamily: 'monospace', fontWeight: FontWeight.bold)),
          ],
        ),
        const SizedBox(height: 6),
        LinearProgressIndicator(
          value: pct,
          backgroundColor: AppConstants.surfaceContainerHighest,
          valueColor: AlwaysStoppedAnimation<Color>(barColor),
          minHeight: 6,
        ),
      ],
    );
  }
}
