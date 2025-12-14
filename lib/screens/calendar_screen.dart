import 'package:flutter/material.dart';
import 'package:table_calendar/table_calendar.dart';
import '../theme/app_theme.dart';
import '../widgets/glass_container.dart';
import '../services/api_service.dart';
import '../models/task_model.dart';
import 'task_detail_screen.dart';

class CalendarScreen extends StatefulWidget {
  const CalendarScreen({super.key});

  @override
  State<CalendarScreen> createState() => _CalendarScreenState();
}

class _CalendarScreenState extends State<CalendarScreen> {
  CalendarFormat _calendarFormat = CalendarFormat.month;
  DateTime _focusedDay = DateTime.now();
  DateTime? _selectedDay;
  Map<DateTime, List<Task>> _events = {}; // Store Task objects
  final ApiService _api = ApiService();

  @override
  void initState() {
    super.initState();
    _selectedDay = _focusedDay;
    _loadEvents();
  }

  void _loadEvents() async {
    try {
      final eventsList = await _api.fetchCalendarEvents();
      final Map<DateTime, List<Task>> mappedEvents = {};
      
      for (var eventJson in eventsList) {
        final task = Task.fromJson(eventJson);
        // Use task.date if available, otherwise parse from json raw string if needed
        // Since API returns 'date' field formatted as YYYY-MM-DD
        final dateParts = (eventJson['date'] as String).split('-');
        final dateKey = DateTime(
          int.parse(dateParts[0]), 
          int.parse(dateParts[1]), 
          int.parse(dateParts[2])
        );
        
        if (mappedEvents[dateKey] == null) mappedEvents[dateKey] = [];
        mappedEvents[dateKey]!.add(task);
      }
      
      if (mounted) {
        setState(() {
          _events = mappedEvents;
        });
      }
    } catch (e) {
      print("Error loading calendar events: $e");
    }
  }

  List<Task> _getEventsForDay(DateTime day) {
    final dateKey = DateTime(day.year, day.month, day.day);
    return _events[dateKey] ?? [];
  }

  @override
  Widget build(BuildContext context) {
    return Container(
       decoration: AppTheme.mainBackground,
       child: SafeArea(
         child: Column(
           children: [
             GlassContainer(
               margin: const EdgeInsets.all(16),
               padding: const EdgeInsets.only(bottom: 10),
               child: TableCalendar(
                 firstDay: DateTime.utc(2024, 1, 1),
                 lastDay: DateTime.utc(2030, 12, 31),
                 focusedDay: _focusedDay,
                 calendarFormat: _calendarFormat,
                 selectedDayPredicate: (day) => isSameDay(_selectedDay, day),
                 onDaySelected: (selectedDay, focusedDay) {
                   setState(() {
                     _selectedDay = selectedDay;
                     _focusedDay = focusedDay;
                   });
                 },
                 onFormatChanged: (format) {
                   if (_calendarFormat != format) {
                     setState(() => _calendarFormat = format);
                   }
                 },
                 onPageChanged: (focusedDay) {
                   _focusedDay = focusedDay;
                 },
                 eventLoader: _getEventsForDay,
                 calendarStyle: const CalendarStyle(
                   defaultTextStyle: TextStyle(color: Colors.white),
                   weekendTextStyle: TextStyle(color: Colors.white70),
                   outsideTextStyle: TextStyle(color: Colors.white30),
                   todayDecoration: BoxDecoration(color: Colors.blueAccent, shape: BoxShape.circle),
                   selectedDecoration: BoxDecoration(color: Colors.pinkAccent, shape: BoxShape.circle),
                   markerDecoration: BoxDecoration(color: Colors.amber, shape: BoxShape.circle),
                 ),
                 headerStyle: const HeaderStyle(
                   titleTextStyle: TextStyle(color: Colors.white, fontSize: 18),
                   formatButtonTextStyle: TextStyle(color: Colors.white),
                   leftChevronIcon: Icon(Icons.chevron_left, color: Colors.white),
                   rightChevronIcon: Icon(Icons.chevron_right, color: Colors.white),
                 ),
               ),
             ),
             Expanded(
               child: ListView(
                 padding: const EdgeInsets.symmetric(horizontal: 16),
                 children: [
                   if (_selectedDay != null) ...[
                     Text(
                       "Tasks for ${_selectedDay!.month}/${_selectedDay!.day}",
                       style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                     ),
                     const SizedBox(height: 10),
                     ..._getEventsForDay(_selectedDay!).map((task) => 
                       GestureDetector(
                         onTap: () {
                           Navigator.push(
                             context,
                             MaterialPageRoute(builder: (context) => TaskDetailScreen(task: task)),
                           ).then((_) => _loadEvents()); // Refresh on return
                         },
                         child: GlassContainer(
                           margin: const EdgeInsets.only(bottom: 8),
                           padding: const EdgeInsets.all(16),
                           child: Row(
                             children: [
                               Expanded(
                                 child: Column(
                                   crossAxisAlignment: CrossAxisAlignment.start,
                                   children: [
                                     Text(
                                       task.title, 
                                       style: TextStyle(
                                         color: Colors.white,
                                         decoration: task.isCompleted ? TextDecoration.lineThrough : null
                                       )
                                     ),
                                     if (task.startTime != null)
                                       Text(task.startTime!, style: const TextStyle(color: Colors.white54, fontSize: 12)),
                                   ],
                                 ),
                               ),
                               // Actions Row
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
                                         _loadEvents(); // Refresh calendar
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
                                     icon: Icon(
                                       task.isCompleted ? Icons.check_circle : Icons.circle_outlined,
                                       color: task.isCompleted ? Colors.greenAccent : Colors.white54,
                                     ),
                                     onPressed: () async {
                                       await _api.completeTask(task.id);
                                       _loadEvents(); // Refresh calendar
                                     },
                                   ),
                                 ],
                               )
                             ],
                           ),
                         ),
                       )
                     )
                   ]
                 ],
               ),
             )
           ],
         ),
       ),
    );
  }
}
