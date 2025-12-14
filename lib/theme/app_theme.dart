import 'package:flutter/material.dart';

class AppTheme {
  static const Color bgStart = Color(0xFF6A11CB);
  static const Color bgEnd = Color(0xFF2575FC);
  
  static const Color glassSurface = Color.fromARGB(51, 255, 255, 255); // 0.2 opacity white
  static const Color text = Colors.white;
  static const Color textSecondary = Color.fromARGB(179, 255, 255, 255); // 0.7 opacity
  static const Color borderLight = Color.fromARGB(128, 255, 255, 255); // 0.5 opacity
  
  static const List<BoxShadow> glassShadow = [
    BoxShadow(
      color: Color.fromRGBO(31, 38, 135, 0.37),
      offset: Offset(0, 8),
      blurRadius: 32,
    )
  ];

  static BoxDecoration mainBackground = const BoxDecoration(
    gradient: LinearGradient(
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
      colors: [bgStart, bgEnd],
    ),
  );
}
