from __future__ import annotations

import unittest

import numpy as np

from lib.time_utils import NS_PER_MS, bucket_100ms, to_ns


class TimeUnitTests(unittest.TestCase):
    def test_us_and_ns_inputs_produce_same_duration(self) -> None:
        ns_values = np.array(
            ["2025-01-01T00:00:00.123456000", "2025-01-01T00:00:27.246912000"],
            dtype="datetime64[ns]",
        )
        us_values = ns_values.astype("datetime64[us]")

        ns_delta_ms = int((to_ns(ns_values)[1] - to_ns(ns_values)[0]) // NS_PER_MS)
        us_delta_ms = int((to_ns(us_values)[1] - to_ns(us_values)[0]) // NS_PER_MS)

        self.assertEqual(ns_delta_ms, 27123)
        self.assertEqual(us_delta_ms, 27123)

    def test_bucket_100ms_is_dtype_invariant(self) -> None:
        ns_values = np.array(
            ["2025-01-01T00:00:00.050000000", "2025-01-01T00:00:00.150000000"],
            dtype="datetime64[ns]",
        )
        us_values = ns_values.astype("datetime64[us]")

        self.assertEqual(bucket_100ms(ns_values).tolist(), [0, 1])
        self.assertEqual(bucket_100ms(us_values).tolist(), [0, 1])


if __name__ == "__main__":
    unittest.main()
