import 'package:dio/dio.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';

@GenerateMocks([Dio])
export 'mock_dio.mocks.dart';

/// Build a successful [Response] with [data] for use in stubbing.
Response<T> mockResponse<T>(T data, {int statusCode = 200}) => Response(
      data: data,
      statusCode: statusCode,
      requestOptions: RequestOptions(path: ''),
    );

/// Build a [DioException] with a response body [error] map.
DioException mockDioError(Map<String, dynamic> error,
    {int statusCode = 400}) =>
    DioException(
      requestOptions: RequestOptions(path: ''),
      response: Response(
        data: error,
        statusCode: statusCode,
        requestOptions: RequestOptions(path: ''),
      ),
      type: DioExceptionType.badResponse,
    );
