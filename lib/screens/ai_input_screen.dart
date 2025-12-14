import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../widgets/glass_container.dart';
import '../services/api_service.dart';

class AiInputScreen extends StatefulWidget {
  const AiInputScreen({super.key});

  @override
  State<AiInputScreen> createState() => _AiInputScreenState();
}

class _AiInputScreenState extends State<AiInputScreen> {
  final TextEditingController _controller = TextEditingController();
  final ApiService _api = ApiService();
  final List<Map<String, dynamic>> _messages = []; // {type: 'user'|'ai', content: String|List}
  bool _isLoading = false;

  void _sendMessage() async {
    final text = _controller.text.trim();
    if (text.isEmpty) return;

    setState(() {
      _messages.add({'type': 'user', 'content': text});
      _isLoading = true;
      _controller.clear();
    });

    try {
      final result = await _api.analyzeText(text);
      // result = {message: "...", suggestions: [...]}
      setState(() {
        _messages.add({
          'type': 'ai',
          'content': result['message'] ?? 'I have analyzed your request.',
          'suggestions': result['suggestions']
        });
      });
    } catch (e) {
      setState(() {
        _messages.add({'type': 'ai', 'content': 'Error analyzing text: $e'});
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  void _confirmTasks(List<dynamic> tasks) async {
    try {
      await _api.confirmTasks(tasks);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Plan saved to your schedule!')),
        );
        Navigator.pop(context);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error saving: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: const Text("AI Planner", style: TextStyle(color: Colors.white)),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.white),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: Container(
        decoration: AppTheme.mainBackground,
        child: Column(
          children: [
            Expanded(
              child: ListView.builder(
                padding: const EdgeInsets.fromLTRB(16, 100, 16, 20),
                itemCount: _messages.length,
                itemBuilder: (context, index) {
                  final msg = _messages[index];
                  final isUser = msg['type'] == 'user';
                  
                  if (isUser) {
                    return Align(
                      alignment: Alignment.centerRight,
                      child: Container(
                        margin: const EdgeInsets.symmetric(vertical: 8),
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.blueAccent.withOpacity(0.8),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text(msg['content'], style: const TextStyle(color: Colors.white)),
                      ),
                    );
                  } else {
                    // AI Response
                    final suggestions = msg['suggestions'] as List<dynamic>?;
                    final message = msg['content'] as String?;
                    final bool isAutoCreated = message != null && message.contains('successfully');
                    
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (message != null)
                          GlassContainer(
                            margin: const EdgeInsets.symmetric(vertical: 8),
                            padding: const EdgeInsets.all(12),
                            child: Text(
                              message,
                              style: const TextStyle(color: Colors.white),
                            ),
                          ),
                        if (suggestions != null)
                          Container(
                            margin: const EdgeInsets.only(left: 10),
                            child: Column(
                              children: [
                                ...suggestions.map((task) => Container(
                                  margin: const EdgeInsets.only(bottom: 8),
                                  child: GlassContainer(
                                    padding: const EdgeInsets.all(12),
                                    child: ListTile(
                                      contentPadding: EdgeInsets.zero,
                                      leading: isAutoCreated 
                                        ? const Icon(Icons.check_circle, color: Colors.greenAccent) 
                                        : const Icon(Icons.lightbulb_outline, color: Colors.amber),
                                      title: Text(task['name'] ?? task['title'] ?? 'Untitled', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                                      subtitle: Text(
                                        "${(task['priority'] ?? 3) + (task['difficulty'] ?? 3) * 5} pts • ${task['estimated_hours'] ?? 1.0} hr", 
                                        style: const TextStyle(color: Colors.white70)
                                      ),
                                      trailing: const Icon(Icons.schedule, color: Colors.white54),
                                    ),
                                  ),
                                )),
                                if (!isAutoCreated && suggestions.isNotEmpty)
                                  ElevatedButton(
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: Colors.pinkAccent,
                                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                                    ),
                                    onPressed: () => _confirmTasks(suggestions),
                                    child: const Text("Confirm & Add to Schedule", style: TextStyle(color: Colors.white)),
                                  )
                              ],
                            ),
                          )
                      ],
                    );
                  }
                },
              ),
            ),
            
            // Input Area
            GlassContainer(
              margin: const EdgeInsets.all(16),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              borderRadius: 30,
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      style: const TextStyle(color: Colors.white),
                      decoration: const InputDecoration(
                        hintText: "Tell me what you need to do...",
                        hintStyle: TextStyle(color: Colors.white54),
                        border: InputBorder.none,
                      ),
                    ),
                  ),
                  _isLoading 
                    ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : IconButton(
                        icon: const Icon(Icons.send, color: Colors.white),
                        onPressed: _sendMessage,
                      )
                ],
              ),
            )
          ],
        ),
      ),
    );
  }
}
