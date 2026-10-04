import 'dart:convert';
import 'package:http/http.dart' as http;
import 'constants.dart';

class UpdateInfo {
  final bool hasUpdate;
  final String currentVersion;
  final String latestVersion;
  final String releaseName;
  final String releaseNotes;
  final String downloadUrl;
  final String publishedAt;

  const UpdateInfo({
    required this.hasUpdate,
    required this.currentVersion,
    required this.latestVersion,
    this.releaseName = '',
    this.releaseNotes = '',
    this.downloadUrl = '',
    this.publishedAt = '',
  });
}

class LiveUpdateService {
  static Future<UpdateInfo> checkLatestRelease() async {
    try {
      final uri = Uri.parse(AppConstants.releasesApiUrl);
      final response = await http.get(
        uri,
        headers: {
          'Accept': 'application/vnd.github.v3+json',
          'User-Agent': 'NutriLens-Mobile/${AppConstants.appVersion}',
        },
      ).timeout(const Duration(seconds: 5));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final tagName = (data['tag_name'] ?? '').toString();
        final releaseName = (data['name'] ?? tagName).toString();
        final body = (data['body'] ?? '').toString();
        final publishedAt = (data['published_at'] ?? '').toString();

        // Extract direct APK download URL from assets if present
        String apkUrl = AppConstants.fallbackApkUrl;
        final assets = (data['assets'] as List?) ?? [];
        for (var asset in assets) {
          final name = (asset['name'] ?? '').toString().toLowerCase();
          if (name.endsWith('.apk')) {
            apkUrl = asset['browser_download_url'] ?? apkUrl;
            break;
          }
        }

        final currentTag = AppConstants.appVersionTag.toLowerCase().replaceAll('v', '');
        final remoteTag = tagName.toLowerCase().replaceAll('v', '');

        final hasNewer = _isVersionGreater(remoteTag, currentTag);

        return UpdateInfo(
          hasUpdate: hasNewer,
          currentVersion: AppConstants.appVersionTag,
          latestVersion: tagName.isNotEmpty ? tagName : AppConstants.appVersionTag,
          releaseName: releaseName,
          releaseNotes: body,
          downloadUrl: apkUrl,
          publishedAt: publishedAt,
        );
      }
    } catch (_) {}

    return const UpdateInfo(
      hasUpdate: false,
      currentVersion: AppConstants.appVersionTag,
      latestVersion: AppConstants.appVersionTag,
      downloadUrl: AppConstants.fallbackApkUrl,
    );
  }

  static bool _isVersionGreater(String remote, String current) {
    if (remote == current || remote.isEmpty) return false;
    final rParts = remote.split('.').map((p) => int.tryParse(p) ?? 0).toList();
    final cParts = current.split('.').map((p) => int.tryParse(p) ?? 0).toList();

    for (int i = 0; i < rParts.length && i < cParts.length; i++) {
      if (rParts[i] > cParts[i]) return true;
      if (rParts[i] < cParts[i]) return false;
    }
    return rParts.length > cParts.length;
  }
}
