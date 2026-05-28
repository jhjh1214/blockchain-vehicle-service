import 'dart:typed_data';
import 'package:dio/dio.dart';
import '../storage/token_storage.dart';

const String _baseUrl = 'http://10.0.2.2:5000/api';

class ApiClient {
  static ApiClient? _instance;
  late Dio _dio;

  ApiClient._() {
    _dio = Dio(BaseOptions(
      baseUrl: _baseUrl,
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 15),
      headers: {'Content-Type': 'application/json'},
    ));

    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await TokenStorage.getAccessToken();
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
      onError: (error, handler) async {
        if (error.response?.statusCode == 401) {
          final refreshed = await _refreshToken();
          if (refreshed) {
            final opts = error.requestOptions;
            final token = await TokenStorage.getAccessToken();
            opts.headers['Authorization'] = 'Bearer $token';
            final response = await _dio.fetch(opts);
            return handler.resolve(response);
          }
        }
        handler.next(error);
      },
    ));
  }

  static ApiClient get instance {
    _instance ??= ApiClient._();
    return _instance!;
  }

  Dio get dio => _dio;

  // ignore: invalid_use_of_visible_for_testing_member
  void injectDio(Dio dio) => _dio = dio;

  Future<Uint8List> downloadBytes(String path) async {
    final response = await _dio.get<List<int>>(
      path,
      options: Options(responseType: ResponseType.bytes),
    );
    return Uint8List.fromList(response.data!);
  }

  Future<bool> _refreshToken() async {
    final refresh = await TokenStorage.getRefreshToken();
    if (refresh == null) return false;
    try {
      final res = await Dio().post('$_baseUrl/auth/refresh',
          data: {'refresh_token': refresh});
      await TokenStorage.save(
        res.data['access_token'],
        res.data['refresh_token'],
      );
      return true;
    } catch (_) {
      await TokenStorage.clear();
      return false;
    }
  }
}
