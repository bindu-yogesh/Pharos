import 'package:flutter/material.dart';
import 'main_navigation.dart';

class SafePlacesScreen extends StatelessWidget {
  const SafePlacesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: const PharosAppBar(),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: const [
          Text("Verified Safe Locations", style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white)),
          SizedBox(height: 12),
          Card(
            color: Color(0xFF162032),
            child: ListTile(
              leading: Icon(Icons.local_hospital, color: Colors.cyanAccent),
              title: Text("Sakleshpur Government Hospital", style: TextStyle(color: Colors.white)),
              subtitle: Text("12 km away • Open 24/7", style: TextStyle(color: Colors.grey)),
            ),
          ),
        ],
      ),
    );
  }
}