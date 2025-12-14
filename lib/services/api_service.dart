import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/task_model.dart';

class ApiService {
  // Use computer's IP for physical device connection
  static const String baseUrl = 'http://192.168.0.102:5000/api'; 

  Future<void> addTask(Map<String, dynamic> taskData) async {
    final response = await http.post(
      Uri.parse('$baseUrl/add_task'), // Make sure this matches backend route
      headers: {'Content-Type': 'application/json'},
      body: json.encode(taskData),
    );
    if (response.statusCode != 200) {
      throw Exception('Failed to add task: ${response.body}');
    }
  }

  Future<UserStats> fetchUser() async {
    final response = await http.get(Uri.parse('$baseUrl/user'));
    if (response.statusCode == 200) {
      return UserStats.fromJson(json.decode(response.body));
    }
    throw Exception('Failed to load user stats');
  }

  Future<List<Task>> fetchTasks() async {
    final response = await http.get(Uri.parse('$baseUrl/tasks'));
    if (response.statusCode == 200) {
      List<dynamic> body = json.decode(response.body);
      return body.map((dynamic item) => Task.fromJson(item)).toList();
    }
    throw Exception('Failed to load tasks');
  }

  Future<Map<String, dynamic>> analyzeText(String text) async {
    final response = await http.post(
      Uri.parse('$baseUrl/analyze'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({'text': text}),
    );
    if (response.statusCode == 200) {
      return json.decode(response.body);
    }
    throw Exception('Failed to analyze text');
  }

  Future<void> confirmTasks(List<dynamic> tasks) async {
    await http.post(
      Uri.parse('$baseUrl/tasks/confirm'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({'tasks': tasks}),
    );
  }

  Future<List<dynamic>> fetchCalendarEvents() async {
    final response = await http.get(Uri.parse('$baseUrl/tasks/calendar'));
    if (response.statusCode == 200) {
      return json.decode(response.body);
    }
    throw Exception('Failed to load calendar events');
  }

  Future<List<dynamic>> fetchWeeklyStats() async {
    final response = await http.get(Uri.parse('$baseUrl/stats/weekly'));
    if (response.statusCode == 200) {
      return json.decode(response.body);
    }
    throw Exception('Failed to load stats');
  }

  Future<List<dynamic>> fetchRewards() async {
    final response = await http.get(Uri.parse('$baseUrl/rewards'));
    if (response.statusCode == 200) {
      return json.decode(response.body);
    }
    throw Exception('Failed to load rewards');
  }

  Future<void> addReward(String title, int cost, String icon) async {
    await http.post(
      Uri.parse('$baseUrl/rewards'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({'title': title, 'cost': cost, 'icon': icon}),
    );
  }

  Future<int> redeemReward(int rewardId) async {
    final response = await http.post(Uri.parse('$baseUrl/rewards/$rewardId/redeem'));
    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      return data['new_score'];
    } else if (response.statusCode == 400) {
      throw Exception('Not enough points');
    }
    throw Exception('Failed to redeem reward');
  }

  Future<int> completeTask(int taskId) async {
    final response = await http.post(
      Uri.parse('$baseUrl/tasks/$taskId/complete'),
    );
    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      return data['new_score'];
    }
    throw Exception('Failed to complete task');
  }

  Future<List<Task>> fetchSubtasks(String eventId) async {
    final response = await http.get(Uri.parse('$baseUrl/tasks/$eventId/subtasks'));
    if (response.statusCode == 200) {
      List<dynamic> body = json.decode(response.body);
      return body.map((dynamic item) => Task.fromJson(item)).toList();
    }
    throw Exception('Failed to load subtasks');
  }

  Future<List<dynamic>> fetchTaskHistory() async {
    final response = await http.get(Uri.parse('$baseUrl/tasks/history'));
    if (response.statusCode == 200) {
      return json.decode(response.body);
    }
    throw Exception('Failed to load task history');
  }

  Future<void> runAiDecomposition() async {
    final response = await http.get(Uri.parse('$baseUrl/run_ai_decompose'));
    if (response.statusCode != 200) {
      throw Exception('Failed to run AI decomposition');
    }
  }

  Future<void> deleteEvent(String eventId) async {
    final response = await http.post(
      Uri.parse('$baseUrl/delete_event'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({'event_id': eventId}),
    );
    if (response.statusCode != 200) {
      throw Exception('Failed to delete event');
    }
  }
}
