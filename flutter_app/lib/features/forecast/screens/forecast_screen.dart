import 'package:flutter/material.dart';
import 'package:gap/gap.dart';
import 'package:fl_chart/fl_chart.dart';

import '../../../core/theme.dart';
import '../../../shared/services/api_client.dart';

class ForecastScreen extends StatefulWidget {
  const ForecastScreen({super.key});
  @override
  State<ForecastScreen> createState() => _ForecastScreenState();
}

class _ForecastScreenState extends State<ForecastScreen> {
  Map<String, dynamic>? _data;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await ApiClient().dio.get('/forecast/monthly');
      setState(() { _data = r.data['data']; _loading = false; });
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : SingleChildScrollView(
                padding: const EdgeInsets.all(20),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('Forecast', style: Theme.of(context).textTheme.headlineLarge),
                  const Gap(8),
                  Text('3-month financial projection', style: Theme.of(context).textTheme.bodyMedium),
                  const Gap(24),

                  // Summary cards
                  Row(children: [
                    Expanded(child: _SummaryCard(label: 'Avg Income', value: _data?['avg_monthly_income'] ?? 0, color: AppTheme.income)),
                    const Gap(12),
                    Expanded(child: _SummaryCard(label: 'Avg Expenses', value: _data?['avg_monthly_expenses'] ?? 0, color: AppTheme.expense)),
                  ]),
                  const Gap(12),
                  _SummaryCard(
                    label: 'Savings Rate',
                    value: ((_data?['savings_rate'] ?? 0) * 100).toDouble(),
                    color: AppTheme.accent,
                    suffix: '%',
                  ),
                  const Gap(24),

                  // Chart
                  if (_data?['monthly'] != null) ...[
                    Text('Monthly Projections', style: Theme.of(context).textTheme.titleLarge),
                    const Gap(16),
                    SizedBox(
                      height: 220,
                      child: _buildChart(),
                    ),
                    const Gap(24),

                    // Monthly breakdown
                    ...(_data!['monthly'] as List).map((m) => _MonthCard(month: Map<String, dynamic>.from(m))),
                  ],
                ]),
              ),
      ),
    );
  }

  Widget _buildChart() {
    final months = List<Map<String, dynamic>>.from(_data?['monthly'] ?? []);
    if (months.isEmpty) return const SizedBox();

    return BarChart(
      BarChartData(
        barTouchData: BarTouchData(enabled: true),
        titlesData: FlTitlesData(
          bottomTitles: AxisTitles(sideTitles: SideTitles(
            showTitles: true,
            getTitlesWidget: (value, meta) {
              final idx = value.toInt();
              if (idx < months.length) {
                return Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(months[idx]['month'].toString().substring(5), style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12)),
                );
              }
              return const SizedBox();
            },
          )),
          leftTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        ),
        borderData: FlBorderData(show: false),
        gridData: const FlGridData(show: false),
        barGroups: List.generate(months.length, (i) {
          final income = (months[i]['projected_income'] as num).toDouble();
          final expenses = (months[i]['projected_expenses'] as num).toDouble();
          return BarChartGroupData(x: i, barRods: [
            BarChartRodData(toY: income, color: AppTheme.income.withOpacity(0.7), width: 16, borderRadius: const BorderRadius.vertical(top: Radius.circular(6))),
            BarChartRodData(toY: expenses, color: AppTheme.expense.withOpacity(0.7), width: 16, borderRadius: const BorderRadius.vertical(top: Radius.circular(6))),
          ]);
        }),
      ),
    );
  }
}

class _SummaryCard extends StatelessWidget {
  final String label;
  final num value;
  final Color color;
  final String suffix;
  const _SummaryCard({required this.label, required this.value, required this.color, this.suffix = ''});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withOpacity(0.08),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: color.withOpacity(0.2)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(label, style: TextStyle(color: color.withOpacity(0.8), fontSize: 12)),
        const Gap(6),
        Text(suffix == '%' ? '${value.toStringAsFixed(1)}$suffix' : '\$${value.toStringAsFixed(2)}',
            style: TextStyle(color: color, fontSize: 22, fontWeight: FontWeight.bold)),
      ]),
    );
  }
}

class _MonthCard extends StatelessWidget {
  final Map<String, dynamic> month;
  const _MonthCard({required this.month});

  @override
  Widget build(BuildContext context) {
    final savings = (month['projected_savings'] as num).toDouble();
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
            Text(month['month'], style: const TextStyle(color: AppTheme.textPrimary, fontWeight: FontWeight.w600)),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: savings >= 0 ? AppTheme.safe.withOpacity(0.15) : AppTheme.risky.withOpacity(0.15),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(savings >= 0 ? '+\$${savings.toStringAsFixed(0)}' : '-\$${savings.abs().toStringAsFixed(0)}',
                  style: TextStyle(color: savings >= 0 ? AppTheme.safe : AppTheme.risky, fontWeight: FontWeight.w600, fontSize: 12)),
            ),
          ]),
          const Gap(8),
          Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
            Text('Income: \$${(month['projected_income'] as num).toStringAsFixed(0)}', style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13)),
            Text('Expenses: \$${(month['projected_expenses'] as num).toStringAsFixed(0)}', style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13)),
          ]),
        ]),
      ),
    );
  }
}
