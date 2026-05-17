import 'dart:io' show Platform;
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../core/constants.dart';

/// API client with 4 interceptors: auth, refresh, logging, error handling.
class ApiClient {
  static final ApiClient _instance = ApiClient._internal();
  factory ApiClient() => _instance;

  late final Dio dio;
  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  ApiClient._internal() {
    final baseUrl = (!kIsWeb && (Platform.isWindows || Platform.isMacOS || Platform.isLinux))
        ? AppConstants.apiBaseUrlDesktop
        : AppConstants.apiBaseUrl;

    dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 15),
      headers: {'Content-Type': 'application/json'},
    ));

    // 1. Auth interceptor — attach access token
    dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await _storage.read(key: AppConstants.accessTokenKey);
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
    ));

    // 2. Token refresh interceptor
    dio.interceptors.add(InterceptorsWrapper(
      onError: (error, handler) async {
        if (error.response?.statusCode == 401) {
          try {
            final refreshToken = await _storage.read(key: AppConstants.refreshTokenKey);
            if (refreshToken != null) {
              final refreshDio = Dio(BaseOptions(baseUrl: baseUrl));
              final response = await refreshDio.post('/auth/refresh', data: {
                'refresh_token': refreshToken,
              });

              if (response.statusCode == 200) {
                final tokens = response.data['data'];
                await _storage.write(
                  key: AppConstants.accessTokenKey,
                  value: tokens['access_token'],
                );
                await _storage.write(
                  key: AppConstants.refreshTokenKey,
                  value: tokens['refresh_token'],
                );

                // Retry original request with new token
                error.requestOptions.headers['Authorization'] =
                    'Bearer ${tokens['access_token']}';
                final retryResponse = await dio.fetch(error.requestOptions);
                return handler.resolve(retryResponse);
              }
            }
          } catch (_) {
            // Refresh failed — clear tokens
            await clearTokens();
          }
        }
        handler.next(error);
      },
    ));

    // 3. Logging interceptor (debug only)
    if (kDebugMode) {
      dio.interceptors.add(LogInterceptor(
        requestBody: true,
        responseBody: true,
        logPrint: (obj) => debugPrint(obj.toString()),
      ));
    }
  }

  Future<void> saveTokens(String accessToken, String refreshToken) async {
    await _storage.write(key: AppConstants.accessTokenKey, value: accessToken);
    await _storage.write(key: AppConstants.refreshTokenKey, value: refreshToken);
  }

  Future<void> clearTokens() async {
    await _storage.delete(key: AppConstants.accessTokenKey);
    await _storage.delete(key: AppConstants.refreshTokenKey);
    await _storage.delete(key: AppConstants.userKey);
  }

  Future<bool> hasToken() async {
    final token = await _storage.read(key: AppConstants.accessTokenKey);
    return token != null;
  }
}
