import 'package:flutter/material.dart';
import 'dart:math' as math;
import 'main_navigation.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  void _showDetailModal(BuildContext context, String title, String detail, IconData icon, Color color) {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF162032),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        return Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 56, color: color),
              const SizedBox(height: 16),
              Text(title, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Colors.white)),
              const SizedBox(height: 12),
              Text(detail, textAlign: TextAlign.center, style: const TextStyle(color: Colors.grey, fontSize: 15)),
              const SizedBox(height: 24),
              ElevatedButton(
                style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF0055FF)),
                onPressed: () => Navigator.pop(context),
                child: const Text("Close", style: TextStyle(color: Colors.white)),
              ),
            ],
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: const PharosAppBar(),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            Container(
              padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 12),
              decoration: BoxDecoration(
                color: const Color(0xFF162032),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.white10),
              ),
              child: Column(
                children: [
                  SizedBox(
                    height: 100,
                    width: 190,
                    child: CustomPaint(
                      painter: GaugePainter(score: 32),
                      child: const Column(
                        mainAxisAlignment: MainAxisAlignment.end,
                        children: [
                          Text("RISK SCORE", style: TextStyle(color: Colors.grey, fontSize: 9, letterSpacing: 1.2)),
                          SizedBox(height: 2),
                          Text("32", style: TextStyle(color: Colors.white, fontSize: 26, fontWeight: FontWeight.bold)),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.green.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: Colors.green.withOpacity(0.4)),
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.check_circle, color: Colors.greenAccent, size: 14),
                        SizedBox(width: 4),
                        Text("LOW RISK", style: TextStyle(color: Colors.greenAccent, fontWeight: FontWeight.bold, fontSize: 11)),
                      ],
                    ),
                  ),
                  const SizedBox(height: 4),
                  const Text("Road conditions are currently safe", style: TextStyle(color: Colors.grey, fontSize: 11)),
                ],
              ),
            ),
            const SizedBox(height: 16),
            GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisSpacing: 14,
              mainAxisSpacing: 14,
              childAspectRatio: 1.2,
              children: [
                _buildGridCard(
                  context,
                  title: "Accidents",
                  value: "2 Today",
                  color: Colors.orange,
                  icon: Icons.warning_amber_rounded,
                  detail: "2 reported minor incidents near hair-pin curves. Road is currently cleared.",
                ),
                _buildGridCard(
                  context,
                  title: "Weather",
                  value: "Light Rain",
                  color: Colors.blue,
                  icon: Icons.cloud_outlined,
                  detail: "Intermittent light drizzle. Visibility is approximately 800m.",
                ),
                _buildGridCard(
                  context,
                  title: "Traffic",
                  value: "Moderate",
                  color: Colors.amber,
                  icon: Icons.traffic_outlined,
                  detail: "Normal heavy-vehicle movement. Average corridor speed is 45 km/h.",
                ),
                _buildGridCard(
                  context,
                  title: "Condition",
                  value: "Good",
                  color: Colors.green,
                  icon: Icons.check_circle_outline,
                  detail: "No major roadblocks or landslides detected along the primary route.",
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildGridCard(BuildContext context, {required String title, required String value, required Color color, required IconData icon, required String detail}) {
    return InkWell(
      onTap: () => _showDetailModal(context, title, detail, icon, color),
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [const Color(0xFF1E293B), color.withOpacity(0.12)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: color.withOpacity(0.4), width: 1.2),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(title, style: const TextStyle(color: Colors.white70, fontSize: 13, fontWeight: FontWeight.w600)),
            Center(
              child: Icon(icon, color: color, size: 42),
            ),
            Text(
              value,
              style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 15),
            ),
          ],
        ),
      ),
    );
  }
}

class GaugePainter extends CustomPainter {
  final int score;
  GaugePainter({required this.score});

  @override
  void paint(Canvas canvas, Size size) {
    final Paint backgroundPaint = Paint()
      ..color = Colors.white12
      ..style = PaintingStyle.stroke
      ..strokeWidth = 12
      ..strokeCap = StrokeCap.round;

    final Paint arcPaint = Paint()
      ..shader = const SweepGradient(
        colors: [Colors.green, Colors.yellow, Colors.orange, Colors.red],
        stops: [0.0, 0.35, 0.7, 1.0],
      ).createShader(Rect.fromLTWH(0, 0, size.width, size.height))
      ..style = PaintingStyle.stroke
      ..strokeWidth = 12
      ..strokeCap = StrokeCap.round;

    final center = Offset(size.width / 2, size.height);
    final radius = size.width / 2 - 10;

    canvas.drawArc(Rect.fromCircle(center: center, radius: radius), math.pi, math.pi, false, backgroundPaint);
    double sweepAngle = math.pi * (score / 100);
    canvas.drawArc(Rect.fromCircle(center: center, radius: radius), math.pi, sweepAngle, false, arcPaint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}