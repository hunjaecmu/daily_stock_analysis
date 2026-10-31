# -*- coding: utf-8 -*-
import unittest
from unittest import mock

from src.services import us_overnight


def _fake_fetch(symbol, column):
    if symbol == us_overnight.YIELD_SYMBOL:
        return 4.98, "2026-10-29"
    return 101.88, "2026-10-30"


class UsOvernightLineTest(unittest.TestCase):
    def test_each_number_shows_its_own_date(self):
        with mock.patch.object(us_overnight, "_fetch_latest", side_effect=_fake_fetch):
            line = us_overnight.build_us_overnight_line()
        self.assertEqual(
            line,
            "**밤사이 미국** | 10년물 금리 4.98% (2026-10-29 기준) · 달러 인덱스 101.88 (2026-10-30 기준)",
        )

    def test_one_failure_is_marked_and_other_number_stays(self):
        def fetch(symbol, column):
            if symbol == us_overnight.YIELD_SYMBOL:
                raise ValueError("down")
            return _fake_fetch(symbol, column)

        with mock.patch.object(us_overnight, "_fetch_latest", side_effect=fetch):
            line = us_overnight.build_us_overnight_line()
        self.assertEqual(
            line,
            "**밤사이 미국** | 10년물 금리 확인 실패 · 달러 인덱스 101.88 (2026-10-30 기준)",
        )

    def test_no_line_when_both_fail(self):
        with mock.patch.object(us_overnight, "_fetch_latest", side_effect=ValueError("down")):
            self.assertIsNone(us_overnight.build_us_overnight_line())


if __name__ == "__main__":
    unittest.main()
