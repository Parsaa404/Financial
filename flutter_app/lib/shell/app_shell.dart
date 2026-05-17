import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../core/theme.dart';

/// App shell with bottom navigation bar.
class AppShell extends StatelessWidget {
  final Widget child;
  const AppShell({super.key, required this.child});

  int _getIndex(BuildContext context) {
    final location = GoRouterState.of(context).uri.toString();
    if (location.startsWith('/transactions')) return 1;
    if (location.startsWith('/decision')) return 2;
    if (location.startsWith('/forecast')) return 3;
    if (location.startsWith('/goals')) return 4;
    return 0;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: child,
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          color: AppTheme.surface,
          border: Border(top: BorderSide(color: AppTheme.cardBorder, width: 0.5)),
        ),
        child: BottomNavigationBar(
          currentIndex: _getIndex(context),
          onTap: (index) {
            switch (index) {
              case 0: context.go('/');
              case 1: context.go('/transactions');
              case 2: context.go('/decision');
              case 3: context.go('/forecast');
              case 4: context.go('/goals');
            }
          },
          items: const [
            BottomNavigationBarItem(icon: Icon(Icons.dashboard_rounded), label: 'Home'),
            BottomNavigationBarItem(icon: Icon(Icons.receipt_long_rounded), label: 'Transactions'),
            BottomNavigationBarItem(icon: Icon(Icons.psychology_rounded), label: 'Decide'),
            BottomNavigationBarItem(icon: Icon(Icons.trending_up_rounded), label: 'Forecast'),
            BottomNavigationBarItem(icon: Icon(Icons.flag_rounded), label: 'Goals'),
          ],
        ),
      ),
    );
  }
}
