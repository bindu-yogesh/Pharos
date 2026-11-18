import 'package:flutter/material.dart';
import 'main_navigation.dart';

class ReportHazardScreen extends StatelessWidget {
  const ReportHazardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: const PharosAppBar(),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text("Report Road Hazard", style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white)),
            const SizedBox(height: 16),
            TextField(
              maxLines: 4,
              decoration: InputDecoration(
                hintText: "Describe hazard (e.g., fallen tree near km marker...)",
                hintStyle: const TextStyle(color: Colors.grey),
                filled: true,
                fillColor: const Color(0xFF162032),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
              ),
            ),
          ],
        ),
      ),
    );
  }
}