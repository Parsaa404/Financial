import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:gap/gap.dart';

import '../../../core/theme.dart';
import '../../../shared/services/api_client.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});
  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  int _currentStep = 0;
  final Map<String, String> _answers = {};
  bool _loading = false;

  final List<Map<String, dynamic>> _questions = [
    {'id': 'goal', 'question': "What's your main financial goal?", 'options': [
      {'value': 'save_more', 'label': 'Save More', 'icon': Icons.savings_rounded},
      {'value': 'get_out_of_debt', 'label': 'Get Out of Debt', 'icon': Icons.money_off_rounded},
      {'value': 'understand_spending', 'label': 'Understand Spending', 'icon': Icons.pie_chart_rounded},
      {'value': 'plan_purchase', 'label': 'Plan a Purchase', 'icon': Icons.shopping_bag_rounded},
    ]},
    {'id': 'spending_style', 'question': 'How would you describe your spending?', 'options': [
      {'value': 'impulsive', 'label': 'Impulsive', 'icon': Icons.flash_on_rounded},
      {'value': 'mostly_careful', 'label': 'Mostly Careful', 'icon': Icons.balance_rounded},
      {'value': 'budget_conscious', 'label': 'Budget Conscious', 'icon': Icons.calculate_rounded},
      {'value': 'inconsistent', 'label': 'Inconsistent', 'icon': Icons.swap_vert_rounded},
    ]},
    {'id': 'pay_frequency', 'question': 'How often do you get paid?', 'options': [
      {'value': 'weekly', 'label': 'Weekly', 'icon': Icons.calendar_view_week_rounded},
      {'value': 'biweekly', 'label': 'Bi-weekly', 'icon': Icons.date_range_rounded},
      {'value': 'monthly', 'label': 'Monthly', 'icon': Icons.calendar_month_rounded},
      {'value': 'irregular', 'label': 'Irregular', 'icon': Icons.shuffle_rounded},
    ]},
    {'id': 'priority', 'question': 'What matters most to you here?', 'options': [
      {'value': 'quick_decisions', 'label': 'Quick Decisions', 'icon': Icons.psychology_rounded},
      {'value': 'deep_insights', 'label': 'Deep Insights', 'icon': Icons.insights_rounded},
      {'value': 'goal_tracking', 'label': 'Goal Tracking', 'icon': Icons.flag_rounded},
      {'value': 'spending_overview', 'label': 'Spending Overview', 'icon': Icons.dashboard_rounded},
    ]},
    {'id': 'currency', 'question': 'Your primary currency?', 'options': [
      {'value': 'USD', 'label': 'USD \$', 'icon': Icons.attach_money_rounded},
      {'value': 'EUR', 'label': 'EUR €', 'icon': Icons.euro_rounded},
      {'value': 'GBP', 'label': 'GBP £', 'icon': Icons.currency_pound_rounded},
      {'value': 'OTHER', 'label': 'Other', 'icon': Icons.language_rounded},
    ]},
  ];

  Future<void> _complete() async {
    setState(() => _loading = true);
    try {
      await ApiClient().dio.post('/onboarding/complete', data: {'answers': _answers});
      if (mounted) context.go('/');
    } catch (_) {
      if (mounted) context.go('/');
    }
  }

  @override
  Widget build(BuildContext context) {
    final q = _questions[_currentStep];
    final progress = (_currentStep + 1) / _questions.length;

    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Progress bar
              LinearProgressIndicator(value: progress, backgroundColor: AppTheme.card, color: AppTheme.primary, minHeight: 4),
              const Gap(8),
              Text('${_currentStep + 1} of ${_questions.length}', style: Theme.of(context).textTheme.bodySmall, textAlign: TextAlign.right),
              const Gap(32),

              Text(q['question'], style: Theme.of(context).textTheme.titleLarge, textAlign: TextAlign.center),
              const Gap(32),

              // Options
              ...List.generate((q['options'] as List).length, (i) {
                final opt = q['options'][i];
                final selected = _answers[q['id']] == opt['value'];
                return Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: GestureDetector(
                    onTap: () {
                      setState(() => _answers[q['id']] = opt['value']);
                      Future.delayed(const Duration(milliseconds: 300), () {
                        if (_currentStep < _questions.length - 1) {
                          setState(() => _currentStep++);
                        } else {
                          _complete();
                        }
                      });
                    },
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 200),
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: selected ? AppTheme.primary.withOpacity(0.15) : AppTheme.card,
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(color: selected ? AppTheme.primary : AppTheme.cardBorder, width: selected ? 2 : 1),
                      ),
                      child: Row(
                        children: [
                          Icon(opt['icon'], color: selected ? AppTheme.primary : AppTheme.textSecondary),
                          const Gap(16),
                          Text(opt['label'], style: TextStyle(color: selected ? AppTheme.primary : AppTheme.textPrimary, fontWeight: FontWeight.w500, fontSize: 16)),
                          const Spacer(),
                          if (selected) const Icon(Icons.check_circle, color: AppTheme.primary),
                        ],
                      ),
                    ),
                  ),
                );
              }),

              const Spacer(),
              if (_currentStep > 0)
                TextButton(
                  onPressed: () => setState(() => _currentStep--),
                  child: const Text('Back', style: TextStyle(color: AppTheme.textSecondary)),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
