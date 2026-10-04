import 'package:flutter/material.dart';
import '../../core/constants.dart';
import '../../core/api_client.dart';
import '../calibration/calibration_screen.dart';

class ScannerScreen extends StatefulWidget {
  final NutriLensApiClient apiClient;

  const ScannerScreen({Key? key, required this.apiClient}) : super(key: key);

  @override
  State<ScannerScreen> createState() => _ScannerScreenState();
}

class _ScannerScreenState extends State<ScannerScreen> {
  bool isScanning = false;

  Future<void> _simulateCaptureAndScan() async {
    setState(() => isScanning = true);
    try {
      // Valid minimal JPEG pixel bytes
      final dummyBytes = <int>[
        0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
        0x01, 0x01, 0x00, 0x48, 0x00, 0x48, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
        0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
        0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
        0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
        0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
        0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
        0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
        0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
        0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
        0x09, 0x0A, 0x0B, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F,
        0x00, 0xBF, 0x00, 0xFF, 0xD9
      ];

      final result = await widget.apiClient.analyzeImageBytes(dummyBytes);

      if (!mounted) return;
      setState(() => isScanning = false);

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
      setState(() => isScanning = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Scan Error: $e'),
          backgroundColor: AppConstants.error,
        ),
      );
    }
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
      ),
      body: Stack(
        children: [
          // Viewfinder Target Box
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
                  // Corner Highlights
                  Positioned(top: 0, left: 0, child: _corner(true, true)),
                  Positioned(top: 0, right: 0, child: _corner(true, false)),
                  Positioned(bottom: 0, left: 0, child: _corner(false, true)),
                  Positioned(bottom: 0, right: 0, child: _corner(false, false)),
                  if (isScanning)
                    const Center(
                      child: CircularProgressIndicator(color: AppConstants.primaryContainer),
                    ),
                ],
              ),
            ),
          ),

          // Bottom Control Strip
          Positioned(
            bottom: 40,
            left: 0,
            right: 0,
            child: Column(
              children: [
                const Text(
                  'ALIGN MEAL INSIDE RETICLE',
                  style: TextStyle(
                    color: AppConstants.textVariant,
                    fontFamily: 'monospace',
                    fontSize: 11,
                    letterSpacing: 1.2,
                  ),
                ),
                const SizedBox(height: 20),
                GestureDetector(
                  onTap: isScanning ? null : _simulateCaptureAndScan,
                  child: Container(
                    width: 72,
                    height: 72,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(color: AppConstants.primaryContainer, width: 3),
                      color: AppConstants.primaryContainer.withOpacity(0.2),
                    ),
                    child: Center(
                      child: Container(
                        width: 54,
                        height: 54,
                        decoration: const BoxDecoration(
                          shape: BoxShape.circle,
                          color: AppConstants.primaryContainer,
                        ),
                        child: const Icon(Icons.camera_alt, color: AppConstants.onPrimary, size: 28),
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
      width: 20,
      height: 20,
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
