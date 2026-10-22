import 'package:flutter/material.dart';
import 'main_navigation.dart';

class LiveMapScreen extends StatelessWidget {
  const LiveMapScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: const PharosAppBar(),
      body: Stack(
        children: [
          Container(
            color: const Color(0xFF0B1120),
            child: CustomPaint(
              size: MediaQuery.of(context).size,
              painter: MapGridPainter(),
            ),
          ),
          Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFF162032).withOpacity(0.9),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: Colors.cyanAccent.withOpacity(0.5)),
                  ),
                  child: Column(
                    children: [
                      const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.navigation, color: Colors.cyanAccent, size: 20),
                          SizedBox(width: 8),
                          Text("Shiradi Ghat Live Radar (NH 75)", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
                        ],
                      ),
                      const SizedBox(height: 8),
                      const Text("Coordinates: 12.8542° N, 75.6831° E", style: TextStyle(color: Colors.grey, fontSize: 11)),
                      const SizedBox(height: 12),
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                            decoration: BoxDecoration(color: Colors.green.withOpacity(0.2), borderRadius: BorderRadius.circular(8)),
                            child: const Text("Clear Pass", style: TextStyle(color: Colors.greenAccent, fontSize: 10)),
                          ),
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                            decoration: BoxDecoration(color: Colors.orange.withOpacity(0.2), borderRadius: BorderRadius.circular(8)),
                            child: const Text("Hairpin Curve Monitored", style: TextStyle(color: Colors.orangeAccent, fontSize: 10)),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class MapGridPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.white.withOpacity(0.04)
      ..strokeWidth = 1;

    const gridSize = 40.0;
    for (double x = 0; x < size.width; x += gridSize) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), paint);
    }
    for (double y = 0; y < size.height; y += gridSize) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), paint);
    }

    final radarPaint = Paint()
      ..color = Colors.cyanAccent.withOpacity(0.15)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;

    canvas.drawCircle(Offset(size.width / 2, size.height / 2), 120, radarPaint);
    canvas.drawCircle(Offset(size.width / 2, size.height / 2), 200, radarPaint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}