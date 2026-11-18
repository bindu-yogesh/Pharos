
import 'package:flutter/material.dart';
import 'main_navigation.dart';
import '../services/route_api_service.dart';

class RoutePlannerScreen extends StatefulWidget {
  const RoutePlannerScreen({super.key});

  @override
  State<RoutePlannerScreen> createState() => _RoutePlannerScreenState();
}

class _RoutePlannerScreenState extends State<RoutePlannerScreen> {
  @override
  void initState() {
    super.initState();
    _testRouteApi();
  }

  Future<void> _testRouteApi() async {
    try {
      final result = await RouteApiService.calculateRoute(
        originLatitude: 12.879189,
originLongitude: 75.721304,
destinationLatitude: 12.831463,
destinationLongitude: 75.542298,
      );

      debugPrint(
        'ROUTE API SUCCESS: ${result.routes.length} route(s) received',
      );

      for (final route in result.routes) {
        debugPrint(
          'Distance: ${route.distanceM} m, '
          'Risk: ${route.overallRiskLevel ?? "Not available"}',
        );
      }
    } catch (e) {
      debugPrint('ROUTE API ERROR: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: const PharosAppBar(),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              "Route Planner",
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: Colors.white,
              ),
            ),
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
                    title: Text(
                      "Bengaluru, Karnataka",
                      style: TextStyle(color: Colors.white),
                    ),
                    subtitle: Text(
                      "From Source",
                      style: TextStyle(color: Colors.grey, fontSize: 10),
                    ),
                  ),
                  Divider(color: Colors.white12),
                  ListTile(
                    leading: Icon(Icons.location_on, color: Colors.redAccent),
                    title: Text(
                      "Mangalore, Karnataka",
                      style: TextStyle(color: Colors.white),
                    ),
                    subtitle: Text(
                      "To Destination",
                      style: TextStyle(color: Colors.grey, fontSize: 10),
                    ),
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
