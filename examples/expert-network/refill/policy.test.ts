import assert from 'node:assert/strict';
import {slots,normalize} from './policy';
assert.equal(slots(99),1);assert.equal(slots(100),0);assert.equal(slots(101),0);assert.equal(slots(0),100);
const p={first_name:'Test',last_name:'Person',title:'Engagement Manager',linkedin_url:'https://www.linkedin.com/in/test-person/',company_domain:'mckinsey.com',country:'United States'};
assert.equal(normalize(p,'mckinsey.com','consulting')?.profile,'https://www.linkedin.com/in/test-person');
assert.equal(normalize({...p,title:'Partner Global Chief Information Officer'},'mckinsey.com','consulting'),null);
assert.equal(normalize({...p,company_domain:'other.com'},'mckinsey.com','consulting'),null);
assert.equal(normalize({...p,country:'France'},'mckinsey.com','consulting'),null);
assert.equal(normalize({...p,linkedin_url:''},'mckinsey.com','consulting'),null);
assert.equal(normalize({...p,title:'Recruiting Manager'},'mckinsey.com','consulting'),null);
assert.equal(normalize({...p,title:'Partner and Counsel Onboarding',company_domain:'lw.com'},'lw.com','law'),null);
assert(normalize({...p,title:'Associate',company_domain:'lw.com'},'lw.com','law'));
for (const title of ['Associate Director of Finance','Attorney Development HRIS Manager','Senior Manager of Attorney Career Progression','Head of Knowledge Management Practice Innovation Counsel','Administrative Assistant to Partner General Counsel']) {
  assert.equal(normalize({...p,title,company_domain:'lw.com'},'lw.com','law'),null);
}
console.log('PASS: threshold boundary, stable identity, country/company mismatch, internal staff exclusion, law title.');
