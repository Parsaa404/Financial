import 'package:flutter/material.dart';
import 'package:gap/gap.dart';
import 'package:percent_indicator/circular_percent_indicator.dart';

import '../../../core/theme.dart';
import '../../../shared/services/api_client.dart';

/// Hero feature — "Can I afford this?" decision screen.
class DecisionScreen extends StatefulWidget {
  const DecisionScreen({super.key});
  @override
  State<DecisionScreen> createState() => _DecisionScreenState();
}

class _DecisionScreenState extends State<DecisionScreen> with SingleTickerProviderStateMixin {
  final _amountController = TextEditingController();
  Map<String, dynamic>? _result;
  bool _loading = false;
  late AnimationController _animController;
  late Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(vsync: this, duration: const Duration(milliseconds: 600));
    _scaleAnimation = CurvedAnimation(parent: _animController, curve: Curves.elasticOut);
  }

  @override
  void dispose() {
    _amountController.dispose();
    _animController.dispose();
    super.dispose();
  }

  Future<void> _decide() async {
    final amountText = _amountController.text.trim();
    if (amountText.isEmpty) return;
    setState(() { _loading = true; _result = null; });
    try {
      final r = await ApiClient().dio.post('/decision/can-afford', data: {
        'amount': double.parse(amountText),
      });
      setState(() { _result = r.data['data']; _loading = false; });
      _animController.forward(from: 0);
    } catch (_) {
      setState(() => _loading = false);
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Failed to get decision')));
    }
  }

  Color _decisionColor(String? decision) => switch (decision) {
    'SAFE' => AppTheme.safe,
    'CAUTION' => AppTheme.caution,
    'RISKY' => AppTheme.risky,
    _ => AppTheme.textSecondary,
  };

  IconData _decisionIcon(String? decision) => switch (decision) {
    'SAFE' => Icons.check_circle_rounded,
    'CAUTION' => Icons.warning_rounded,
    'RISKY' => Icons.dangerous_rounded,
    _ => Icons.help_rounded,
  };

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            const Gap(10),
            Text('Can I Afford This?', style: Theme.of(context).textTheme.headlineLarge, textAlign: TextAlign.center),
            const Gap(8),
            Text('Enter an amount and find out instantly', style: Theme.of(context).textTheme.bodyMedium, textAlign: TextAlign.center),
            const Gap(32),

            // Amount input
            Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: AppTheme.card,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: AppTheme.cardBorder),
              ),
              child: Column(children: [
                const Text('Purchase Amount', style: TextStyle(color: AppTheme.textSecondary)),
                const Gap(12),
                TextField(
                  controller: _amountController,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  style: const TextStyle(color: AppTheme.textPrimary, fontSize: 48, fontWeight: FontWeight.bold),
                  textAlign: TextAlign.center,
                  decoration: const InputDecoration(prefixText: '\$  ', border: InputBorder.none, hintText: '0.00', hintStyle: TextStyle(color: AppTheme.cardBorder)),
                ),
              ]),
            ),
            const Gap(20),

            // Decide button
            SizedBox(
              height: 56,
              child: ElevatedButton(
                onPressed: _loading ? null : _decide,
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primary,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                ),
                child: _loading
                    ? const SizedBox(height: 24, width: 24, child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.white))
                    : const Text('Can I Afford It?', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              ),
            ),
            const Gap(24),

            // Result
            if (_result != null) ...[
              ScaleTransition(
                scale: _scaleAnimation,
                child: _DecisionResult(result: _result!, color: _decisionColor(_result!['decision']), icon: _decisionIcon(_result!['decision'])),
              ),
              const Gap(16),
              _DetailCard(result: _result!),
              const Gap(16),
              if (_result!['explanation'] != null)
                _ExplanationCard(explanation: _result!['explanation'], suggestion: _result!['suggestion']),
            ],
          ]),
        ),
      ),
    );
  }
}

class _DecisionResult extends StatelessWidget {
  final Map<String, dynamic> result;
  final Color color;
  final IconData icon;
  const _DecisionResult({required this.result, required this.color, required this.icon});

  @override
  Widget build(BuildContext context) {
    final score = (result['risk_score'] as num).toInt();
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: color.withOpacity(0.08),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withOpacity(0.3), width: 2),
      ),
      child: Column(children: [
        CircularPercentIndicator(
          radius: 50,
          lineWidth: 8,
          percent: score / 100.0,
          center: Icon(icon, color: color, size: 40),
          progressColor: color,
          backgroundColor: color.withOpacity(0.2),
          circularStrokeCap: CircularStrokeCap.round,
          animation: true,
          animationDuration: 800,
        ),
        const Gap(16),
        Text(result['decision'], style: TextStyle(color: color, fontSize: 28, fontWeight: FontWeight.bold)),
        const Gap(4),
        Text('Risk Score: $score/100', style: TextStyle(color: color.withOpacity(0.8), fontSize: 14)),
      ]),
    );
  }
}

class _DetailCard extends StatelessWidget {
  final Map<String, dynamic> result;
  const _DetailCard({required this.result});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(children: [
          _Row(label: 'Available Now', value: '\$${(result['available_now'] as num).toStringAsFixed(2)}'),
          const Divider(color: AppTheme.cardBorder, height: 20),
          _Row(label: 'After Purchase', value: '\$${(result['available_after'] as num).toStringAsFixed(2)}'),
          const Divider(color: AppTheme.cardBorder, height: 20),
          _Row(label: 'Month-End Projected', value: '\$${(result['month_end_projected'] as num).toStringAsFixed(2)}'),
          const Divider(color: AppTheme.cardBorder, height: 20),
          _Row(label: 'Upcoming Bills (30d)', value: '\$${(result['upcoming_bills_30d'] as num).toStringAsFixed(2)}'),
        ]),
      ),
    );
  }
}

class _Row extends StatelessWidget {
  final String label;
  final String value;
  const _Row({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
      Text(label, style: const TextStyle(color: AppTheme.textSecondary, fontSize: 14)),
      Text(value, style: const TextStyle(color: AppTheme.textPrimary, fontWeight: FontWeight.w600, fontSize: 14)),
    ]);
  }
}

class _ExplanationCard extends StatelessWidget {
  final String explanation;
  final String? suggestion;
  const _ExplanationCard({required this.explanation, this.suggestion});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Row(children: [
            Icon(Icons.auto_awesome, color: AppTheme.accent, size: 18),
            Gap(8),
            Text('AI Insight', style: TextStyle(color: AppTheme.accent, fontWeight: FontWeight.w600)),
          ]),
          const Gap(12),
          Text(explanation, style: const TextStyle(color: AppTheme.textPrimary, height: 1.5)),
          if (suggestion != null) ...[
            const Gap(12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(color: AppTheme.primary.withOpacity(0.08), borderRadius: BorderRadius.circular(10)),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Icon(Icons.tips_and_updates_rounded, color: AppTheme.primary, size: 18),
                const Gap(8),
                Expanded(child: Text(suggestion!, style: const TextStyle(color: AppTheme.textPrimary, fontSize: 13, height: 1.4))),
              ]),
            ),
          ],
        ]),
      ),
    );
  }
}
