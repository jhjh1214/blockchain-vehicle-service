// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint

// Run the following command to regenerate:
//   dart run build_runner build --delete-conflicting-outputs

// After Flutter SDK is installed:
//   cd owner_mobile_app && flutter pub run build_runner build

import 'dart:async' as _i3;
import 'dart:io' as _i4;

import 'package:dio/dio.dart' as _i2;
import 'package:mockito/mockito.dart' as _i1;

class MockDio extends _i1.Mock implements _i2.Dio {
  MockDio() {
    _i1.throwOnMissingStub(this);
  }

  @override
  _i2.HttpClientAdapter get httpClientAdapter =>
      (super.noSuchMethod(
        Invocation.getter(#httpClientAdapter),
        returnValue: _FakeHttpClientAdapter_0(
          this,
          Invocation.getter(#httpClientAdapter),
        ),
      ) as _i2.HttpClientAdapter);

  @override
  set httpClientAdapter(_i2.HttpClientAdapter? _httpClientAdapter) =>
      super.noSuchMethod(
        Invocation.setter(#httpClientAdapter, _httpClientAdapter),
        returnValueForMissingStub: null,
      );

  @override
  _i2.BaseOptions get options => (super.noSuchMethod(
        Invocation.getter(#options),
        returnValue: _FakeBaseOptions_1(this, Invocation.getter(#options)),
      ) as _i2.BaseOptions);

  @override
  set options(_i2.BaseOptions? _options) => super.noSuchMethod(
        Invocation.setter(#options, _options),
        returnValueForMissingStub: null,
      );

  @override
  _i2.Interceptors get interceptors => (super.noSuchMethod(
        Invocation.getter(#interceptors),
        returnValue: _FakeInterceptors_2(this, Invocation.getter(#interceptors)),
      ) as _i2.Interceptors);

  @override
  _i3.Future<_i2.Response<T>> get<T>(
    String? path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
    _i2.Options? options,
    _i2.CancelToken? cancelToken,
    _i2.ProgressCallback? onReceiveProgress,
  }) =>
      (super.noSuchMethod(
        Invocation.method(#get, [path], {
          #data: data,
          #queryParameters: queryParameters,
          #options: options,
          #cancelToken: cancelToken,
          #onReceiveProgress: onReceiveProgress,
        }),
        returnValue: _i3.Future<_i2.Response<T>>.value(_FakeResponse_3<T>(
          this,
          Invocation.method(#get, [path], {
            #data: data,
            #queryParameters: queryParameters,
            #options: options,
            #cancelToken: cancelToken,
            #onReceiveProgress: onReceiveProgress,
          }),
        )),
      ) as _i3.Future<_i2.Response<T>>);

  @override
  _i3.Future<_i2.Response<T>> post<T>(
    String? path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
    _i2.Options? options,
    _i2.CancelToken? cancelToken,
    _i2.ProgressCallback? onSendProgress,
    _i2.ProgressCallback? onReceiveProgress,
  }) =>
      (super.noSuchMethod(
        Invocation.method(#post, [path], {
          #data: data,
          #queryParameters: queryParameters,
          #options: options,
          #cancelToken: cancelToken,
          #onSendProgress: onSendProgress,
          #onReceiveProgress: onReceiveProgress,
        }),
        returnValue: _i3.Future<_i2.Response<T>>.value(_FakeResponse_3<T>(
          this,
          Invocation.method(#post, [path], {
            #data: data,
            #queryParameters: queryParameters,
            #options: options,
            #cancelToken: cancelToken,
            #onSendProgress: onSendProgress,
            #onReceiveProgress: onReceiveProgress,
          }),
        )),
      ) as _i3.Future<_i2.Response<T>>);

  @override
  _i3.Future<_i2.Response<T>> put<T>(
    String? path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
    _i2.Options? options,
    _i2.CancelToken? cancelToken,
    _i2.ProgressCallback? onSendProgress,
    _i2.ProgressCallback? onReceiveProgress,
  }) =>
      (super.noSuchMethod(
        Invocation.method(#put, [path], {
          #data: data,
          #queryParameters: queryParameters,
          #options: options,
          #cancelToken: cancelToken,
          #onSendProgress: onSendProgress,
          #onReceiveProgress: onReceiveProgress,
        }),
        returnValue: _i3.Future<_i2.Response<T>>.value(_FakeResponse_3<T>(
          this,
          Invocation.method(#put, [path], {
            #data: data,
            #queryParameters: queryParameters,
            #options: options,
            #cancelToken: cancelToken,
            #onSendProgress: onSendProgress,
            #onReceiveProgress: onReceiveProgress,
          }),
        )),
      ) as _i3.Future<_i2.Response<T>>);

  @override
  _i3.Future<_i2.Response<T>> fetch<T>(_i2.RequestOptions? requestOptions) =>
      (super.noSuchMethod(
        Invocation.method(#fetch, [requestOptions]),
        returnValue: _i3.Future<_i2.Response<T>>.value(_FakeResponse_3<T>(
          this,
          Invocation.method(#fetch, [requestOptions]),
        )),
      ) as _i3.Future<_i2.Response<T>>);
}

class _FakeHttpClientAdapter_0 extends _i1.SmartFake
    implements _i2.HttpClientAdapter {
  _FakeHttpClientAdapter_0(Object parent, Invocation parentInvocation)
      : super(parent, parentInvocation);
}

class _FakeBaseOptions_1 extends _i1.SmartFake implements _i2.BaseOptions {
  _FakeBaseOptions_1(Object parent, Invocation parentInvocation)
      : super(parent, parentInvocation);
}

class _FakeInterceptors_2 extends _i1.SmartFake implements _i2.Interceptors {
  _FakeInterceptors_2(Object parent, Invocation parentInvocation)
      : super(parent, parentInvocation);
}

class _FakeResponse_3<T> extends _i1.SmartFake implements _i2.Response<T> {
  _FakeResponse_3(Object parent, Invocation parentInvocation)
      : super(parent, parentInvocation);
}
