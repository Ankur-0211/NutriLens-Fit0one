import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'constants.dart';
import 'offline_engine.dart';

class NutriLensApiClient {
  static const String _prefKeyBaseUrl = "nutrilens_api_base_url";

  String _baseUrl;
  bool isOfflineMode = false;
  bool lastUsedOffline = false;

  NutriLensApiClient({String? customBaseUrl})
      : _baseUrl = customBaseUrl ?? (kIsWeb ? "/v1" : AppConstants.defaultApiBaseUrl) {
    _loadSavedBaseUrl();
  }

  String get baseUrl => _baseUrl;

  Future<void> _loadSavedBaseUrl() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final saved = prefs.getString(_prefKeyBaseUrl);
      if (saved != null && saved.isNotEmpty) {
        _baseUrl = saved;
        isOfflineMode = (_baseUrl == "OFFLINE");
      }
    } catch (_) {}
  }

  Future<void> updateBaseUrl(String newUrl) async {
    _baseUrl = newUrl.trim();
    isOfflineMode = (_baseUrl == "OFFLINE");
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_prefKeyBaseUrl, _baseUrl);
    } catch (_) {}
  }

  /// Pings server health or confirms offline mode
  Future<Map<String, dynamic>> testConnection([String? testUrl]) async {
    final target = (testUrl ?? _baseUrl).trim();
    if (target == "OFFLINE") {
      return {
        'success': true,
        'mode': 'offline',
        'message': 'Autonomous On-Device Engine Active',
        'latency_ms': 0,
      };
    }

    final stopwatch = Stopwatch()..start();
    try {
      final healthUri = Uri.parse(target.replaceAll(RegExp(r'/v1/?$'), '') + '/health');
      final res = await http.get(healthUri).timeout(const Duration(seconds: 4));
      stopwatch.stop();

      if (res.statusCode == 200) {
        return {
          'success': true,
          'mode': 'online',
          'message': 'Connected to NutriLens Server',
          'latency_ms': stopwatch.elapsedMilliseconds,
        };
      } else {
        return {
          'success': false,
          'mode': 'error',
          'message': 'Server returned HTTP ${res.statusCode}',
          'latency_ms': stopwatch.elapsedMilliseconds,
        };
      }
    } catch (e) {
      stopwatch.stop();
      return {
        'success': false,
        'mode': 'unreachable',
        'message': 'Server unreachable (falling back to on-device AI)',
        'latency_ms': stopwatch.elapsedMilliseconds,
      };
    }
  }

  /// Analyzes a meal photo using cloud AI or autonomous on-device fallback
  Future<Map<String, dynamic>> analyzeImageBytes(List<int> imageBytes, {String filename = "meal.jpg"}) async {
    if (isOfflineMode) {
      lastUsedOffline = true;
      return await OfflineNutritionEngine.generateScanResult(imageBytes: imageBytes);
    }

    try {
      final uri = Uri.parse('$_baseUrl/food/analyze');
      final request = http.MultipartRequest('POST', uri);
      request.files.add(http.MultipartFile.fromBytes('image', imageBytes, filename: filename));

      final streamedResponse = await request.send().timeout(const Duration(seconds: 6));
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        lastUsedOffline = false;
        return jsonDecode(response.body);
      } else {
        // Fallback gracefully on 5xx or server issues
        lastUsedOffline = true;
        return await OfflineNutritionEngine.generateScanResult(imageBytes: imageBytes);
      }
    } catch (_) {
      // Laptop off or offline - use on-device autonomous AI
      lastUsedOffline = true;
      return await OfflineNutritionEngine.generateScanResult(imageBytes: imageBytes);
    }
  }

  /// Calculates dynamic nutrition for calibrated items
  Future<Map<String, dynamic>> calculateNutrition(List<Map<String, dynamic>> items) async {
    if (isOfflineMode) {
      lastUsedOffline = true;
      return OfflineNutritionEngine.recalculate(items);
    }

    try {
      final uri = Uri.parse('$_baseUrl/nutrition/calculate');
      final response = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'items': items}),
      ).timeout(const Duration(seconds: 4));

      if (response.statusCode == 200) {
        lastUsedOffline = false;
        return jsonDecode(response.body);
      } else {
        lastUsedOffline = true;
        return OfflineNutritionEngine.recalculate(items);
      }
    } catch (_) {
      lastUsedOffline = true;
      return OfflineNutritionEngine.recalculate(items);
    }
  }

  /// Submits user verification corrections to record training feedback
  Future<Map<String, dynamic>> submitCorrection(Map<String, dynamic> payload) async {
    if (isOfflineMode) {
      return {'status': 'saved_offline', 'correction_batch_id': 'local_corr_${DateTime.now().millisecondsSinceEpoch}'};
    }

    try {
      final uri = Uri.parse('$_baseUrl/food/correct');
      final response = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(payload),
      ).timeout(const Duration(seconds: 4));

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
    } catch (_) {}

    return {'status': 'saved_offline', 'correction_batch_id': 'local_corr_${DateTime.now().millisecondsSinceEpoch}'};
  }

  /// Fetches daily nutrition totals and meal history
  Future<Map<String, dynamic>> fetchDailyTelemetry(String date) async {
    if (isOfflineMode) {
      lastUsedOffline = true;
      return await OfflineNutritionEngine.getLocalDailyTelemetry(date);
    }

    try {
      final uri = Uri.parse('$_baseUrl/nutrition/daily?date=$date');
      final response = await http.get(uri).timeout(const Duration(seconds: 4));

      if (response.statusCode == 200) {
        lastUsedOffline = false;
        final serverData = jsonDecode(response.body);
        final localData = await OfflineNutritionEngine.getLocalDailyTelemetry(date);
        
        // Merge local offline meals if any exist
        final List<dynamic> serverMeals = (serverData['meals'] as List?) ?? [];
        final List<dynamic> localMeals = (localData['meals'] as List?) ?? [];
        
        if (localMeals.isNotEmpty) {
          final mergedMeals = [...localMeals, ...serverMeals];
          return {
            'date': date,
            'totals': localMeals.isEmpty ? serverData['totals'] : localData['totals'],
            'meals': mergedMeals,
          };
        }
        return serverData;
      } else {
        lastUsedOffline = true;
        return await OfflineNutritionEngine.getLocalDailyTelemetry(date);
      }
    } catch (_) {
      lastUsedOffline = true;
      return await OfflineNutritionEngine.getLocalDailyTelemetry(date);
    }
  }

  /// Logs confirmed meal to user diary (always persists on device, syncs if online)
  Future<Map<String, dynamic>> saveMeal(Map<String, dynamic> mealData) async {
    // Always save locally so data is NEVER lost
    await OfflineNutritionEngine.saveLocalMeal(mealData);

    if (isOfflineMode) {
      lastUsedOffline = true;
      return {'status': 'saved_offline', 'meal_id': mealData['analysis_id'] ?? 'local_meal'};
    }

    try {
      final uri = Uri.parse('$_baseUrl/meals');
      final response = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(mealData),
      ).timeout(const Duration(seconds: 5));

      if (response.statusCode == 200) {
        lastUsedOffline = false;
        return jsonDecode(response.body);
      }
    } catch (_) {}

    lastUsedOffline = true;
    return {'status': 'saved_locally', 'meal_id': mealData['analysis_id'] ?? 'local_meal'};
  }

  /// Fetches on-device model manifest for mobile caching
  Future<Map<String, dynamic>> fetchModelManifest({String platform = 'android', String precision = 'INT8'}) async {
    try {
      final uri = Uri.parse('$_baseUrl/models/manifest?platform=$platform&precision=$precision');
      final response = await http.get(uri).timeout(const Duration(seconds: 4));
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
    } catch (_) {}

    return {
      'platform': platform,
      'runtime': platform == 'ios' ? 'coreml' : 'tflite',
      'precision': precision,
      'fits_mobile_budget': true,
      'models': [],
    };
  }
}
