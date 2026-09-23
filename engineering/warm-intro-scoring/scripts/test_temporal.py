import unittest
import temporal
class TemporalTests(unittest.TestCase):
 def test_shared_month_alone_does_not_prove_overlap(self):
  a={'start':'2020-01','end':'2020-04'};b={'start':'2020-04','end':'2021-01'}
  self.assertEqual(temporal.overlap(a,b,'2026-09-23')['status'],'unknown')
 def test_year_only_overlap_uses_guaranteed_bounds(self):
  r=temporal.overlap({'start':'2020','end':'2023'},{'start':'2021','end':'2024'},'2026-09-23')
  self.assertEqual(r['start'],'2021-12-31');self.assertEqual(r['end'],'2023-01-01')
 def test_disjoint_dates_do_not_match(self):
  self.assertEqual(temporal.overlap({'start':'2020','end':'2021'},{'start':'2022','end':'2023'},'2026-09-23')['status'],'non_overlap')
 def test_current_role_cannot_extend_past_source_observation(self):
  r=temporal.overlap({'start':'2020','current':True,'observed_at':'2026-08-02'},{'start':'2026-09-01','current':True,'observed_at':'2026-09-23'},'2026-09-23')
  self.assertEqual(r['status'],'unknown')
 def test_unknown_end_does_not_mean_current(self):
  self.assertEqual(temporal.overlap({'start':'2020'},{'start':'2021','end':'2023'},'2026-09-23')['status'],'unknown')
 def test_invalid_interval_rejected(self):
  with self.assertRaises(ValueError):temporal.overlap({'start':'2022','end':'2020'},{'start':'2021','end':'2023'},'2026-09-23')
