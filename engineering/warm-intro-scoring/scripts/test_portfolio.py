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
