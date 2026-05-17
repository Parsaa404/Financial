import 'package:flutter/material.dart';
import 'package:gap/gap.dart';
import 'package:percent_indicator/linear_percent_indicator.dart';

import '../../../core/theme.dart';
import '../../../shared/services/api_client.dart';

class GoalsScreen extends StatefulWidget {
  const GoalsScreen({super.key});
  @override
  State<GoalsScreen> createState() => _GoalsScreenState();
}

class _GoalsScreenState extends State<GoalsScreen> {
  List<Map<String, dynamic>> _goals = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await ApiClient().dio.get('/goals');
      setState(() {
        _goals = List<Map<String, dynamic>>.from(r.data['data'] ?? []);
        _loading = false;
      });
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  void _showAddGoal() {
    final titleCtrl = TextEditingController();
    final amountCtrl = TextEditingController();
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppTheme.surface,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (ctx) => Padding(
        padding: EdgeInsets.fromLTRB(20, 20, 20, MediaQuery.of(ctx).viewInsets.bottom + 20),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Container(width: 40, height: 4, decoration: BoxDecoration(color: AppTheme.cardBorder, borderRadius: BorderRadius.circular(2))),
          const Gap(20),
          const Text('New Goal', style: TextStyle(color: AppTheme.textPrimary, fontSize: 20, fontWeight: FontWeight.bold)),
          const Gap(20),
          TextField(controller: titleCtrl, style: const TextStyle(color: AppTheme.textPrimary), decoration: const InputDecoration(labelText: 'Goal Title')),
          const Gap(12),
          TextField(controller: amountCtrl, keyboardType: TextInputType.number, style: const TextStyle(color: AppTheme.textPrimary), decoration: const InputDecoration(labelText: 'Target Amount', prefixText: '\$ ')),
          const Gap(20),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: () async {
                if (titleCtrl.text.isEmpty || amountCtrl.text.isEmpty) return;
                try {
                  await ApiClient().dio.post('/goals', data: {
                    'title': titleCtrl.text,
                    'target_amount': double.parse(amountCtrl.text),
                  });
                  Navigator.pop(ctx);
                  _load();
                } catch (_) {}
              },
              child: const Text('Create Goal'),
            ),
          ),
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 12),
            child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
              Text('Goals', style: Theme.of(context).textTheme.headlineLarge),
              IconButton(
                onPressed: _showAddGoal,
                icon: Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(color: AppTheme.primary, borderRadius: BorderRadius.circular(10)),
                  child: const Icon(Icons.add, color: Colors.white, size: 20),
                ),
              ),
            ]),
          ),
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _goals.isEmpty
                    ? Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
                        Icon(Icons.flag_rounded, size: 64, color: AppTheme.textSecondary.withOpacity(0.3)),
                        const Gap(16),
                        const Text('No goals yet', style: TextStyle(color: AppTheme.textSecondary)),
                        const Gap(8),
                        ElevatedButton.icon(onPressed: _showAddGoal, icon: const Icon(Icons.add, size: 18), label: const Text('Add Goal')),
                      ]))
                    : RefreshIndicator(
                        onRefresh: _load,
                        child: ListView.builder(
                          padding: const EdgeInsets.symmetric(horizontal: 20),
                          itemCount: _goals.length,
                          itemBuilder: (_, i) => _GoalCard(goal: _goals[i]),
                        ),
                      ),
          ),
        ]),
      ),
    );
  }
}

class _GoalCard extends StatelessWidget {
  final Map<String, dynamic> goal;
  const _GoalCard({required this.goal});

  @override
  Widget build(BuildContext context) {
    final progress = (goal['progress_pct'] as num?)?.toDouble() ?? 0;
    final target = (goal['target_amount'] as num?)?.toDouble() ?? 0;
    final saved = (goal['saved_amount'] as num?)?.toDouble() ?? 0;
    final emoji = goal['emoji'] ?? '🎯';

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Text(emoji, style: const TextStyle(fontSize: 24)),
            const Gap(12),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(goal['title'] ?? '', style: const TextStyle(color: AppTheme.textPrimary, fontWeight: FontWeight.w600, fontSize: 16)),
              const Gap(2),
              Text('${progress.toStringAsFixed(1)}% complete', style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12)),
            ])),
            Text('\$${saved.toStringAsFixed(0)} / \$${target.toStringAsFixed(0)}',
                style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13)),
          ]),
          const Gap(12),
          LinearPercentIndicator(
            lineHeight: 8,
            percent: (progress / 100).clamp(0, 1),
            backgroundColor: AppTheme.cardBorder,
            progressColor: progress >= 100 ? AppTheme.safe : AppTheme.primary,
            barRadius: const Radius.circular(4),
            padding: EdgeInsets.zero,
            animation: true,
          ),
        ]),
      ),
    );
  }
}
