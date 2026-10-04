import 'package:flutter/material.dart';
import 'core/constants.dart';
import 'core/api_client.dart';
import 'core/user_profile.dart';
import 'features/onboarding/onboarding_screen.dart';
import 'features/dashboard/dashboard_screen.dart';
import 'features/scanner/scanner_screen.dart';
import 'features/diary/diary_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const NutriLensApp());
}

class NutriLensApp extends StatelessWidget {
  const NutriLensApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'NutriLens AI',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: AppConstants.surface,
        primaryColor: AppConstants.primaryContainer,
        colorScheme: const ColorScheme.dark(
          primary: AppConstants.primaryContainer,
          surface: AppConstants.surface,
          error: AppConstants.error,
        ),
      ),
      home: const RootAppShell(),
    );
  }
}

class RootAppShell extends StatefulWidget {
  const RootAppShell({Key? key}) : super(key: key);

  @override
  State<RootAppShell> createState() => _RootAppShellState();
}

class _RootAppShellState extends State<RootAppShell> {
  bool _isLoading = true;
  bool _hasCompletedOnboarding = false;

  @override
  void initState() {
    super.initState();
    _checkOnboardingStatus();
  }

  Future<void> _checkOnboardingStatus() async {
    try {
      final profile = await UserProfileService.loadProfile();
      if (mounted) {
        setState(() {
          _hasCompletedOnboarding = profile.hasCompletedOnboarding;
          _isLoading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        backgroundColor: AppConstants.surface,
        body: Center(
          child: CircularProgressIndicator(color: AppConstants.primaryContainer),
        ),
      );
    }

    if (!_hasCompletedOnboarding) {
      return OnboardingScreen(
        onSetupCompleted: () {
          setState(() => _hasCompletedOnboarding = true);
        },
      );
    }

    return const MainNavigationShell();
  }
}

class MainNavigationShell extends StatefulWidget {
  const MainNavigationShell({Key? key}) : super(key: key);

  @override
  State<MainNavigationShell> createState() => _MainNavigationShellState();
}

class _MainNavigationShellState extends State<MainNavigationShell> {
  int _currentIndex = 0;
  final NutriLensApiClient _apiClient = NutriLensApiClient();

  void _onScanPressed() {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => ScannerScreen(apiClient: _apiClient)),
    );
  }

  @override
  Widget build(BuildContext context) {
    final screens = [
      DashboardScreen(apiClient: _apiClient, onScanPressed: _onScanPressed),
      DiaryScreen(apiClient: _apiClient),
    ];

    return Scaffold(
      body: screens[_currentIndex],
      bottomNavigationBar: NavigationBar(
        backgroundColor: AppConstants.surfaceContainerLow,
        indicatorColor: AppConstants.primaryContainer.withOpacity(0.2),
        selectedIndex: _currentIndex,
        onDestinationSelected: (i) => setState(() => _currentIndex = i),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.speed, color: AppConstants.outline),
            selectedIcon: Icon(Icons.speed, color: AppConstants.primaryContainer),
            label: 'DASH',
          ),
          NavigationDestination(
            icon: Icon(Icons.dataset, color: AppConstants.outline),
            selectedIcon: Icon(Icons.dataset, color: AppConstants.primaryContainer),
            label: 'DIARY',
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _onScanPressed,
        backgroundColor: AppConstants.primaryContainer,
        child: const Icon(Icons.center_focus_strong, color: AppConstants.onPrimary),
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerDocked,
    );
  }
}
