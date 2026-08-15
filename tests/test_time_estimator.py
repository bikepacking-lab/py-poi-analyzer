import unittest

from core.time_estimator import TimeEstimator


class TimeEstimatorTest(unittest.TestCase):
    def test_uses_daily_duration_for_human_readable_format(self):
        estimate = TimeEstimator.estimate_time(
            distance_km=827,
            total_ascent_m=0,
            speed_kmh=12,
            activity_type='gravel',
            breaks_per_hour=5,
        )

        self.assertEqual(estimate['formatted_moving_dhm'], '8d 4h 55min')
        self.assertEqual(estimate['formatted_total_dhm'], '9d 2h 39min')


if __name__ == '__main__':
    unittest.main()
