import csv
import unittest
from pathlib import Path
from calculate import calculate,timestamp
class MetricsTest(unittest.TestCase):
    def setUp(self):
        with (Path(__file__).parent/'events.csv').open() as source:self.rows=list(csv.DictReader(source))
        self.cutoff=timestamp('2026-11-22T00:00:00Z')
    def test_maturity_duplicates_practice_and_retention(self):
        value=calculate(self.rows,self.cutoff,True)
        self.assertEqual(value['retained_contributing_experts_28d'],1)
        self.assertEqual(value['newly_activated_28d'],1)
        self.assertEqual(value['activation_within_30d_of_ready'],{'numerator':2,'denominator':3,'rate':2/3})
        self.assertEqual(value['mature_cohort_repeat_days_30_to_60'],{'numerator':1,'denominator':2,'rate':.5})
    def test_synthetic_excluded_and_zero_denominator(self):
        self.assertIsNone(calculate(self.rows,self.cutoff)['mature_cohort_repeat_days_30_to_60']['rate'])
    def test_withdrawn_acceptance(self):
        self.rows.append(dict(event_id='withdrawal',expert_id='syn-a',event_type='acceptance_withdrawn',occurred_at='2026-11-20T00:00:00Z',artifact_id='syn-art-a3',artifact_type='production',is_synthetic='true'))
        self.assertEqual(calculate(self.rows,self.cutoff,True)['retained_contributing_experts_28d'],0)
    def test_window_boundaries(self):
        for row in self.rows:
            if row['artifact_id']=='syn-art-a3':row['occurred_at']='2026-10-25T00:00:00Z'
        self.assertEqual(calculate(self.rows,self.cutoff,True)['retained_contributing_experts_28d'],1)
        for row in self.rows:
            if row['artifact_id']=='syn-art-a3':row['occurred_at']='2026-11-22T00:00:00Z'
        self.assertEqual(calculate(self.rows,self.cutoff,True)['retained_contributing_experts_28d'],0)
if __name__=='__main__':unittest.main()
