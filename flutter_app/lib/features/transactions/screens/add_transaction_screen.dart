import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:gap/gap.dart';

import '../../../core/theme.dart';
import '../../../shared/services/api_client.dart';

class AddTransactionScreen extends StatefulWidget {
  const AddTransactionScreen({super.key});
  @override
  State<AddTransactionScreen> createState() => _AddTransactionScreenState();
}

class _AddTransactionScreenState extends State<AddTransactionScreen> {
  final _amountController = TextEditingController();
  final _merchantController = TextEditingController();
  final _noteController = TextEditingController();
  String _type = 'expense';
  String? _accountId;
  List<Map<String, dynamic>> _accounts = [];
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _loadAccounts();
  }

  Future<void> _loadAccounts() async {
    try {
      final r = await ApiClient().dio.get('/dashboard');
      final accounts = List<Map<String, dynamic>>.from(r.data['data']['accounts'] ?? []);
      setState(() {
        _accounts = accounts;
        if (accounts.isNotEmpty) _accountId = accounts[0]['id'].toString();
      });
    } catch (_) {}
  }

  Future<void> _save() async {
    if (_amountController.text.isEmpty || _accountId == null) return;
    setState(() => _saving = true);
    try {
      await ApiClient().dio.post('/transactions', data: {
        'account_id': _accountId,
        'amount': double.parse(_amountController.text),
        'type': _type,
        'merchant': _merchantController.text.isNotEmpty ? _merchantController.text : null,
        'note': _noteController.text.isNotEmpty ? _noteController.text : null,
        'transacted_at': DateTime.now().toUtc().toIso8601String(),
      });
      if (mounted) context.go('/transactions');
    } catch (e) {
      setState(() => _saving = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Failed to save')));
      }
    }
  }

  @override
  void dispose() {
    _amountController.dispose();
    _merchantController.dispose();
    _noteController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Add Transaction', style: TextStyle(color: AppTheme.textPrimary)),
        leading: BackButton(onPressed: () => context.go('/transactions')),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          // Type toggle
          Row(children: [
            Expanded(child: _TypeButton(label: 'Expense', selected: _type == 'expense', color: AppTheme.expense, onTap: () => setState(() => _type = 'expense'))),
            const Gap(12),
            Expanded(child: _TypeButton(label: 'Income', selected: _type == 'income', color: AppTheme.income, onTap: () => setState(() => _type = 'income'))),
          ]),
          const Gap(24),

          // Amount
          TextField(
            controller: _amountController,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            style: const TextStyle(color: AppTheme.textPrimary, fontSize: 32, fontWeight: FontWeight.bold),
            textAlign: TextAlign.center,
            decoration: const InputDecoration(labelText: 'Amount', prefixText: '\$ ', border: InputBorder.none),
          ),
          const Gap(16),

          // Account dropdown
          if (_accounts.isNotEmpty)
            DropdownButtonFormField<String>(
              value: _accountId,
              dropdownColor: AppTheme.card,
              style: const TextStyle(color: AppTheme.textPrimary),
              decoration: const InputDecoration(labelText: 'Account'),
              items: _accounts.map((a) => DropdownMenuItem(value: a['id'].toString(), child: Text(a['name']))).toList(),
              onChanged: (v) => setState(() => _accountId = v),
            ),
          const Gap(16),

          TextField(controller: _merchantController, style: const TextStyle(color: AppTheme.textPrimary), decoration: const InputDecoration(labelText: 'Merchant', prefixIcon: Icon(Icons.store, color: AppTheme.textSecondary))),
          const Gap(16),
          TextField(controller: _noteController, style: const TextStyle(color: AppTheme.textPrimary), decoration: const InputDecoration(labelText: 'Note (optional)', prefixIcon: Icon(Icons.note, color: AppTheme.textSecondary))),
          const Gap(32),

          ElevatedButton(
            onPressed: _saving ? null : _save,
            child: _saving ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)) : const Text('Save Transaction'),
          ),
        ]),
      ),
    );
  }
}

class _TypeButton extends StatelessWidget {
  final String label;
  final bool selected;
  final Color color;
  final VoidCallback onTap;
  const _TypeButton({required this.label, required this.selected, required this.color, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(
          color: selected ? color.withOpacity(0.15) : AppTheme.card,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: selected ? color : AppTheme.cardBorder, width: selected ? 2 : 1),
        ),
        child: Text(label, textAlign: TextAlign.center, style: TextStyle(color: selected ? color : AppTheme.textSecondary, fontWeight: FontWeight.w600)),
      ),
    );
  }
}
