/// Application constants.
class AppConstants {
  AppConstants._();

  static const String appName = 'FinanceApp';
  static const String apiBaseUrl = 'http://10.0.2.2:8000/api/v1'; // Android emulator
  static const String apiBaseUrlDesktop = 'http://localhost:8000/api/v1';

  // Token storage keys
  static const String accessTokenKey = 'access_token';
  static const String refreshTokenKey = 'refresh_token';
  static const String userKey = 'user_data';

  // Decision colors
  static const int safeColor = 0xFF22C55E;
  static const int cautionColor = 0xFFF59E0B;
  static const int riskyColor = 0xFFEF4444;
}
