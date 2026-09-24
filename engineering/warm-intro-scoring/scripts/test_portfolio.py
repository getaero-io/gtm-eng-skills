import unittest
import portfolio
class PortfolioTests(unittest.TestCase):
 def fixture(self):
  return {'companies':[{'id':'seed','name':'Seed','domain':'seed.example'},{'id':'peer','name':'Peer','domain':'peer.example'}], 'investors':[{'id':'fund','name':'Fund','type':'firm'}], 'edges':[{'company_id':c,'investor_id':'fund','source_url':'https://fund.example/portfolio','observed_at':'2026-09-23'} for c in ['seed','peer']]}
 def test_expands_only_connected_investors_and_excludes_seed(self):
  r=portfolio.expand(self.fixture(),'seed');self.assertEqual([x['id'] for x in r['portfolio_companies']],['peer']);self.assertEqual(r['coverage_status'],'partial')
 def test_duplicate_receipts_do_not_multiply_companies(self):
  d=self.fixture();d['edges']+=d['edges'];self.assertEqual(len(portfolio.expand(d,'seed')['portfolio_companies']),1)
 def test_missing_source_is_not_an_investment_edge(self):
  d=self.fixture();d['edges'][0].pop('source_url')
  with self.assertRaises(ValueError):portfolio.expand(d,'seed')
 def test_unknown_endpoint_rejected(self):
  d=self.fixture();d['edges'][0]['investor_id']='stranger'
  with self.assertRaises(ValueError):portfolio.expand(d,'seed')
 def test_duplicate_identity_rejected(self):
  d=self.fixture();d['companies'].append(d['companies'][0])
  with self.assertRaises(ValueError):portfolio.expand(d,'seed')
 def test_no_investors_is_explicit_gap(self):
  d=self.fixture();d['edges']=[];r=portfolio.expand(d,'seed');self.assertEqual(r['coverage_status'],'no_disclosed_edges');self.assertFalse(r['portfolio_companies'])

 def test_calendar_and_week_dates_have_explicit_portable_semantics(self):
  cases={'2026-09-23':'2026-09-23','20260923':'2026-09-23',
         '2026-W39-3':'2026-09-23','2026W393':'2026-09-23',
         '2026-W39':'2026-09-21','2026W39':'2026-09-21',
         '2020-W53-7':'2021-01-03','00010101':'0001-01-01',
         '0001-W01-1':'0001-01-01','99991231':'9999-12-31'}
  for value,expected in cases.items():
   with self.subTest(value=value):self.assertEqual(portfolio.source_date(value).isoformat(),expected)
 def test_invalid_source_dates_reject_instead_of_normalizing(self):
  for value in [None,20260923,True,'','2026-09','2026-09-23T00:00:00',
                '2026-09-23\n','2026-0923','2026W39-3','2026-W393',
                '2021-W53-1','2020-W00-1','2020W541','2020-W53-0',
                '2020-W53-8','20260229','2026-02-30','0000-01-01',
                '10000-01-01','0000W011','9999-W52-7']:
   with self.subTest(value=value),self.assertRaises(ValueError):portfolio.source_date(value)
 def test_expansion_accepts_basic_dates_without_fromisoformat(self):
  from datetime import date
  from unittest.mock import patch
  class PortableDate(date):
   @classmethod
   def fromisoformat(cls,value):raise AssertionError('Version-dependent parser must not be used')
   @classmethod
   def today(cls):return cls(2026,9,23)
  d=self.fixture();d['edges'][0]['observed_at']='20260923';d['edges'][1]['observed_at']='2026W393'
  with patch.object(portfolio,'date',PortableDate):
   result=portfolio.expand(d,'seed')
   self.assertEqual(len(result['portfolio_companies']),1)
   self.assertEqual(result['seed_evidence'][0]['observed_at'],'20260923')
 def test_future_basic_and_week_observations_remain_rejected(self):
  from datetime import date
  from unittest.mock import patch
  class FrozenDate(date):
   @classmethod
   def today(cls):return cls(2026,9,23)
  for observed in ['20260924','2026-W39-4']:
   d=self.fixture();d['edges'][0]['observed_at']=observed
   with self.subTest(observed=observed),patch.object(portfolio,'date',FrozenDate),self.assertRaises(ValueError):portfolio.expand(d,'seed')
