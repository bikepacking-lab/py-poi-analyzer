import unittest
from unittest.mock import Mock, patch

from analyzers.track_analyzer import TrackAnalyzer
from core.poi_detector import POIDetector


class MountainPassesTest(unittest.TestCase):
    def test_queries_osm_for_named_and_elevated_mountain_pass_nodes(self):
        detector = POIDetector()
        node = {
            'type': 'node',
            'id': 42,
            'lat': 45.0,
            'lon': 6.0,
            'tags': {'mountain_pass': 'yes', 'ele': '1500', 'name': 'Col test'}
        }

        with patch.object(detector, '_query_overpass', return_value=[node]) as query:
            result = detector.detect_mountain_passes((44.0, 5.0, 46.0, 7.0))

        self.assertEqual(result, [node])
        query.assert_called_once()
        self.assertIn('node["mountain_pass"="yes"]["ele"]', query.call_args.args[0])
        self.assertIn('(44.000000,5.000000,46.000000,7.000000)', query.call_args.args[0])

    def test_builds_climb_metrics_and_departure_commune(self):
        detector = POIDetector()
        track_points = [
            {'latitude': 45.0, 'longitude': 6.0, 'elevation': 100.0},
            {'latitude': 45.01, 'longitude': 6.0, 'elevation': 150.0},
            {'latitude': 45.02, 'longitude': 6.0, 'elevation': 200.0},
        ]
        pass_nodes = [{
            'type': 'node',
            'id': 42,
            'lat': 45.02,
            'lon': 6.0,
            'tags': {'mountain_pass': 'yes', 'ele': '220', 'name': 'Col test'}
        }]
        resolver = Mock()
        resolver.resolve.return_value = {
            'name': 'Village',
            'address': {'village': 'Village'}
        }

        with patch('analyzers.track_analyzer.PlaceResolver', return_value=resolver):
            passes = TrackAnalyzer._build_mountain_passes(
                pass_nodes, track_points, detector
            )

        assert passes is not None
        self.assertEqual(len(passes), 1)
        mountain_pass = passes[0]
        self.assertEqual(mountain_pass['name'], 'Col test')
        self.assertAlmostEqual(mountain_pass['kilometer_on_track'], 2.22, delta=0.1)
        self.assertAlmostEqual(mountain_pass['distance_km'], 2.22, delta=0.1)
        self.assertEqual(mountain_pass['altitude_m'], 220.0)
        self.assertEqual(mountain_pass['ascent_m'], 120.0)
        self.assertAlmostEqual(mountain_pass['average_grade_percent'], 5.4, delta=0.2)
        self.assertAlmostEqual(mountain_pass['max_grade_percent'], 4.5, delta=0.2)
        self.assertEqual(mountain_pass['start_commune'], 'Village')

    def test_excludes_passes_far_from_track_and_marks_query_failure(self):
        detector = POIDetector()
        track_points = [
            {'latitude': 45.0, 'longitude': 6.0, 'elevation': 100.0},
            {'latitude': 45.01, 'longitude': 6.0, 'elevation': 150.0},
        ]
        distant_pass = {
            'id': 43,
            'lat': 45.0,
            'lon': 6.1,
            'tags': {'mountain_pass': 'yes', 'ele': '1500'}
        }

        self.assertEqual(
            TrackAnalyzer._build_mountain_passes(
                [distant_pass], track_points, detector
            ),
            []
        )
        with patch.object(detector, '_query_overpass', return_value=None):
            self.assertIsNone(
                detector.detect_mountain_passes((44.0, 5.0, 46.0, 7.0))
            )


if __name__ == '__main__':
    unittest.main()
