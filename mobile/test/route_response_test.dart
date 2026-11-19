import 'package:flutter_test/flutter_test.dart';
import 'package:road_safe/models/route_response.dart';

void main() {
  test('Route API response parses correctly', () {
    final json = {
      'routes': [
        {
          'distance_m': 28566.4,
          'duration_s': 1800,
          'geometry': {
            'type': 'LineString',
            'coordinates': [
              [75.72, 12.87],
              [75.71, 12.88]
            ]
          },
          'segments': [
            {
              'segment_id': 1,
              'start': [75.72, 12.87],
              'end': [75.71, 12.88],
              'coordinates': [
                [75.72, 12.87],
                [75.71, 12.88]
              ],
              'geometry': {
                'type': 'LineString',
                'coordinates': [
                  [75.72, 12.87],
                  [75.71, 12.88]
                ]
              },
              'length_m': 1000,
              'risk_status': 'incomplete',
              'risk_assessment': 'incomplete',
              'risk_flags': {
                'heavy_rain': false,
                'landslide_history': false,
                'steep_slope': false,
                'recent_hazard_report': false,
                'heavy_traffic': null,
                'low_visibility': false
              },
              'risk_data_gaps': ['heavy_traffic']
            }
          ],
          'risk_assessment': 'incomplete',
          'risk_data_gaps': ['heavy_traffic'],
          'overall_risk_reasons': []
        }
      ]
    };

    final result = RouteCollectionResponse.fromJson(json);

    expect(result.routes.length, 1);
    expect(result.routes.first.distanceM, 28566.4);
    expect(result.routes.first.riskAssessment, 'incomplete');
    expect(result.routes.first.segments.length, 1);
    expect(
      result.routes.first.segments.first.riskFlags!.heavyTraffic,
      isNull,
    );
    expect(
      result.routes.first.riskDataGaps,
      contains('heavy_traffic'),
    );
  });
}
