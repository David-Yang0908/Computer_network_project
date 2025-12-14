import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../widgets/glass_container.dart';
import '../widgets/donut_chart.dart';
import '../services/api_service.dart';
import '../models/task_model.dart';
import 'ai_input_screen.dart';
import 'calendar_screen.dart';
import 'rewards_screen.dart';
import 'task_detail_screen.dart';
import '../widgets/add_task_dialog.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final ApiService _api = ApiService();
  int _currentIndex = 0;
  
  // Key to control DashboardContent state
  final GlobalKey<_DashboardContentState> _dashboardKey = GlobalKey();

  final List<Widget> _screens = [];
  
  @override
  void initState() {
    super.initState();
    _screens.add(DashboardContent(key: _dashboardKey));
    _screens.add(const CalendarScreen());
    _screens.add(const RewardsScreen());
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBody: true, 
      extendBodyBehindAppBar: true,
      floatingActionButton: _currentIndex == 0 ? Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          // AI Button (Small)
          FloatingActionButton.small(
            heroTag: "btn_ai",
            backgroundColor: Colors.blueAccent,
            onPressed: () async {
               await Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const AiInputScreen()),
              );
              _dashboardKey.currentState?._refreshData();
            },
            child: const Icon(Icons.auto_awesome, color: Colors.white),
          ),
          const SizedBox(width: 10),
          // Add Task Button (Big)
          FloatingActionButton(
            heroTag: "btn_add",
            backgroundColor: Colors.pinkAccent,
            onPressed: () async {
              final bool? result = await showDialog(
                context: context,
                builder: (context) => const AddTaskDialog(),
              );
              if (result == true) {
                 // 1. Refresh to show the new raw task immediately
                 _dashboardKey.currentState?._refreshData();
                 
                 if (context.mounted) {
                   ScaffoldMessenger.of(context).showSnackBar(
                     const SnackBar(
                       content: Text("Task added. AI is analyzing & decomposing... 🤖"),
                       duration: Duration(seconds: 2),
                     ),
                   );
                 }

                 // 2. Trigger AI Decomposition in background
                 try {
                   await _api.runAiDecomposition();
                   if (context.mounted) {
                     ScaffoldMessenger.of(context).showSnackBar(
                       const SnackBar(content: Text("AI Analysis Complete! Schedule updated. ✨")),
                     );
                     // 3. Refresh again to show decomposed subtasks
                     _dashboardKey.currentState?._refreshData();
                   }
                 } catch (e) {
                   if (context.mounted) {
                     ScaffoldMessenger.of(context).showSnackBar(
                       SnackBar(content: Text("AI Error: $e")),
                     );
                   }
                 }
              }
            },
            child: const Icon(Icons.add, color: Colors.white),
          ),
        ],
      ) : null,
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          boxShadow: AppTheme.glassShadow,
        ),
        child: ClipRRect(
          borderRadius: const BorderRadius.only(topLeft: Radius.circular(20), topRight: Radius.circular(20)),
          child: BottomNavigationBar(
            currentIndex: _currentIndex,
            onTap: (index) => setState(() => _currentIndex = index),
            backgroundColor: AppTheme.glassSurface.withOpacity(0.1), // Glassy
            selectedItemColor: Colors.pinkAccent,
            unselectedItemColor: Colors.white54,
            elevation: 0,
            type: BottomNavigationBarType.fixed,
            items: const [
              BottomNavigationBarItem(icon: Icon(Icons.dashboard_rounded), label: 'Today'),
              BottomNavigationBarItem(icon: Icon(Icons.calendar_month_rounded), label: 'Calendar'),
              BottomNavigationBarItem(icon: Icon(Icons.emoji_events_rounded), label: 'Rewards'),
            ],
          ),
        ),
      ),
      body: Container(
        decoration: AppTheme.mainBackground,
        child: _screens[_currentIndex],
      ),
    );
  }
}

class DashboardContent extends StatefulWidget {
  const DashboardContent({super.key});

  @override
  State<DashboardContent> createState() => _DashboardContentState();
}

class _DashboardContentState extends State<DashboardContent> {
  final ApiService _api = ApiService();
  late Future<UserStats> _userFuture;
  late Future<List<Task>> _tasksFuture;

  @override
  void initState() {
    super.initState();
    _refreshData();
  }

  void _refreshData() {
    setState(() {
      _userFuture = _api.fetchUser();
      _tasksFuture = _api.fetchTasks();
    });
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 20),
          // --- Top Section: Score & Donut ---
          FutureBuilder<UserStats>(
            future: _userFuture,
            builder: (context, snapshot) {
              if (snapshot.hasData) {
                return Center(
                  child: DonutChart(
                    score: snapshot.data!.score,
                    level: snapshot.data!.level,
                  ),
                );
              }
              return const Center(child: CircularProgressIndicator(color: Colors.white));
            },
          ),
          
          const Padding(
            padding: EdgeInsets.fromLTRB(24, 30, 24, 10),
            child: Text(
              "Today's Timeline",
              style: TextStyle(
                color: Colors.white,
                fontSize: 22,
                fontWeight: FontWeight.bold,
                fontFamily: 'Poppins'
              ),
            ),
          ),

          // --- Task List ---
          Expanded(
            child: FutureBuilder<List<Task>>(
              future: _tasksFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator(color: Colors.white));
                }
                if (!snapshot.hasData || snapshot.data!.isEmpty) {
                  return const Center(
                    child: Text(
                      "No tasks today.\nRelax or ask AI to plan!",
                      textAlign: TextAlign.center,
                      style: TextStyle(color: Colors.white70),
                    ),
                  );
                }

                final tasks = snapshot.data!;
                return ListView.builder(
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  itemCount: tasks.length,
                  itemBuilder: (context, index) {
                    final task = tasks[index];
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 16),
                      child: GestureDetector(
                        onTap: () async {
                          await Navigator.push(
                            context, 
                            MaterialPageRoute(builder: (context) => TaskDetailScreen(task: task))
                          );
                          _refreshData();
                        },
                        child: GlassContainer(
                          padding: const EdgeInsets.all(16),
                          child: Row(
                            children: [
                              // Time
                              Column(
                                children: [
                                  Text(
                                    task.deadline != null 
                                      ? "${task.deadline!.hour}:${task.deadline!.minute.toString().padLeft(2,'0')}" 
                                      : "--:--",
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  const Text("PM", style: TextStyle(color: Colors.white70, fontSize: 10)),
                                ],
                              ),
                              const SizedBox(width: 16),
                              // Content
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      task.title,
                                      style: const TextStyle(
                                        color: Colors.white,
                                        fontSize: 16,
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                    if (task.description.isNotEmpty)
                                      Text(
                                        task.description,
                                        style: const TextStyle(color: Colors.white70, fontSize: 12),
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                  ],
                                ),
                              ),
                                                                                              // Checkbox
                                                                                              Row(
                                                                                                mainAxisSize: MainAxisSize.min,
                                                                                                children: [
                                                                                                  IconButton(
                                                                                                    icon: const Icon(Icons.delete_outline, color: Colors.white54),
                                                                                                    onPressed: () async {
                                                                                                      if (task.eventId == null) {
                                                                                                         ScaffoldMessenger.of(context).showSnackBar(
                                                                                                            const SnackBar(content: Text("Cannot delete legacy task (No Event ID)")),
                                                                                                         );
                                                                                                         return;
                                                                                                      }
                                                                                                      try {
                                                                                                        await _api.deleteEvent(task.eventId!);
                                                                                                        _refreshData();
                                                                                                      } catch (e) {
                                                                                                        if (context.mounted) {
                                                                                                          ScaffoldMessenger.of(context).showSnackBar(
                                                                                                            SnackBar(content: Text("Error deleting: $e")),
                                                                                                          );
                                                                                                        }
                                                                                                      }
                                                                                                    },
                                                                                                  ),
                                                                                                  IconButton(
                                                                                                    icon: const Icon(Icons.check_circle_outline, color: Colors.white54),
                                                                                                    onPressed: () async {
                                                                                                      await _api.completeTask(task.id);
                                                                                                      _refreshData();
                                                                                                    },
                                                                                                  ),
                                                                                                ],
                                                                                              )
                                                              
                              
                            ],
                          ),
                        ),
                      ),
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}