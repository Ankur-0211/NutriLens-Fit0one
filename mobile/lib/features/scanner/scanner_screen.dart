import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import '../../core/constants.dart';
import '../../core/api_client.dart';
import '../calibration/calibration_screen.dart';
import '../calibration/food_picker_dialog.dart';

class ScannerScreen extends StatefulWidget {
  final NutriLensApiClient apiClient;

  const ScannerScreen({Key? key, required this.apiClient}) : super(key: key);

  @override
  State<ScannerScreen> createState() => _ScannerScreenState();
}

class _ScannerScreenState extends State<ScannerScreen> with WidgetsBindingObserver {
  CameraController? _cameraController;
  List<CameraDescription> _cameras = [];
  int _selectedCameraIndex = 0;
  FlashMode _flashMode = FlashMode.off;
  bool _isCameraInitialized = false;
  bool _isScanning = false;
  String? _cameraErrorMessage;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _initCamera();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _cameraController?.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final CameraController? controller = _cameraController;
    if (controller == null || !controller.value.isInitialized) {
      return;
    }
    if (state == AppLifecycleState.inactive) {
      controller.dispose();
    } else if (state == AppLifecycleState.resumed) {
      _initCamera();
    }
  }

  Future<void> _initCamera() async {
    try {
      _cameras = await availableCameras();
      if (_cameras.isEmpty) {
        setState(() {
          _cameraErrorMessage = 'No camera hardware found on this device.';
        });
        return;
      }

      await _setupCameraController(_cameras[_selectedCameraIndex]);
    } catch (e) {
      setState(() {
        _cameraErrorMessage = 'Camera permission or initialization error: $e';
      });
    }
  }

  Future<void> _setupCameraController(CameraDescription camera) async {
    final controller = CameraController(
      camera,
      ResolutionPreset.medium,
      enableAudio: false,
      imageFormatGroup: ImageFormatGroup.jpeg,
    );

    _cameraController = controller;

    try {
      await controller.initialize();
      await controller.setFlashMode(_flashMode);
      if (mounted) {
        setState(() {
          _isCameraInitialized = true;
          _cameraErrorMessage = null;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isCameraInitialized = false;
          _cameraErrorMessage = 'Could not start camera preview: $e';
        });
      }
    }
  }

  Future<void> _toggleFlash() async {
    if (_cameraController == null || !_cameraController!.value.isInitialized) return;
    FlashMode newMode;
    switch (_flashMode) {
      case FlashMode.off:
        newMode = FlashMode.torch;
        break;
      case FlashMode.torch:
        newMode = FlashMode.auto;
        break;
      case FlashMode.auto:
      default:
        newMode = FlashMode.off;
        break;
    }

    try {
      await _cameraController!.setFlashMode(newMode);
      setState(() => _flashMode = newMode);
    } catch (_) {}
  }

  Future<void> _switchCamera() async {
    if (_cameras.length < 2) return;
    _selectedCameraIndex = (_selectedCameraIndex + 1) % _cameras.length;
    await _cameraController?.dispose();
    setState(() => _isCameraInitialized = false);
    await _setupCameraController(_cameras[_selectedCameraIndex]);
  }

  Future<void> _capturePhotoAndAnalyze() async {
    if (_isScanning) return;
    setState(() => _isScanning = true);

    try {
      List<int> imageBytes;

      if (_cameraController != null && _cameraController!.value.isInitialized) {
        final XFile file = await _cameraController!.takePicture();
        imageBytes = await file.readAsBytes();
      } else {
        // Fallback dummy image if camera is not available
        imageBytes = [];
      }

      final result = await widget.apiClient.analyzeImageBytes(imageBytes);

      if (!mounted) return;
      setState(() => _isScanning = false);

      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => CalibrationScreen(
            apiClient: widget.apiClient,
            analysisResult: result,
          ),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() => _isScanning = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Scan Error: $e'), backgroundColor: AppConstants.error),
      );
    }
  }

  void _openManualFoodPicker() {
    showDialog(
      context: context,
      builder: (ctx) => FoodPickerDialog(
        onFoodSelected: (food, grams) {
          final ratio = grams / 100.0;
          final kcal = ((food['energy_100g'] as double? ?? 0) * ratio);
          final p = ((food['protein_100g'] as double? ?? 0) * ratio);
          final c = ((food['carbs_100g'] as double? ?? 0) * ratio);
          final f = ((food['fat_100g'] as double? ?? 0) * ratio);

          final manualResult = {
            'analysis_id': 'manual_${DateTime.now().millisecondsSinceEpoch}',
            'items': [
              {
                'item_id': 'item_1',
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
              }
            ],
            'totals': {
              'energy_kcal': {'value': double.parse(kcal.toStringAsFixed(1))},
              'protein_g': {'value': double.parse(p.toStringAsFixed(1))},
              'carbs_g': {'value': double.parse(c.toStringAsFixed(1))},
              'fat_g': {'value': double.parse(f.toStringAsFixed(1))},
            },
          };

          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (_) => CalibrationScreen(
                apiClient: widget.apiClient,
                analysisResult: manualResult,
              ),
            ),
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: AppConstants.textOnSurface),
          onPressed: () => Navigator.pop(context),
        ),
        title: const Text(
          'CYBER-KINETIC SCANNER',
          style: TextStyle(
            fontFamily: 'monospace',
            fontSize: 13,
            fontWeight: FontWeight.bold,
            letterSpacing: 1.2,
          ),
        ),
        actions: [
          if (_isCameraInitialized) ...[
            IconButton(
              icon: Icon(
                _flashMode == FlashMode.torch
                    ? Icons.flash_on
                    : (_flashMode == FlashMode.auto ? Icons.flash_auto : Icons.flash_off),
                color: _flashMode == FlashMode.off ? AppConstants.outline : AppConstants.primaryContainer,
              ),
              onPressed: _toggleFlash,
            ),
            if (_cameras.length > 1)
              IconButton(
                icon: const Icon(Icons.flip_camera_android, color: AppConstants.textOnSurface),
                onPressed: _switchCamera,
              ),
          ],
        ],
      ),
      body: Stack(
        children: [
          // Camera Live Preview or Fallback View
          if (_isCameraInitialized && _cameraController != null)
            SizedBox.expand(
              child: FittedBox(
                fit: BoxFit.cover,
                child: SizedBox(
                  width: _cameraController!.value.previewSize?.height ?? 1,
                  height: _cameraController!.value.previewSize?.width ?? 1,
                  child: CameraPreview(_cameraController!),
                ),
              ),
            )
          else
            Center(
              child: Padding(
                padding: const EdgeInsets.all(24.0),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.camera_alt_outlined, color: AppConstants.outline, size: 54),
                    const SizedBox(height: 16),
                    Text(
                      _cameraErrorMessage ?? 'Initializing camera hardware...',
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: AppConstants.textVariant, fontSize: 13),
                    ),
                    const SizedBox(height: 20),
                    ElevatedButton.icon(
                      onPressed: _openManualFoodPicker,
                      icon: const Icon(Icons.restaurant_menu, color: AppConstants.onPrimary),
                      label: const Text('SELECT FOOD MANUALLY', style: TextStyle(fontWeight: FontWeight.bold, color: AppConstants.onPrimary)),
                      style: ElevatedButton.styleFrom(backgroundColor: AppConstants.primaryContainer),
                    ),
                  ],
                ),
              ),
            ),

          // Viewfinder Target Box Overlay
          Center(
            child: Container(
              width: 280,
              height: 280,
              decoration: BoxDecoration(
                border: Border.all(color: AppConstants.primaryContainer.withOpacity(0.8), width: 2),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Stack(
                children: [
                  Positioned(top: 0, left: 0, child: _corner(true, true)),
                  Positioned(top: 0, right: 0, child: _corner(true, false)),
                  Positioned(bottom: 0, left: 0, child: _corner(false, true)),
                  Positioned(bottom: 0, right: 0, child: _corner(false, false)),
                  if (_isScanning)
                    Container(
                      color: Colors.black54,
                      child: Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: const [
                            CircularProgressIndicator(color: AppConstants.primaryContainer),
                            SizedBox(height: 16),
                            Text(
                              'ANALYZING INDIAN THALI...',
                              style: TextStyle(
                                color: AppConstants.primaryContainer,
                                fontFamily: 'monospace',
                                fontWeight: FontWeight.bold,
                                fontSize: 12,
                                letterSpacing: 1.2,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ),

          // Bottom Control Strip
          Positioned(
            bottom: 36,
            left: 0,
            right: 0,
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    TextButton.icon(
                      onPressed: _openManualFoodPicker,
                      icon: const Icon(Icons.search, color: AppConstants.primaryContainer, size: 16),
                      label: const Text(
                        'OR SEARCH FOOD MANUALLY',
                        style: TextStyle(
                          color: AppConstants.primaryContainer,
                          fontFamily: 'monospace',
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                GestureDetector(
                  onTap: _isScanning ? null : _capturePhotoAndAnalyze,
                  child: Container(
                    width: 76,
                    height: 76,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(color: AppConstants.primaryContainer, width: 3),
                      color: AppConstants.primaryContainer.withOpacity(0.2),
                    ),
                    child: Center(
                      child: Container(
                        width: 58,
                        height: 58,
                        decoration: const BoxDecoration(
                          shape: BoxShape.circle,
                          color: AppConstants.primaryContainer,
                        ),
                        child: const Icon(Icons.camera_alt, color: AppConstants.onPrimary, size: 30),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _corner(bool isTop, bool isLeft) {
    return Container(
      width: 24,
      height: 24,
      decoration: BoxDecoration(
        color: AppConstants.primaryContainer,
        borderRadius: BorderRadius.only(
          topLeft: Radius.circular(isTop && isLeft ? 18 : 0),
          topRight: Radius.circular(isTop && !isLeft ? 18 : 0),
          bottomLeft: Radius.circular(!isTop && isLeft ? 18 : 0),
          bottomRight: Radius.circular(!isTop && !isLeft ? 18 : 0),
        ),
      ),
    );
  }
}
