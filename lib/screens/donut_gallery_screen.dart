import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../theme/app_theme.dart';
import '../widgets/glass_container.dart';
import '../services/api_service.dart';

class DonutGalleryScreen extends StatelessWidget {
  const DonutGalleryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final ApiService api = ApiService();

    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: const Text("My Donut Collection", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.white),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: Container(
        decoration: AppTheme.mainBackground,
        child: SafeArea(
          child: FutureBuilder<List<String>>(
            future: api.fetchDonutGallery(),
            builder: (context, snapshot) {
              if (snapshot.connectionState == ConnectionState.waiting) {
                return const Center(child: CircularProgressIndicator(color: Colors.white));
              }
              if (snapshot.hasError) {
                return Center(child: Text("Error: ${snapshot.error}", style: const TextStyle(color: Colors.white)));
              }
              
              final images = snapshot.data ?? [];
              if (images.isEmpty) {
                return const Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.cookie_outlined, size: 80, color: Colors.white24),
                      SizedBox(height: 16),
                      Text("No donuts yet.\nComplete tasks to earn them!", textAlign: TextAlign.center, style: TextStyle(color: Colors.white54, fontSize: 16)),
                    ],
                  ),
                );
              }

              return GridView.builder(
                padding: const EdgeInsets.all(16),
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,
                  crossAxisSpacing: 16,
                  mainAxisSpacing: 16,
                  childAspectRatio: 0.85,
                ),
                itemCount: images.length,
                itemBuilder: (context, index) {
                  final imageName = images[index];
                  final imageUrl = '${ApiService.baseUrl}/donuts/gallery/$imageName';
                  
                  return GestureDetector(
                    onTap: () {
                      showDialog(
                        context: context, 
                        barrierColor: Colors.black87,
                        builder: (_) => Stack(
                          alignment: Alignment.center,
                          children: [
                            // 1. Rotating Light Beams Background
                            Transform.translate(
                              offset: const Offset(0, 50), // Move down
                              child: SizedBox(
                                width: 500, height: 500,
                                child: Stack(
                                  alignment: Alignment.center,
                                  children: List.generate(8, (i) => Transform.rotate(
                                    angle: i * 0.785, // 45 degrees in radians
                                    child: Container(
                                      width: 2, height: 600,
                                      decoration: BoxDecoration(
                                        gradient: LinearGradient(
                                          colors: [Colors.transparent, Colors.white10, Colors.transparent],
                                          begin: Alignment.topCenter, end: Alignment.bottomCenter
                                        )
                                      ),
                                    ),
                                  )),
                                ),
                              ).animate(onPlay: (c) => c.repeat()).rotate(duration: 10.seconds),
                            ),

                            // 2. Main Dialog Content
                            Dialog(
                              backgroundColor: Colors.transparent,
                              insetPadding: const EdgeInsets.all(20),
                              child: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  const Text("✨ COLLECTED! ✨", 
                                    style: TextStyle(
                                      color: Colors.amber, 
                                      fontWeight: FontWeight.bold, 
                                      fontSize: 28, 
                                      letterSpacing: 2,
                                      shadows: [Shadow(color: Colors.amberAccent, blurRadius: 10)]
                                    )
                                  ).animate().fadeIn().scale(delay: 200.ms, curve: Curves.elasticOut),
                                  
                                  const SizedBox(height: 40),
                                  
                                  // Image with Animation
                                  Stack(
                                    alignment: Alignment.center,
                                    children: [
                                      // The Donut
                                      Image.network(imageUrl, height: 250, fit: BoxFit.contain)
                                        .animate()
                                        .scale(duration: 800.ms, curve: Curves.elasticOut)
                                        .then(delay: 200.ms)
                                        .shimmer(duration: 1200.ms, color: Colors.white54)
                                        .then(delay: 500.ms)
                                        .shake(hz: 2, curve: Curves.easeInOut) // Gentle hover feel
                                    ]
                                  ),
                                  
                                  const SizedBox(height: 30),
                                  
                                  GlassContainer(
                                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
                                    borderRadius: 20,
                                    child: Text(
                                      "Donut #${index + 1}", 
                                      style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold)
                                    ),
                                  ).animate().fadeIn(delay: 500.ms).moveY(begin: 20, end: 0),
                                  
                                  const SizedBox(height: 40),
                                  
                                  // Close Button
                                  IconButton(
                                    onPressed: () => Navigator.pop(context),
                                    icon: const Icon(Icons.close_rounded, color: Colors.white70, size: 40),
                                    style: IconButton.styleFrom(
                                      backgroundColor: Colors.white10,
                                      padding: const EdgeInsets.all(12)
                                    ),
                                  )
                                ],
                              ),
                            ),
                          ],
                        )
                      );
                    },
                    child: GlassContainer(
                      padding: const EdgeInsets.all(12),
                      child: Column(
                        children: [
                          Expanded(
                            child: Hero(
                              tag: imageName,
                              child: Image.network(
                                imageUrl,
                                fit: BoxFit.contain,
                                loadingBuilder: (context, child, loadingProgress) {
                                  if (loadingProgress == null) return child;
                                  return const Center(child: CircularProgressIndicator(color: Colors.pinkAccent));
                                },
                              ),
                            ),
                          ),
                          const SizedBox(height: 12),
                          Text(
                            "Donut #${index + 1}",
                            style: const TextStyle(color: Colors.white70, fontSize: 14, fontWeight: FontWeight.bold),
                          ),
                        ],
                      ),
                    ).animate().scale(duration: 400.ms, delay: (index * 100).ms, curve: Curves.easeOutBack),
                  );
                },
              );
            },
          ),
        ),
      ),
    );
  }
}
