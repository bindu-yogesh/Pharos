
class RouteCollectionResponse {
  final List<RouteOption> routes;

  RouteCollectionResponse({required this.routes});

  factory RouteCollectionResponse.fromJson(Map<String, dynamic> json) {
    return RouteCollectionResponse(
      routes: (json['routes'] as List? ?? [])
          .map((item) =>
              RouteOption.fromJson(Map<String, dynamic>.from(item)))
          .toList(),
    );
  }
}

class RouteOption {
  final double distanceM;
  final double durationS;
  final RouteGeometry geometry;
  final List<RiskSegment> segments;
  final String riskAssessment;
  final List<String> riskDataGaps;
  final double? overallRiskScore;
  final String? overallRiskLevel;
  final String? overallRiskColor;
  final List<String> overallRiskReasons;

  RouteOption({
    required this.distanceM,
    required this.durationS,
    required this.geometry,
    required this.segments,
    required this.riskAssessment,
    required this.riskDataGaps,
    this.overallRiskScore,
    this.overallRiskLevel,
    this.overallRiskColor,
    required this.overallRiskReasons,
  });

  factory RouteOption.fromJson(Map<String, dynamic> json) {
    return RouteOption(
      distanceM: (json['distance_m'] as num).toDouble(),
      durationS: (json['duration_s'] as num).toDouble(),
      geometry: RouteGeometry.fromJson(
        Map<String, dynamic>.from(json['geometry']),
      ),
      segments: (json['segments'] as List? ?? [])
          .map((item) =>
              RiskSegment.fromJson(Map<String, dynamic>.from(item)))
          .toList(),
      riskAssessment: json['risk_assessment'] ?? 'incomplete',
      riskDataGaps: List<String>.from(json['risk_data_gaps'] ?? []),
      overallRiskScore: (json['overall_risk_score'] as num?)?.toDouble(),
      overallRiskLevel: json['overall_risk_level'] as String?,
      overallRiskColor: json['overall_risk_color'] as String?,
      overallRiskReasons:
          List<String>.from(json['overall_risk_reasons'] ?? []),
    );
  }
}

class RouteGeometry {
  final String type;
  final List<List<double>> coordinates;

  RouteGeometry({
    required this.type,
    required this.coordinates,
  });

  factory RouteGeometry.fromJson(Map<String, dynamic> json) {
    return RouteGeometry(
      type: json['type'] ?? 'LineString',
      coordinates: (json['coordinates'] as List)
          .map((point) => (point as List)
              .map((value) => (value as num).toDouble())
              .toList())
          .toList(),
    );
  }
}

class RiskSegment {
  final int segmentId;
  final List<double> start;
  final List<double> end;
  final List<List<double>> coordinates;
  final RouteGeometry geometry;
  final double lengthM;
  final String riskStatus;
  final String riskAssessment;
  final int? roadSegmentId;
  final double? roadMatchDistanceM;
  final double? slopePercent;
  final Map<String, dynamic>? weatherForecast;
  final double? score;
  final String? level;
  final String? color;
  final RiskFlags? riskFlags;
  final List<String> reasons;
  final List<String> riskDataGaps;

  RiskSegment({
    required this.segmentId,
    required this.start,
    required this.end,
    required this.coordinates,
    required this.geometry,
    required this.lengthM,
    required this.riskStatus,
    required this.riskAssessment,
    this.roadSegmentId,
    this.roadMatchDistanceM,
    this.slopePercent,
    this.weatherForecast,
    this.score,
    this.level,
    this.color,
    this.riskFlags,
    required this.reasons,
    required this.riskDataGaps,
  });

  factory RiskSegment.fromJson(Map<String, dynamic> json) {
    List<double> parsePoint(dynamic point) {
      return (point as List)
          .map((value) => (value as num).toDouble())
          .toList();
    }

    return RiskSegment(
      segmentId: json['segment_id'] as int,
      start: parsePoint(json['start']),
      end: parsePoint(json['end']),
      coordinates: (json['coordinates'] as List)
          .map((point) => parsePoint(point))
          .toList(),
      geometry: RouteGeometry.fromJson(
        Map<String, dynamic>.from(json['geometry']),
      ),
      lengthM: (json['length_m'] as num).toDouble(),
      riskStatus: json['risk_status'] ?? '',
      riskAssessment: json['risk_assessment'] ?? 'incomplete',
      roadSegmentId: json['road_segment_id'] as int?,
      roadMatchDistanceM:
          (json['road_match_distance_m'] as num?)?.toDouble(),
      slopePercent: (json['slope_percent'] as num?)?.toDouble(),
      weatherForecast: json['weather_forecast'] == null
          ? null
          : Map<String, dynamic>.from(json['weather_forecast']),
      score: (json['score'] as num?)?.toDouble(),
      level: json['level'] as String?,
      color: json['color'] as String?,
      riskFlags: json['risk_flags'] == null
          ? null
          : RiskFlags.fromJson(
              Map<String, dynamic>.from(json['risk_flags']),
            ),
      reasons: List<String>.from(json['reasons'] ?? []),
      riskDataGaps: List<String>.from(json['risk_data_gaps'] ?? []),
    );
  }
}

class RiskFlags {
  final bool? heavyRain;
  final bool? landslideHistory;
  final bool? steepSlope;
  final bool? recentHazardReport;
  final bool? heavyTraffic;
  final bool? lowVisibility;

  RiskFlags({
    this.heavyRain,
    this.landslideHistory,
    this.steepSlope,
    this.recentHazardReport,
    this.heavyTraffic,
    this.lowVisibility,
  });

  factory RiskFlags.fromJson(Map<String, dynamic> json) {
    return RiskFlags(
      heavyRain: json['heavy_rain'] as bool?,
      landslideHistory: json['landslide_history'] as bool?,
      steepSlope: json['steep_slope'] as bool?,
      recentHazardReport: json['recent_hazard_report'] as bool?,
      heavyTraffic: json['heavy_traffic'] as bool?,
      lowVisibility: json['low_visibility'] as bool?,
    );
  }
}
