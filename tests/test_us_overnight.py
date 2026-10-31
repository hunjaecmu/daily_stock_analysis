# -*- coding: utf-8 -*-
import unittest
from unittest import mock

from src.services import us_overnight


def _patch_fred(**kwargs):
    return mock.patch.object(us_overnight, "_fetch_fred_latest", **kwargs)


def _patch_dollar(**kwargs):
    return mock.patch.object(us_overnight, "_fetch_dollar_latest", **kwargs)


class UsOvernightLineTest(unittest.TestCase):
    def test_each_number_shows_its_own_date(self):
        with _patch_fred(return_value=(4.98, "2026-10-29")), _patch_dollar(return_value=(101.88, "2026-10-30")):
            line = us_overnight.build_us_overnight_line()
        self.assertEqual(
            line,
            "**밤사이 미국** | 10년물 금리 4.98% (2026-10-29 기준) · 달러 인덱스 101.88 (2026-10-30 기준)",
        )

    def test_one_failure_is_marked_and_other_number_stays(self):
        with _patch_fred(side_effect=ValueError("down")), _patch_dollar(return_value=(101.88, "2026-10-30")):
            line = us_overnight.build_us_overnight_line()
        self.assertEqual(
            line,
            "**밤사이 미국** | 10년물 금리 확인 실패 · 달러 인덱스 101.88 (2026-10-30 기준)",
        )

    def test_no_line_when_both_fail(self):
        with _patch_fred(side_effect=ValueError("down")), _patch_dollar(side_effect=ValueError("down")):
            self.assertIsNone(us_overnight.build_us_overnight_line())


class FredLatestTest(unittest.TestCase):
    def _fetch(self, csv_text):
        response = mock.Mock(text=csv_text)
        with mock.patch.object(us_overnight.requests, "get", return_value=response):
            return us_overnight._fetch_fred_latest("DGS10")

    def test_holiday_gap_keeps_the_last_real_date(self):
        csv_text = "observation_date,DGS10\n2026-11-09,4.10\n2026-11-10,4.12\n2026-11-11,\n"
        self.assertEqual(self._fetch(csv_text), (4.12, "2026-11-10"))

    def test_dot_placeholder_counts_as_empty(self):
        csv_text = "observation_date,DGS10\n2026-11-10,4.12\n2026-11-11,.\n"
        self.assertEqual(self._fetch(csv_text), (4.12, "2026-11-10"))

    def test_all_empty_raises(self):
        with self.assertRaises(ValueError):
            self._fetch("observation_date,DGS10\n2026-11-11,\n")


if __name__ == "__main__":
    unittest.main()
