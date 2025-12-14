import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'glass_container.dart';
import '../services/api_service.dart';

class AddTaskDialog extends StatefulWidget {
  const AddTaskDialog({super.key});

  @override
  State<AddTaskDialog> createState() => _AddTaskDialogState();
}

class _AddTaskDialogState extends State<AddTaskDialog> {
  final _formKey = GlobalKey<FormState>();
  final TextEditingController _titleController = TextEditingController();
  final ApiService _api = ApiService();

  DateTime _selectedDate = DateTime.now();
  TimeOfDay _startTime = const TimeOfDay(hour: 9, minute: 0);
  TimeOfDay _endTime = const TimeOfDay(hour: 10, minute: 0);
  
  bool _isFixed = false;
  double _estimatedHours = 1.0;
  
  int _priority = 3;
  int _importance = 3;
  int _difficulty = 3;
  
  bool _isSubmitting = false;

  Future<void> _selectDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _selectedDate,
      firstDate: DateTime.now(),
      lastDate: DateTime(2030),
    );
    if (picked != null) setState(() => _selectedDate = picked);
  }

  Future<void> _selectTime(bool isStart) async {
    final picked = await showTimePicker(
      context: context,
      initialTime: isStart ? _startTime : _endTime,
    );
    if (picked != null) {
      setState(() {
        if (isStart) _startTime = picked;
        else _endTime = picked;
      });
    }
  }

  Widget _buildRatingSelector(String label, int value, Function(int) onChanged) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(color: Colors.white70, fontSize: 12)),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: List.generate(5, (index) {
            final int rating = index + 1;
            final bool isSelected = rating <= value;
            return GestureDetector(
              onTap: () => onChanged(rating),
              child: Icon(
                Icons.star,
                color: isSelected ? Colors.amber : Colors.white24,
                size: 24,
              ),
            );
          }),
        )
      ],
    );
  }

  void _submit() async {
    if (!_formKey.currentState!.validate()) return;
    
    setState(() => _isSubmitting = true);
    
    final String dateStr = DateFormat('yyyy-MM-dd').format(_selectedDate);
    final String startStr = "${_startTime.hour.toString().padLeft(2,'0')}:${_startTime.minute.toString().padLeft(2,'0')}";
    final String endStr = "${_endTime.hour.toString().padLeft(2,'0')}:${_endTime.minute.toString().padLeft(2,'0')}";
    
    final Map<String, dynamic> taskData = {
      // Google Calendar ID only allows a-v and 0-9. No underscores.
      "event_id": "task${DateTime.now().millisecondsSinceEpoch}", 
      "parent_id": null,
      "name": _titleController.text,
      "date": dateStr,
      "start_time": _isFixed ? startStr : null,
      "end_time": _isFixed ? endStr : null,
      "estimated_hours": _isFixed ? 0.0 : _estimatedHours,
      "priority": _priority,
      "importance": _importance,
      "difficulty": _difficulty,
      "is_fixed": _isFixed,
      "status": "pending"
    };

    try {
      await _api.addTask(taskData);
      if (mounted) {
        Navigator.pop(context, true); // Return true to indicate success
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Error: $e")));
      }
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: Colors.transparent,
      insetPadding: const EdgeInsets.all(16),
      child: GlassContainer(
        padding: const EdgeInsets.all(20),
        child: SingleChildScrollView(
          child: Form(
            key: _formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text("Add New Task", style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold)),
                const SizedBox(height: 20),
                
                // Name
                TextFormField(
                  controller: _titleController,
                  style: const TextStyle(color: Colors.white),
                  decoration: const InputDecoration(
                    labelText: "Task Name",
                    labelStyle: TextStyle(color: Colors.white70),
                    enabledBorder: UnderlineInputBorder(borderSide: BorderSide(color: Colors.white24)),
                  ),
                  validator: (v) => v!.isEmpty ? "Required" : null,
                ),
                const SizedBox(height: 20),
                
                // Date
                Row(
                  children: [
                    const Icon(Icons.calendar_today, color: Colors.white70, size: 20),
                    const SizedBox(width: 10),
                    TextButton(
                      onPressed: _selectDate,
                      child: Text(DateFormat('yyyy-MM-dd').format(_selectedDate), style: const TextStyle(color: Colors.white, fontSize: 16)),
                    )
                  ],
                ),
                const Divider(color: Colors.white24),
                
                // Fixed Time Switch
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text("Fixed Schedule?", style: TextStyle(color: Colors.white, fontSize: 16)),
                    Switch(
                      value: _isFixed,
                      activeColor: Colors.pinkAccent,
                      onChanged: (val) => setState(() => _isFixed = val),
                    ),
                  ],
                ),
                
                if (_isFixed) ...[
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      _buildTimeBtn("Start", _startTime, () => _selectTime(true)),
                      const Icon(Icons.arrow_forward, color: Colors.white54),
                      _buildTimeBtn("End", _endTime, () => _selectTime(false)),
                    ],
                  )
                ] else ...[
                  const Text("Estimated Hours", style: TextStyle(color: Colors.white70)),
                  Slider(
                    value: _estimatedHours,
                    min: 0.5,
                    max: 8.0,
                    divisions: 15,
                    activeColor: Colors.blueAccent,
                    label: "${_estimatedHours}h",
                    onChanged: (val) => setState(() => _estimatedHours = val),
                  ),
                  Center(child: Text("${_estimatedHours} hours", style: const TextStyle(color: Colors.white)))
                ],
                
                const SizedBox(height: 20),
                Row(
                  children: [
                    Expanded(child: _buildRatingSelector("Priority", _priority, (v) => setState(() => _priority = v))),
                    const SizedBox(width: 10),
                    Expanded(child: _buildRatingSelector("Importance", _importance, (v) => setState(() => _importance = v))),
                  ],
                ),
                const SizedBox(height: 10),
                _buildRatingSelector("Difficulty", _difficulty, (v) => setState(() => _difficulty = v)),
                
                const SizedBox(height: 30),
                
                // Actions
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    TextButton(
                      onPressed: () => Navigator.pop(context),
                      child: const Text("Cancel", style: TextStyle(color: Colors.white70)),
                    ),
                    const SizedBox(width: 10),
                    ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.pinkAccent,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                      ),
                      onPressed: _isSubmitting ? null : _submit,
                      child: _isSubmitting 
                        ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                        : const Text("Add Task", style: TextStyle(color: Colors.white)),
                    )
                  ],
                )
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildTimeBtn(String label, TimeOfDay time, VoidCallback onTap) {
    return Column(
      children: [
        Text(label, style: const TextStyle(color: Colors.white54, fontSize: 10)),
        TextButton(
          onPressed: onTap,
          child: Text("${time.hour.toString().padLeft(2,'0')}:${time.minute.toString().padLeft(2,'0')}", 
            style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
        )
      ],
    );
  }
}
