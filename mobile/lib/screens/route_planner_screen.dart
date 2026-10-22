import 'package:flutter/material.dart';
import 'main_navigation.dart';

class RoutePlannerScreen extends StatelessWidget {
  const RoutePlannerScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: const PharosAppBar(),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text("Route Planner", style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white)),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFF162032),
                borderRadius: BorderRadius.circular(16),
              ),
              child: const Column(
                children: [
                  ListTile(
                    leading: Icon(Icons.trip_origin, color: Colors.green),
                    title: Text("Bengaluru, Karnataka", style: TextStyle(color: Colors.white)),
                    subtitle: Text("From Source", style: TextStyle(color: Colors.grey, fontSize: 10)),
                  ),
                  Divider(color: Colors.white12),
                  ListTile(
                    leading: Icon(Icons.location_on, color: Colors.redAccent),
                    title: Text("Mangalore, Karnataka", style: TextStyle(color: Colors.white)),
                    subtitle: Text("To Destination", style: TextStyle(color: Colors.grey, fontSize: 10)),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}