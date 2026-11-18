
import 'package:flutter/material.dart';
import 'main_navigation.dart';
import '../services/route_api_service.dart';
import '../services/risk_api_service.dart';

class LiveMapScreen extends StatefulWidget {
  const LiveMapScreen({super.key});

  @override
  State<LiveMapScreen> createState() => _LiveMapScreenState();
}

class _LiveMapScreenState extends State<LiveMapScreen> {
  @override
  void initState() {
    super.initState();
    _loadCurrentRisk();
  }

  Future<void> _loadCurrentRisk() async {
    try {
      final result = await RiskApiService.getCurrentLocationRisk();
      debugPrint('RISK API SUCCESS: $result');
    } catch (e) {
      debugPrint('RISK API ERROR: $e');
    }
  }

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
                    border: Border.all(
                      color: Colors.cyanAccent.withOpacity(0.5),
                    ),
                  ),
                  child: Column(
                    children: [
                      const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.navigation,
                            color: Colors.cyanAccent,
                            size: 20,
                          ),
                          SizedBox(width: 8),
                          Text(
                            "Shiradi Ghat Live Radar (NH 75)",
                            style: TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.bold,
                              fontSize: 14,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        "Coordinates: 12.8542Â° N, 75.6831Â° E",
                        style: TextStyle(
                          color: Colors.grey,
                          fontSize: 11,
                        ),
                      ),
                      const SizedBox(height: 12),
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: Colors.green.withOpacity(0.2),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: const Text(
                              "Clear Pass",
                              style: TextStyle(
                                color: Colors.greenAccent,
                                fontSize: 10,
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: Colors.orange.withOpacity(0.2),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: const Text(
                              "Hairpin Curve Monitored",
                              style: TextStyle(
                                color: Colors.orangeAccent,
                                fontSize: 10,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // Live location risk API display
          Positioned(
            top: 16,
            left: 16,
            right: 16,
            child: ValueListenableBuilder<Map<String, dynamic>?>(
              valueListenable: RiskApiService.latestRisk,
              builder: (context, risk, child) {
                if (risk == null) {
                  return const SizedBox.shrink();
                }

                final gaps = risk['risk_data_gaps'] as List? ?? [];
                final reasons = risk['reasons'] as List? ?? [];

                return Container(
                  constraints: const BoxConstraints(maxHeight: 190),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFF162032),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: Colors.orangeAccent),
                  ),
                  child: SingleChildScrollView(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Text(
                          'LIVE LOCATION RISK',
                          style: TextStyle(
                            color: Colors.orangeAccent,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          'Risk level: ${risk['risk_level'] ?? 'Not available'}',
                          style: const TextStyle(color: Colors.white),
                        ),
                        Text(
                          'Risk score: ${risk['risk_score'] ?? 'Not available'}',
                          style: const TextStyle(color: Colors.white),
                        ),
                        Text(
                          'Assessment: ${risk['risk_assessment'] ?? 'Unknown'}',
                          style: const TextStyle(color: Colors.white70),
                        ),
                        if (reasons.isNotEmpty) ...[
                          const SizedBox(height: 6),
                          const Text(
                            'Reasons:',
                            style: TextStyle(color: Colors.white),
                          ),
                          ...reasons.map(
                            (reason) => Text(
                              '• $reason',
                              style: const TextStyle(
                                color: Colors.white70,
                                fontSize: 12,
                              ),
                            ),
                          ),
                        ],
                        if (gaps.isNotEmpty) ...[
                          const SizedBox(height: 6),
                          const Text(
                            'Data gaps:',
                            style: TextStyle(color: Colors.orangeAccent),
                          ),
                          ...gaps.map(
                            (gap) => Text(
                              '• $gap',
                              style: const TextStyle(
                                color: Colors.white70,
                                fontSize: 12,
                              ),
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
          // API response display
          Positioned(
            bottom: 20,
            left: 16,
            right: 16,
            child: ValueListenableBuilder(
              valueListenable: RouteApiService.latestRoute,
              builder: (context, response, child) {
                if (response == null || response.routes.isEmpty) {
                  return const SizedBox.shrink();
                }

                final route = response.routes.first;

                return Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: const Color(0xFF162032),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: Colors.cyanAccent),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Text(
                        'API Route Information',
                        style: TextStyle(
                          color: Colors.cyanAccent,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Distance: ${(route.distanceM / 1000).toStringAsFixed(2)} km',
                        style: const TextStyle(color: Colors.white),
                      ),
                      Text(
                        'Risk: ${route.overallRiskLevel ?? "Not available"}',
                        style: const TextStyle(color: Colors.white),
                      ),
                      Text(
                        'Assessment: ${route.riskAssessment}',
                        style: const TextStyle(color: Colors.white70),
                      ),
                    ],
                  ),
                );
              },
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
      canvas.drawLine(
        Offset(x, 0),
        Offset(x, size.height),
        paint,
      );
    }

    for (double y = 0; y < size.height; y += gridSize) {
      canvas.drawLine(
        Offset(0, y),
        Offset(size.width, y),
        paint,
      );
    }

    final radarPaint = Paint()
      ..color = Colors.cyanAccent.withOpacity(0.15)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;

    canvas.drawCircle(
      Offset(size.width / 2, size.height / 2),
      120,
      radarPaint,
    );

    canvas.drawCircle(
      Offset(size.width / 2, size.height / 2),
      200,
      radarPaint,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}


