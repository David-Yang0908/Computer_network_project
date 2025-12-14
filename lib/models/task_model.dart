class Task {
  final int id;
  final String? eventId;
  final String? parentId;
  final String title;
  final String description;
  final DateTime? deadline; // Keep for compatibility
  
  // Scheduling
  final String? date;
  final String? startTime;
  final String? endTime;
  final double estimatedHours;
  
  // Attributes
  final int priority;
  final int importance;
  final int difficulty;
  final bool isFixed;
  final String status;
  
  final int scoreValue;
  final bool isCompleted;

  Task({
    required this.id,
    this.eventId,
    this.parentId,
    required this.title,
    this.description = '',
    this.deadline,
    this.date,
    this.startTime,
    this.endTime,
    this.estimatedHours = 0.0,
    this.priority = 3,
    this.importance = 3,
    this.difficulty = 3,
    this.isFixed = false,
    this.status = 'pending',
    this.scoreValue = 0,
    this.isCompleted = false,
  });

  factory Task.fromJson(Map<String, dynamic> json) {
    DateTime? parsedDeadline;
    if (json['deadline'] != null) {
      parsedDeadline = DateTime.tryParse(json['deadline']);
    } else if (json['date'] != null && json['start_time'] != null) {
      // Fallback: construct deadline from date + start_time
      parsedDeadline = DateTime.tryParse("${json['date']} ${json['start_time']}");
    }

    return Task(
      id: json['id'] ?? 0,
      eventId: json['event_id'],
      parentId: json['parent_id'],
      title: json['title'] ?? '',
      description: json['description'] ?? '',
      deadline: parsedDeadline,
      date: json['date'],
      startTime: json['start_time'],
      endTime: json['end_time'],
      estimatedHours: (json['estimated_hours'] ?? 0).toDouble(),
      priority: json['priority'] ?? 3,
      importance: json['importance'] ?? 3,
      difficulty: json['difficulty'] ?? 3,
      isFixed: json['is_fixed'] ?? false,
      status: json['status'] ?? 'pending',
      scoreValue: json['score_value'] ?? 0,
      isCompleted: json['is_completed'] ?? false,
    );
  }
}

class UserStats {
  final int score;
  final int level;

  UserStats({required this.score, required this.level});

  factory UserStats.fromJson(Map<String, dynamic> json) {
    return UserStats(
      score: json['score'] ?? 0,
      level: json['level'] ?? 1,
    );
  }
}
