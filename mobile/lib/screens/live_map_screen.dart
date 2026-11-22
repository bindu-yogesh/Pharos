import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';

import 'main_navigation.dart';
import '../services/route_api_service.dart';
import '../services/risk_api_service.dart';

class LiveMapScreen extends StatefulWidget {
  const LiveMapScreen({super.key});

  @override
  State<LiveMapScreen> createState() => _LiveMapScreenState();
}

class _LiveMapScreenState extends State<LiveMapScreen> {
  final MapController _mapController = MapController();
  bool _routeCameraFitted = false;

  Position? _currentPosition;
  StreamSubscription<Position>? _positionSubscription;

  bool _tracking = false;
  bool _loading = true;
  bool _fetchingRisk = false;
  String? _locationError;
  DateTime? _lastRiskFetch;

  static const LatLng _defaultCenter = LatLng(12.9716, 77.5946);

  @override
  void initState() {
    super.initState();
    _startTracking();
  }

  Future<void> _startTracking() async {
    try {
      final serviceEnabled =
          await Geolocator.isLocationServiceEnabled();

      if (!serviceEnabled) {
        throw Exception('Please enable your device location service.');
      }

      LocationPermission permission =
          await Geolocator.checkPermission();

      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }

      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        throw Exception('Location permission was not granted.');
      }

      const settings = LocationSettings(
        accuracy: LocationAccuracy.best,
        distanceFilter: 10,
      );

      final initialPosition = await Geolocator.getCurrentPosition(
        locationSettings: settings,
      );

      if (!mounted) return;

      _updatePosition(initialPosition);
      await _refreshRisk();

      _positionSubscription =
          Geolocator.getPositionStream(
        locationSettings: settings,
      ).listen(
        (position) {
          _updatePosition(position);

          final lastFetch = _lastRiskFetch;
          if (lastFetch == null ||
              DateTime.now().difference(lastFetch).inSeconds >= 20) {
            _refreshRisk();
          }
        },
        onError: (error) {
          if (mounted) {
            setState(() {
              _locationError = 'Location updates failed: $error';
            });
          }
        },
      );

      if (mounted) {
        setState(() {
          _tracking = true;
          _loading = false;
          _locationError = null;
        });
      }
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _loading = false;
        _locationError = e.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  void _updatePosition(Position position) {
    if (!mounted) return;

    setState(() {
      _currentPosition = position;
      _locationError = null;
    });

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;

      try {
        if (!_routeCameraFitted) {
          _mapController.move(
            LatLng(position.latitude, position.longitude),
            15,
          );
        }
      } catch (_) {
        // The map may not be attached yet.
      }
    });
  }

  Future<void> _refreshRisk() async {
    if (_fetchingRisk) return;

    _fetchingRisk = true;
    _lastRiskFetch = DateTime.now();

    try {
      final result =
          await RiskApiService.getCurrentLocationRisk();
      debugPrint('LIVE RISK UPDATED: $result');
    } catch (e) {
      debugPrint('LIVE RISK ERROR: $e');
    } finally {
      _fetchingRisk = false;
    }
  }

  @override
  void dispose() {
    _positionSubscription?.cancel();
    _mapController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: const PharosAppBar(),
      body: Stack(
        children: [
          FlutterMap(
            mapController: _mapController,
            options: MapOptions(
              center: _defaultCenter,
              zoom: 13,
              minZoom: 3,
              maxZoom: 19,
            ),
            children: [
              TileLayer(
                urlTemplate:
                    'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                userAgentPackageName: 'com.example.road_safe',
              ),

              ValueListenableBuilder(
                valueListenable: RouteApiService.latestRoute,
                builder: (context, response, child) {
                  if (response == null || response.routes.isEmpty) {
                    return const SizedBox.shrink();
                  }

                  final coordinates =
                      response.routes.first.geometry.coordinates;

                  if (coordinates.isEmpty) {
                    return const SizedBox.shrink();
                  }

                  final points = coordinates
                      .where((point) => point.length >= 2)
                      .map((point) => LatLng(point[1], point[0]))
                      .toList();

                  if (points.isEmpty) {
                    return const SizedBox.shrink();
                  }

                  if (!_routeCameraFitted) {
                    _routeCameraFitted = true;
                    WidgetsBinding.instance.addPostFrameCallback((_) {
                      if (mounted) {
                        _mapController.fitCamera(
                          CameraFit.coordinates(
                            coordinates: points,
                            padding: const EdgeInsets.all(60),
                          ),
                        );
                      }
                    });
                  }

                  return PolylineLayer(
                    polylines: [
                      Polyline(
                        points: points,
                        strokeWidth: 5,
                        color: Colors.cyanAccent,
                      ),
                    ],
                  );
                },
              ),

              if (_currentPosition != null)
                MarkerLayer(
                  markers: [
                    Marker(
                      point: LatLng(
                        _currentPosition!.latitude,
                        _currentPosition!.longitude,
                      ),
                      width: 55,
                      height: 55,
                      child: const Icon(
                        Icons.my_location,
                        color: Colors.blue,
                        size: 38,
                      ),
                    ),
                  ],
                ),
            ],
          ),

          Positioned(
            top: 12,
            left: 12,
            right: 12,
            child: ValueListenableBuilder<Map<String, dynamic>?>(
              valueListenable: RiskApiService.latestRisk,
              builder: (context, risk, child) {
                final gaps = risk?['risk_data_gaps'] as List? ?? [];

                return Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFF162032).withOpacity(0.95),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: Colors.orangeAccent),
                  ),
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
                      const SizedBox(height: 5),
                      Text(
                        'Risk level: ${risk?['risk_level'] ?? 'Waiting for data'}',
                        style: const TextStyle(color: Colors.white),
                      ),
                      Text(
                        'Risk score: ${risk?['risk_score'] ?? 'Not available'}',
                        style: const TextStyle(color: Colors.white),
                      ),
                      Text(
                        'Assessment: ${risk?['risk_assessment'] ?? 'Loading'}',
                        style: const TextStyle(color: Colors.white70),
                      ),
                      if (gaps.isNotEmpty)
                        Text(
                          'Data gaps: ${gaps.join(', ')}',
                          style: const TextStyle(
                            color: Colors.orangeAccent,
                            fontSize: 11,
                          ),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                    ],
                  ),
                );
              },
            ),
          ),

          Positioned(
            bottom: 30,
            left: 12,
            right: 12,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (_locationError != null)
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(10),
                    margin: const EdgeInsets.only(bottom: 8),
                    decoration: BoxDecoration(
                      color: Colors.red.shade900,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Text(
                      _locationError!,
                      style: const TextStyle(color: Colors.white),
                    ),
                  ),

                if (_currentPosition != null)
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: const Color(0xFF162032).withOpacity(0.95),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      'GPS: ${_currentPosition!.latitude.toStringAsFixed(5)}, '
                      '${_currentPosition!.longitude.toStringAsFixed(5)}'
                      '\n${_tracking ? 'Live location tracking active' : 'Location available'}',
                      style: const TextStyle(color: Colors.white),
                    ),
                  ),

                const SizedBox(height: 8),

                ValueListenableBuilder(
                  valueListenable: RouteApiService.latestRoute,
                  builder: (context, response, child) {
                    if (response == null || response.routes.isEmpty) {
                      return const SizedBox.shrink();
                    }

                    final route = response.routes.first;

                    return Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: const Color(0xFF162032).withOpacity(0.95),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: Colors.cyanAccent),
                      ),
                      child: Text(
                        'CALCULATED ROUTE\n'
                        'Distance: ${(route.distanceM / 1000).toStringAsFixed(2)} km\n'
                        'Risk: ${route.overallRiskLevel ?? 'Not available'}\n'
                        'Assessment: ${route.riskAssessment}',
                        style: const TextStyle(color: Colors.white),
                      ),
                    );
                  },
                ),
              ],
            ),
          ),

          if (_loading)
            const Center(
              child: CircularProgressIndicator(),
            ),

          Positioned(
            right: 14,
            bottom: 14,
            child: FloatingActionButton.small(
              heroTag: 'refresh_live_location',
              onPressed: _startTracking,
              child: const Icon(Icons.my_location),
            ),
          ),

          const Positioned(
            left: 8,
            top: 155,
            child: Text(
              'Â© OpenStreetMap contributors',
              style: TextStyle(
                fontSize: 10,
                color: Colors.black87,
                backgroundColor: Colors.white70,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
