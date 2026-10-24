import unittest
from unittest.mock import Mock, patch

from analyzers.track_analyzer import TrackAnalyzer
from core.place_resolver import PlaceResolver
from core.poi_detector import POI


class DailyStagesTest(unittest.TestCase):
    def test_splits_track_by_daily_duration_and_assigns_pois_once(self):
        track_points = [
            {'distance': 0.0, 'elevation': 100.0},
            {'distance': 50.0, 'elevation': 150.0},
            {'distance': 100.0, 'elevation': 200.0},
            {'distance': 150.0, 'elevation': 210.0},
        ]
        pois = [
            POI(
                id='start',
                type='water',
                lat=0,
                lon=0,
                name='Start',
                tags={},
                distance_along_track=10.0
            ),
            POI(
                id='boundary',
                type='water',
                lat=0,
                lon=0,
                name='Boundary',
                tags={},
                distance_along_track=100.0
            ),
            POI(
                id='finish',
                type='water',
                lat=0,
                lon=0,
                name='Finish',
                tags={},
                distance_along_track=150.0
            ),
        ]

        stages = TrackAnalyzer._build_daily_stages(track_points, pois, 'gravel')

        self.assertEqual(len(stages), 2)
        self.assertEqual([stage['distance_km'] for stage in stages], [100.0, 50.0])
        self.assertEqual([stage['total_ascent_m'] for stage in stages], [100.0, 10.0])
        self.assertEqual(
            [[poi['id'] for poi in stage['pois']] for stage in stages],
            [['start'], ['boundary', 'finish']]
        )
        self.assertIn('total_hours', stages[0]['duration'])
        self.assertIn('average_speed_kmh', stages[0])

    def test_returns_no_stages_for_track_with_fewer_than_two_points(self):
        self.assertEqual(
            TrackAnalyzer._build_daily_stages(
                [{'distance': 0.0}], [], 'gravel'
            ),
            []
        )

    def test_adds_nominatim_locations_for_each_stage_endpoint(self):
        track_points = [
            {'distance': 0.0, 'elevation': 100.0, 'latitude': 43.0, 'longitude': 1.0},
            {'distance': 50.0, 'elevation': 150.0, 'latitude': 43.5, 'longitude': 1.5},
            {'distance': 100.0, 'elevation': 200.0, 'latitude': 44.0, 'longitude': 2.0},
            {'distance': 150.0, 'elevation': 210.0, 'latitude': 44.5, 'longitude': 2.5},
        ]
        response = Mock()
        response.json.return_value = {
            'name': 'Place',
            'display_name': 'Place, France',
            'address': {'hamlet': 'Lieu-dit', 'village': 'Village'}
        }
        resolver = PlaceResolver()

        with patch.object(resolver.session, 'get', return_value=response) as get_request:
            with patch('core.place_resolver.time.sleep'):
                stages = TrackAnalyzer._build_daily_stages(
                    track_points, [], 'gravel', resolver
                )

        self.assertEqual(len(stages), 2)
        self.assertEqual(stages[0]['start_location']['name'], 'Lieu-dit')
        self.assertEqual(stages[0]['end_location']['name'], 'Lieu-dit')
        self.assertEqual(stages[1]['start_location']['name'], 'Lieu-dit')
        self.assertEqual(stages[1]['end_location']['display_name'], 'Place, France')
        self.assertEqual(get_request.call_count, 3)
        self.assertIn('addressdetails', get_request.call_args.kwargs['params'])


if __name__ == '__main__':
    unittest.main()
