import unittest

from core.poi_detector import POI, POIDetector


class POIDetectorTest(unittest.TestCase):
    def test_calculates_distance_along_track_from_start(self):
        detector = POIDetector()
        track_points = [
            {'latitude': 0.0, 'longitude': 0.0},
            {'latitude': 0.1, 'longitude': 0.0},
            {'latitude': 0.2, 'longitude': 0.0},
        ]
        poi = POI(
            id='test-poi',
            type='water',
            lat=0.1,
            lon=0.0,
            name='Test water',
            tags={},
        )

        detector.calculate_distances_to_track([poi], track_points)

        self.assertAlmostEqual(poi.distance_along_track, 11.1, delta=1.0)
        self.assertAlmostEqual(poi.distance, 0.0, delta=0.01)

    def test_sorts_pois_by_distance_along_track(self):
        detector = POIDetector()
        track_points = [
            {'latitude': 0.0, 'longitude': 0.0},
            {'latitude': 0.1, 'longitude': 0.0},
            {'latitude': 0.2, 'longitude': 0.0},
        ]
        pois = [
            POI(id='second', type='water', lat=0.2, lon=0.0, name='Second', tags={}),
            POI(id='first', type='water', lat=0.0, lon=0.0, name='First', tags={}),
        ]

        result = detector.calculate_distances_to_track(pois, track_points)

        self.assertEqual([poi.id for poi in result], ['first', 'second'])


if __name__ == '__main__':
    unittest.main()
