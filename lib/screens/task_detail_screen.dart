import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../widgets/glass_container.dart';
import '../models/task_model.dart';
import '../services/api_service.dart';

class TaskDetailScreen extends StatefulWidget {
  final Task task;

  const TaskDetailScreen({super.key, required this.task});

  @override
  State<TaskDetailScreen> createState() => _TaskDetailScreenState();
}

class _TaskDetailScreenState extends State<TaskDetailScreen> {
  final ApiService _api = ApiService();
  late Future<List<Task>> _subtasksFuture;

  @override
  void initState() {
    super.initState();
    if (widget.task.eventId != null) {
      _subtasksFuture = _api.fetchSubtasks(widget.task.eventId!);
    } else {
      _subtasksFuture = Future.value([]); // No event ID, so no subtasks
    }
  }
  
  void _refreshSubtasks() {
    if (widget.task.eventId != null) {
      setState(() {
        _subtasksFuture = _api.fetchSubtasks(widget.task.eventId!);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.white),
          onPressed: () => Navigator.pop(context),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.edit, color: Colors.white),
            onPressed: () {
              // TODO: Implement edit functionality
            },
          )
        ],
      ),
      body: Container(
        decoration: AppTheme.mainBackground,
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // --- Parent Task Info ---
                GlassContainer(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.task_alt, color: Colors.pinkAccent, size: 28),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              widget.task.title,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 24,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 20),
                      Row(
                        children: [
                          const Icon(Icons.access_time, color: Colors.white70),
                          const SizedBox(width: 8),
                          Text(
                            widget.task.date != null 
                              ? "${widget.task.date} ${widget.task.startTime ?? ''}" 
                              : (widget.task.deadline != null 
                                  ? "${widget.task.deadline!.month}/${widget.task.deadline!.day} ${widget.task.deadline!.hour}:${widget.task.deadline!.minute.toString().padLeft(2,'0')}"
                                  : "No Deadline"),
                            style: const TextStyle(color: Colors.white, fontSize: 16),
                          ),
                          const Spacer(),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                            decoration: BoxDecoration(
                              color: Colors.pinkAccent.withOpacity(0.2),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: Colors.pinkAccent)
                            ),
                            child: Text(
                              "+${widget.task.scoreValue} pts",
                              style: const TextStyle(color: Colors.pinkAccent, fontWeight: FontWeight.bold),
                            ),
                          )
                        ],
                      ),
                      const SizedBox(height: 20),
                      
                      // --- Attributes Section ---
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          _buildAttributeBadge("Priority", widget.task.priority, Colors.orangeAccent),
                          _buildAttributeBadge("Importance", widget.task.importance, Colors.purpleAccent),
                          _buildAttributeBadge("Difficulty", widget.task.difficulty, Colors.redAccent),
                        ],
                      ),
                      
                      const SizedBox(height: 20),
                      const Divider(color: Colors.white24),
                      const SizedBox(height: 20),
                      const Text(
                        "Description",
                        style: TextStyle(color: Colors.white70, fontSize: 14, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        widget.task.description.isEmpty ? "No description provided." : widget.task.description,
                        style: const TextStyle(color: Colors.white, fontSize: 16, height: 1.5),
                      ),
                    ],
                  ),
                ),
                
                const SizedBox(height: 30),
                const Text(
                  "Sub-tasks",
                  style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 10),
                
                // --- Subtasks List ---
                Expanded(
                  child: FutureBuilder<List<Task>>(
                    future: _subtasksFuture,
                    builder: (context, snapshot) {
                      if (snapshot.connectionState == ConnectionState.waiting) {
                        return const Center(child: CircularProgressIndicator(color: Colors.white));
                      }
                      if (snapshot.hasError) {
                         return Center(child: Text("Error: ${snapshot.error}", style: const TextStyle(color: Colors.white70)));
                      }
                      
                      final subtasks = snapshot.data ?? [];
                      if (subtasks.isEmpty) {
                        return const Center(child: Text("No subtasks yet.", style: TextStyle(color: Colors.white30)));
                      }

                      return ListView.builder(
                        itemCount: subtasks.length,
                        itemBuilder: (context, index) {
                          final subtask = subtasks[index];
                          return GlassContainer(
                            margin: const EdgeInsets.only(bottom: 10),
                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                            child: Row(
                              children: [
                                Icon(
                                  subtask.isCompleted ? Icons.check_circle : Icons.circle_outlined,
                                  color: subtask.isCompleted ? Colors.greenAccent : Colors.white54,
                                  size: 20
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        subtask.title, 
                                        style: TextStyle(
                                          color: Colors.white,
                                          decoration: subtask.isCompleted ? TextDecoration.lineThrough : null
                                        )
                                      ),
                                      if (subtask.startTime != null)
                                        Text(
                                          "${subtask.date} ${subtask.startTime}",
                                          style: const TextStyle(color: Colors.white30, fontSize: 10),
                                        )
                                    ],
                                  ),
                                ),
                                if (!subtask.isCompleted)
                                  IconButton(
                                    icon: const Icon(Icons.check, color: Colors.white),
                                    onPressed: () async {
                                      await _api.completeTask(subtask.id);
                                      _refreshSubtasks();
                                    },
                                  )
                              ],
                            ),
                          );
                        }
                      );
                    },
                  ),
                )
              ],
            ),
          ),
        ),
      ),
        );
      }
    
      Widget _buildAttributeBadge(String label, int value, Color color) {
        return Column(
          children: [
            Text(label, style: const TextStyle(color: Colors.white70, fontSize: 12)),
            const SizedBox(height: 4),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: color.withOpacity(0.2),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: color.withOpacity(0.5)),
              ),
              child: Row(
                children: [
                  Text("$value", style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                  const SizedBox(width: 4),
                  const Icon(Icons.star, size: 14, color: Colors.amber),
                ],
              ),
            ),
          ],
        );
      }
    }
    