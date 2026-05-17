import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:gap/gap.dart';

import '../../../core/theme.dart';
import '../../../shared/services/api_client.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});
  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  Map<String, dynamic>? _data;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadDashboard();
  }

  Future<void> _loadDashboard() async {
    try {
      final response = await ApiClient().dio.get('/dashboard');
      setState(() { _data = response.data['data']; _loading = false; });
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _loadDashboard,
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : SingleChildScrollView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Header
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            Text('Good ${_greeting()}', style: Theme.of(context).textTheme.bodyMedium),
                            const Gap(4),
                            Text('Your Finances', style: Theme.of(context).textTheme.headlineLarge),
                          ]),
                          GestureDetector(
                            onTap: () => context.go('/decision'),
                            child: Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                gradient: const LinearGradient(colors: [AppTheme.primary, AppTheme.secondary]),
                                borderRadius: BorderRadius.circular(14),
                              ),
                              child: const Icon(Icons.psychology_rounded, color: Colors.white, size: 28),
                            ),
                          ),
                        ],
                      ),
                      const Gap(24),

                      // Balance card
                      _BalanceCard(
                        balance: _data?['total_balance']?.toDouble() ?? 0.0,
                        currency: _data?['currency'] ?? 'USD',
                      ),
                      const Gap(20),

                      // Quick actions
                      Row(children: [
                        Expanded(child: _QuickAction(icon: Icons.add, label: 'Add', color: AppTheme.safe, onTap: () => context.go('/transactions/add'))),
                        const Gap(12),
                        Expanded(child: _QuickAction(icon: Icons.psychology, label: 'Decide', color: AppTheme.primary, onTap: () => context.go('/decision'))),
                        const Gap(12),
                        Expanded(child: _QuickAction(icon: Icons.trending_up, label: 'Forecast', color: AppTheme.accent, onTap: () => context.go('/forecast'))),
                        const Gap(12),
                        Expanded(child: _QuickAction(icon: Icons.flag, label: 'Goals', color: AppTheme.caution, onTap: () => context.go('/goals'))),
                      ]),
                      const Gap(24),

                      // Accounts
                      Text('Accounts', style: Theme.of(context).textTheme.titleLarge),
                      const Gap(12),
                      if (_data?['accounts'] != null)
                        ...(_data!['accounts'] as List).map((a) => _AccountCard(account: a)),

                      const Gap(24),
                      // Insights
                      if ((_data?['unread_insights_count'] ?? 0) > 0) ...[
                        Text('Insights', style: Theme.of(context).textTheme.titleLarge),
                        const Gap(12),
                        ...(_data!['recent_insights'] as List).map((i) => _InsightCard(insight: i)),
                      ],
                    ],
                  ),
                ),
        ),
      ),
    );
  }

  String _greeting() {
    final hour = DateTime.now().hour;
    if (hour < 12) return 'Morning';
    if (hour < 17) return 'Afternoon';
    return 'Evening';
  }
}

class _BalanceCard extends StatelessWidget {
  final double balance;
  final String currency;
  const _BalanceCard({required this.balance, required this.currency});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [AppTheme.primary.withOpacity(0.8), AppTheme.secondary.withOpacity(0.6)],
          begin: Alignment.topLeft, end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('Total Balance', style: TextStyle(color: Colors.white70, fontSize: 14)),
        const Gap(8),
        Text('\$${balance.toStringAsFixed(2)}', style: const TextStyle(color: Colors.white, fontSize: 36, fontWeight: FontWeight.bold)),
        const Gap(4),
        Text(currency, style: const TextStyle(color: Colors.white54, fontSize: 14)),
      ]),
    );
  }
}

class _QuickAction extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;
  const _QuickAction({required this.icon, required this.label, required this.color, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 16),
        decoration: BoxDecoration(
          color: color.withOpacity(0.12),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: color.withOpacity(0.3)),
        ),
        child: Column(children: [
          Icon(icon, color: color, size: 24),
          const Gap(6),
          Text(label, style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600)),
        ]),
      ),
    );
  }
}

class _AccountCard extends StatelessWidget {
  final Map<String, dynamic> account;
  const _AccountCard({required this.account});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(color: AppTheme.primary.withOpacity(0.15), borderRadius: BorderRadius.circular(10)),
            child: Icon(_iconForType(account['type']), color: AppTheme.primary, size: 20),
          ),
          const Gap(12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(account['name'], style: const TextStyle(color: AppTheme.textPrimary, fontWeight: FontWeight.w600)),
            Text(account['type'].toString().toUpperCase(), style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12)),
          ])),
          Text('\$${(account['balance'] as num).toStringAsFixed(2)}', style: const TextStyle(color: AppTheme.textPrimary, fontWeight: FontWeight.bold, fontSize: 16)),
        ]),
      ),
    );
  }

  IconData _iconForType(String? type) {
    return switch (type) {
      'checking' => Icons.account_balance_rounded,
      'savings' => Icons.savings_rounded,
      'credit' => Icons.credit_card_rounded,
      'cash' => Icons.money_rounded,
      'investment' => Icons.trending_up_rounded,
      _ => Icons.account_balance_wallet_rounded,
    };
  }
}

class _InsightCard extends StatelessWidget {
  final Map<String, dynamic> insight;
  const _InsightCard({required this.insight});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(children: [
          const Icon(Icons.lightbulb_rounded, color: AppTheme.caution),
          const Gap(12),
          Expanded(child: Text(insight['title'] ?? '', style: const TextStyle(color: AppTheme.textPrimary))),
        ]),
      ),
    );
  }
}
