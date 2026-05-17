import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:gap/gap.dart';

import '../../../core/theme.dart';
import '../../../shared/services/api_client.dart';

class TransactionsScreen extends StatefulWidget {
  const TransactionsScreen({super.key});
  @override
  State<TransactionsScreen> createState() => _TransactionsScreenState();
}

class _TransactionsScreenState extends State<TransactionsScreen> {
  List<Map<String, dynamic>> _transactions = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await ApiClient().dio.get('/transactions');
      setState(() {
        _transactions = List<Map<String, dynamic>>.from(r.data['data'] ?? []);
        _loading = false;
      });
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 20, 20, 12),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('Transactions', style: Theme.of(context).textTheme.headlineLarge),
                  IconButton(
                    onPressed: () => context.go('/transactions/add'),
                    icon: Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(color: AppTheme.primary, borderRadius: BorderRadius.circular(10)),
                      child: const Icon(Icons.add, color: Colors.white, size: 20),
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : _transactions.isEmpty
                      ? Center(
                          child: Column(mainAxisSize: MainAxisSize.min, children: [
                            Icon(Icons.receipt_long_rounded, size: 64, color: AppTheme.textSecondary.withOpacity(0.3)),
                            const Gap(16),
                            const Text('No transactions yet', style: TextStyle(color: AppTheme.textSecondary)),
                            const Gap(8),
                            ElevatedButton.icon(
                              onPressed: () => context.go('/transactions/add'),
                              icon: const Icon(Icons.add, size: 18),
                              label: const Text('Add Transaction'),
                            ),
                          ]),
                        )
                      : RefreshIndicator(
                          onRefresh: _load,
                          child: ListView.builder(
                            padding: const EdgeInsets.symmetric(horizontal: 20),
                            itemCount: _transactions.length,
                            itemBuilder: (_, i) => _TransactionTile(txn: _transactions[i]),
                          ),
                        ),
            ),
          ],
        ),
      ),
    );
  }
}

class _TransactionTile extends StatelessWidget {
  final Map<String, dynamic> txn;
  const _TransactionTile({required this.txn});

  @override
  Widget build(BuildContext context) {
    final isExpense = txn['type'] == 'expense';
    final color = isExpense ? AppTheme.expense : AppTheme.income;
    final sign = isExpense ? '-' : '+';
    final amount = (txn['amount'] as num).toDouble();

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(color: color.withOpacity(0.12), borderRadius: BorderRadius.circular(10)),
            child: Icon(isExpense ? Icons.arrow_downward_rounded : Icons.arrow_upward_rounded, color: color, size: 20),
          ),
          const Gap(12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(txn['merchant'] ?? txn['category'] ?? 'Unknown', style: const TextStyle(color: AppTheme.textPrimary, fontWeight: FontWeight.w600)),
              const Gap(2),
              Text(txn['category'] ?? 'Uncategorized', style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12)),
            ]),
          ),
          Text('$sign\$${amount.toStringAsFixed(2)}', style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 16)),
        ]),
      ),
    );
  }
}
