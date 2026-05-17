import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:equatable/equatable.dart';

import '../../../shared/services/api_client.dart';

// ── Events ──
abstract class AuthEvent extends Equatable {
  @override
  List<Object?> get props => [];
}

class AuthLoginRequested extends AuthEvent {
  final String email;
  final String password;
  AuthLoginRequested({required this.email, required this.password});
  @override
  List<Object?> get props => [email, password];
}

class AuthRegisterRequested extends AuthEvent {
  final String email;
  final String password;
  AuthRegisterRequested({required this.email, required this.password});
  @override
  List<Object?> get props => [email, password];
}

class AuthLogoutRequested extends AuthEvent {}

class AuthCheckRequested extends AuthEvent {}

// ── States ──
abstract class AuthState extends Equatable {
  @override
  List<Object?> get props => [];
}

class AuthInitial extends AuthState {}
class AuthLoading extends AuthState {}
class AuthAuthenticated extends AuthState {
  final Map<String, dynamic> user;
  AuthAuthenticated({required this.user});
  @override
  List<Object?> get props => [user];
}
class AuthUnauthenticated extends AuthState {}
class AuthError extends AuthState {
  final String message;
  AuthError({required this.message});
  @override
  List<Object?> get props => [message];
}

// ── BLoC ──
class AuthBloc extends Bloc<AuthEvent, AuthState> {
  final ApiClient _api = ApiClient();

  AuthBloc() : super(AuthInitial()) {
    on<AuthLoginRequested>(_onLogin);
    on<AuthRegisterRequested>(_onRegister);
    on<AuthLogoutRequested>(_onLogout);
    on<AuthCheckRequested>(_onCheck);
  }

  Future<void> _onLogin(AuthLoginRequested event, Emitter<AuthState> emit) async {
    emit(AuthLoading());
    try {
      final response = await _api.dio.post('/auth/login', data: {
        'email': event.email,
        'password': event.password,
      });
      final data = response.data['data'];
      await _api.saveTokens(
        data['tokens']['access_token'],
        data['tokens']['refresh_token'],
      );
      emit(AuthAuthenticated(user: data['user']));
    } catch (e) {
      emit(AuthError(message: _extractError(e)));
    }
  }

  Future<void> _onRegister(AuthRegisterRequested event, Emitter<AuthState> emit) async {
    emit(AuthLoading());
    try {
      final response = await _api.dio.post('/auth/register', data: {
        'email': event.email,
        'password': event.password,
      });
      final data = response.data['data'];
      await _api.saveTokens(
        data['tokens']['access_token'],
        data['tokens']['refresh_token'],
      );
      emit(AuthAuthenticated(user: data['user']));
    } catch (e) {
      emit(AuthError(message: _extractError(e)));
    }
  }

  Future<void> _onLogout(AuthLogoutRequested event, Emitter<AuthState> emit) async {
    await _api.clearTokens();
    emit(AuthUnauthenticated());
  }

  Future<void> _onCheck(AuthCheckRequested event, Emitter<AuthState> emit) async {
    final hasToken = await _api.hasToken();
    if (hasToken) {
      try {
        final response = await _api.dio.get('/dashboard');
        if (response.statusCode == 200) {
          emit(AuthAuthenticated(user: {}));
          return;
        }
      } catch (_) {}
    }
    emit(AuthUnauthenticated());
  }

  String _extractError(dynamic e) {
    if (e is DioException && e.response?.data != null) {
      final data = e.response!.data;
      if (data is Map && data.containsKey('detail')) return data['detail'];
    }
    return 'Something went wrong. Please try again.';
  }
}
