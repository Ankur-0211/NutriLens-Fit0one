import 'package:flutter/material.dart';

class AppConstants {
  // App Version & Update Information
  static const String appVersion = "1.0.0";
  static const String appVersionTag = "v1.0.0";
  static const String githubRepo = "Ankur-0211/NutriLens-Fit0one";
  static const String releasesApiUrl = "https://api.github.com/repos/Ankur-0211/NutriLens-Fit0one/releases/latest";
  static const String fallbackApkUrl = "https://github.com/Ankur-0211/NutriLens-Fit0one/releases/download/v1.0.0/nutrilens.apk";

  // Network API Base URL
  static const String defaultApiBaseUrl = "http://10.0.89.21:8000/v1"; // Wi-Fi host IP
  static const String iosApiBaseUrl = "http://127.0.0.1:8000/v1";

  // Cyber-Kinetic Color Palette (matching stitch_calorie_counter_app_interface tokens)
  static const Color surface = Color(0xFF101319);
  static const Color surfaceContainerLow = Color(0xFF191C22);
  static const Color surfaceContainer = Color(0xFF1D2026);
  static const Color surfaceContainerHigh = Color(0xFF272A30);
  static const Color surfaceContainerHighest = Color(0xFF32353B);
  
  static const Color primaryContainer = Color(0xFF00FF88); // Electric Kinetic Green
  static const Color onPrimary = Color(0xFF003919);
  static const Color primaryFixedDim = Color(0xFF00E479);

  static const Color secondary = Color(0xFFFFB68E); // Thermogenic Orange
  static const Color onSecondary = Color(0xFF542200);

  static const Color error = Color(0xFFFFB4AB);
  static const Color textOnSurface = Color(0xFFE1E2EB);
  static const Color textVariant = Color(0xFFB9CBB9);
  static const Color outline = Color(0xFF849585);
}
