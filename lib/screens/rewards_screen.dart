import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../theme/app_theme.dart';
import '../widgets/glass_container.dart';
import '../services/api_service.dart';
import 'completed_tasks_screen.dart';

class RewardsScreen extends StatefulWidget {
  const RewardsScreen({super.key});

  @override
  State<RewardsScreen> createState() => _RewardsScreenState();
}

class _RewardsScreenState extends State<RewardsScreen> {
  final ApiService _api = ApiService();
  List<dynamic> _rewards = [];
  List<dynamic> _stats = [];
  int _currentScore = 0;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  void _loadData() async {
    try {
      final user = await _api.fetchUser();
      final rewards = await _api.fetchRewards();
      final stats = await _api.fetchWeeklyStats();
      
      if (mounted) {
        setState(() {
          _currentScore = user.score;
          _rewards = rewards;
          _stats = stats;
        });
      }
    } catch (e) {
      print("Error loading rewards data: $e");
    }
  }

  void _redeem(int id, int cost, String title, String icon) async {
    try {
      final newScore = await _api.redeemReward(id);
      setState(() => _currentScore = newScore);
      if (mounted) {
        _showRedeemSuccessDialog(title, icon);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
      }
    }
  }

  void _showRedeemSuccessDialog(String title, String icon) {
    showDialog(
      context: context,
      builder: (context) => Dialog(
        backgroundColor: Colors.transparent,
        child: GlassContainer(
          padding: const EdgeInsets.all(30),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(icon, style: const TextStyle(fontSize: 80))
                  .animate()
                  .scale(duration: 600.ms, curve: Curves.elasticOut)
                  .then(delay: 200.ms)
                  .shimmer(duration: 1200.ms),
              const SizedBox(height: 20),
              const Text("Redeemed!", style: TextStyle(color: Colors.pinkAccent, fontSize: 24, fontWeight: FontWeight.bold))
                  .animate().fadeIn().moveY(begin: 20, end: 0),
              const SizedBox(height: 10),
              Text("Enjoy your $title", style: const TextStyle(color: Colors.white, fontSize: 18), textAlign: TextAlign.center)
                  .animate().fadeIn(delay: 300.ms),
              const SizedBox(height: 30),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.pinkAccent,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                ),
                onPressed: () => Navigator.pop(context),
                child: const Text("Awesome!", style: TextStyle(color: Colors.white)),
              )
            ],
          ),
        ),
      ),
    );
  }

  void _addNewReward() {
    final titleController = TextEditingController();
    final costController = TextEditingController();
    String selectedIcon = '🎁';
    final List<String> icons = ['🎁', '🎮', '☕', '🍔', '🎬', '✈️', '💤', '🏃', '🎵', '📚'];

    showModalBottomSheet(
      context: context, 
      isScrollControlled: true, // Allow full height and keyboard adaptation
      backgroundColor: Colors.transparent,
      builder: (context) => StatefulBuilder(
        builder: (context, setState) {
          return Padding(
            padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
            child: GlassContainer(
              padding: const EdgeInsets.all(24),
              // Optional: Add rounded corners to the top if desired, GlassContainer handles radius usually
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Center(
                      child: Container(
                        width: 40, height: 4, 
                        margin: const EdgeInsets.only(bottom: 20),
                        decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(2))
                      ),
                    ),
                    const Text("Add New Reward", style: TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 20),
                    
                    // Name
                    TextField(
                      controller: titleController,
                      style: const TextStyle(color: Colors.white),
                      decoration: const InputDecoration(
                        labelText: "Reward Name",
                        labelStyle: TextStyle(color: Colors.white70),
                        enabledBorder: UnderlineInputBorder(borderSide: BorderSide(color: Colors.white24)),
                      ),
                    ),
                    const SizedBox(height: 20),
                    
                    // Cost
                    TextField(
                      controller: costController,
                      style: const TextStyle(color: Colors.white),
                      decoration: const InputDecoration(
                        labelText: "Cost (Points)",
                        labelStyle: TextStyle(color: Colors.white70),
                        enabledBorder: UnderlineInputBorder(borderSide: BorderSide(color: Colors.white24)),
                      ),
                      keyboardType: TextInputType.number,
                    ),
                    const SizedBox(height: 20),
                    
                    // Icon Selector
                    const Text("Select Icon", style: TextStyle(color: Colors.white70, fontSize: 14)),
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: icons.map((icon) => GestureDetector(
                        onTap: () => setState(() => selectedIcon = icon),
                        child: Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: selectedIcon == icon ? Colors.pinkAccent.withOpacity(0.5) : Colors.white10,
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                              color: selectedIcon == icon ? Colors.pinkAccent : Colors.transparent,
                            ),
                          ),
                          child: Text(icon, style: const TextStyle(fontSize: 24)),
                        ),
                      )).toList(),
                    ),
                    
                    const SizedBox(height: 30),
                    
                    // Actions
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.pinkAccent,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                          padding: const EdgeInsets.symmetric(vertical: 16)
                        ),
                        onPressed: () async {
                          if (titleController.text.isNotEmpty && costController.text.isNotEmpty) {
                            await _api.addReward(titleController.text, int.parse(costController.text), selectedIcon);
                            _loadData();
                            if (context.mounted) Navigator.pop(context);
                          }
                        }, 
                        child: const Text("Add Reward", style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
                      ),
                    ),
                    const SizedBox(height: 20),
                  ],
                ),
              ),
            ),
          );
        }
      )
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: AppTheme.mainBackground,
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Score Header
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text("My Points", style: TextStyle(color: Colors.white70, fontSize: 14)),
                      Text("$_currentScore", style: const TextStyle(color: Colors.white, fontSize: 32, fontWeight: FontWeight.bold)),
                    ],
                  ),
                  IconButton(onPressed: _addNewReward, icon: const Icon(Icons.add_circle, color: Colors.pinkAccent, size: 30))
                ],
              ),
              const SizedBox(height: 20),

              // Weekly Stats Chart
              const Text("Weekly Performance", style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 10),
              GestureDetector(
                onTap: () {
                  Navigator.push(context, MaterialPageRoute(builder: (context) => const CompletedTasksScreen()));
                },
                child: GlassContainer(
                  height: 150,
                  padding: const EdgeInsets.all(16),
                  child: BarChart(
                    BarChartData(
                      alignment: BarChartAlignment.spaceAround,
                      maxY: 200, // Adjusted for score points
                      barTouchData: BarTouchData(enabled: false),
                      titlesData: FlTitlesData(
                        show: true,
                        bottomTitles: AxisTitles(
                          sideTitles: SideTitles(
                            showTitles: true,
                            getTitlesWidget: (value, meta) {
                              if (value.toInt() < _stats.length) {
                                return Text(_stats[value.toInt()]['day'], style: const TextStyle(color: Colors.white, fontSize: 10));
                              }
                              return const Text('');
                            },
                          ),
                        ),
                        leftTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                        topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                        rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                      ),
                      gridData: const FlGridData(show: false),
                      borderData: FlBorderData(show: false),
                      barGroups: _stats.asMap().entries.map((e) {
                        return BarChartGroupData(
                          x: e.key,
                          barRods: [
                            BarChartRodData(
                              toY: (e.value['score'] as num).toDouble(), // Use score instead of rate
                              color: Colors.amber, // Use gold color for points
                              width: 12,
                              borderRadius: BorderRadius.circular(4),
                            )
                          ]
                        );
                      }).toList(),
                    )
                  ),
                ),
              ),

              const SizedBox(height: 20),
              const Text("Rewards Shop", style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 10),

              // Rewards Grid
              Expanded(
                child: _rewards.isEmpty 
                  ? LayoutBuilder(
                      builder: (context, constraints) {
                        return SingleChildScrollView(
                          physics: const AlwaysScrollableScrollPhysics(),
                          child: ConstrainedBox(
                            constraints: BoxConstraints(minHeight: constraints.maxHeight),
                            child: Center(
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  const Icon(Icons.shopping_bag_outlined, size: 60, color: Colors.white24),
                                  const SizedBox(height: 10),
                                  const Text("No rewards yet.", style: TextStyle(color: Colors.white54)),
                                  TextButton(
                                    onPressed: _addNewReward,
                                    child: const Text("Create your first reward!", style: TextStyle(color: Colors.pinkAccent)),
                                  )
                                ],
                              ),
                            ),
                          ),
                        );
                      }
                    )
                  : GridView.builder(
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 2,
                    crossAxisSpacing: 10,
                    mainAxisSpacing: 10,
                    childAspectRatio: 1.1,
                  ),
                  itemCount: _rewards.length,
                  itemBuilder: (context, index) {
                    final reward = _rewards[index];
                    return GlassContainer(
                      padding: const EdgeInsets.all(12),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(reward['icon'], style: const TextStyle(fontSize: 32)),
                          const SizedBox(height: 8),
                          Text(reward['title'], style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold), textAlign: TextAlign.center),
                          const Spacer(),
                          ElevatedButton(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: _currentScore >= reward['cost'] ? Colors.pinkAccent : Colors.grey,
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                            ),
                            onPressed: _currentScore >= reward['cost'] ? () => _redeem(reward['id'], reward['cost'], reward['title'], reward['icon']) : null,
                            child: Text("${reward['cost']} pts", style: const TextStyle(color: Colors.white)),
                          )
                        ],
                      ),
                    );
                  },
                ),
              )
            ],
          ),
        ),
      ),
    );
  }
}
