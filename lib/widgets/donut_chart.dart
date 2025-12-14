import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import 'glass_container.dart';
import '../services/api_service.dart';

class DonutChart extends StatelessWidget {
  final int score;
  final int level;

  const DonutChart({super.key, required this.score, required this.level});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        SizedBox(
          width: 200,
          height: 200,
          child: Stack(
            alignment: Alignment.center,
            children: [
              // Outer Glow/Ring
              Container(
                width: 180,
                height: 180,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: Colors.pinkAccent.withOpacity(0.4),
                      blurRadius: 40,
                      spreadRadius: 5,
                    )
                  ]
                ),
              ),
              // The Donut Image
              GlassContainer(
                borderRadius: 100,
                padding: const EdgeInsets.all(20),
                child: Image.network(
                  '${ApiService.baseUrl}/donut_image', // Load from our Backend
                  fit: BoxFit.contain,
                  // Add a unique key or cache busting if images change dynamically, 
                  // but for now standard caching is fine.
                  loadingBuilder: (context, child, loadingProgress) {
                    if (loadingProgress == null) return child;
                    return const Center(child: CircularProgressIndicator(color: Colors.pinkAccent));
                  },
                  errorBuilder: (context, error, stackTrace) {
                     // Fallback if image fails to load
                     return const Center(child: Text('🍩', style: TextStyle(fontSize: 80)));
                  },
                ),
              ),
              // Score Overlay
              Positioned(
                bottom: 0,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.black54,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    'Score: $score',
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 16,
                    ),
                  ),
                ),
              )
            ],
          ),
        ),
        const SizedBox(height: 10),
        Text(
          'Level $level',
          style: const TextStyle(
            color: AppTheme.textSecondary,
            fontSize: 18,
            letterSpacing: 1.2,
          ),
        )
      ],
    );
  }
}
