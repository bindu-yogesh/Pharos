import 'package:flutter/material.dart';
import 'screens/main_navigation.dart';

void main() {
  runApp(const PharosApp());
}

class PharosApp extends StatelessWidget {
  const PharosApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Pharos',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF0F172A),
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.cyanAccent,
          brightness: Brightness.dark,
        ),
      ),
      home: const MainNavigation(),
    );
  }
}