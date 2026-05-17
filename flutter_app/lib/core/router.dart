import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../features/auth/screens/login_screen.dart';
import '../features/auth/screens/register_screen.dart';
import '../features/dashboard/screens/dashboard_screen.dart';
import '../features/decision/screens/decision_screen.dart';
import '../features/forecast/screens/forecast_screen.dart';
import '../features/goals/screens/goals_screen.dart';
import '../features/onboarding/screens/onboarding_screen.dart';
import '../features/transactions/screens/transactions_screen.dart';
import '../features/transactions/screens/add_transaction_screen.dart';
import '../shell/app_shell.dart';

/// App router configuration using go_router.
final GoRouter appRouter = GoRouter(
  initialLocation: '/login',
  routes: [
    // Auth routes (no shell)
    GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
    GoRoute(path: '/register', builder: (_, __) => const RegisterScreen()),
    GoRoute(path: '/onboarding', builder: (_, __) => const OnboardingScreen()),

    // Main app routes (with bottom nav shell)
    ShellRoute(
      builder: (context, state, child) => AppShell(child: child),
      routes: [
        GoRoute(path: '/', builder: (_, __) => const DashboardScreen()),
        GoRoute(path: '/transactions', builder: (_, __) => const TransactionsScreen()),
        GoRoute(path: '/transactions/add', builder: (_, __) => const AddTransactionScreen()),
        GoRoute(path: '/decision', builder: (_, __) => const DecisionScreen()),
        GoRoute(path: '/forecast', builder: (_, __) => const ForecastScreen()),
        GoRoute(path: '/goals', builder: (_, __) => const GoalsScreen()),
      ],
    ),
  ],
);
