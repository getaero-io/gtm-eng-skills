/* eslint-disable @typescript-eslint/no-explicit-any -- Ported JSON contract/parity boundary; runtime validators reject malformed values. */
import {test,expect} from 'bun:test';
import {buildFeatures} from '../plays/features';
import {requireEvidenceRegistry} from '../plays/guardrails';
import {strictJSON} from '../plays/strict-json';
import fixture from './e2e-fixture.json';
test('invalid connector URLs cannot earn coworker points',()=>{
 const data=structuredClone(fixture);data.connectors[1].linkedin_url='not-a-profile';expect(()=>buildFeatures(data)).toThrow('Invalid connector');
});
test('one connector URL cannot occupy several ranked routes',()=>{
 const data=structuredClone(fixture);data.connectors.push({...data.connectors[1],id:'duplicate-person'});expect(()=>buildFeatures(data)).toThrow('Duplicate connector');
});
test('cloud scoring requires a registry even when the key was removed',()=>{
 expect(()=>requireEvidenceRegistry({paths:[]})).toThrow();expect(()=>requireEvidenceRegistry({evidence:[]})).not.toThrow();
});
test('ambiguous JSON keys and infinite numbers fail at every cloud boundary',()=>{
 expect(()=>strictJSON('{"review_status":"blocked_declined","review_status":"ready_for_human_review"}')).toThrow('Duplicate');
 expect(()=>strictJSON('{"weight":1e999}')).toThrow('Nonfinite');
});
import {isInvestorRole,metro} from '../plays/features';
test('investor relations and angel programs are not direct investment roles',()=>{
 expect(isInvestorRole('Investor Relations Manager')).toBe(false);expect(isInvestorRole('Angel Program Manager')).toBe(false);expect(isInvestorRole('Seed Investor')).toBe(true);
});
test('city names in other regions do not become California overlap',()=>{
 for(const value of ['San Jose, Costa Rica','Oakland, New Jersey','Sunnyvale, Texas','Berkeley, Missouri'])expect(metro(value)).toBeNull();
 expect(metro('San Jose, California, United States')).toBe('San Francisco Bay Area');
});
test('conflicting company sizes cannot inflate work scores',()=>{
 const data:any=structuredClone(fixture);const e={id:'size',source:'fixture:size',observed_at:'2026-08-02',detail:'Size'};
 data.company_sizes=[{company_id:'fictional-co',count:50000,evidence:e},{company_id:'fictional-co',count:12,evidence:{...e,id:'size2'}}];expect(()=>buildFeatures(data)).toThrow('Duplicate company size');
});
test('future current jobs are rejected instead of earning function points',()=>{
 const data=structuredClone(fixture);data.connectors[1].experience[0].startDate.year=2030;expect(()=>buildFeatures(data)).toThrow('future profile interval');
});
test('malformed profile URL paths cannot silently truncate to another identity',()=>{
 const data=structuredClone(fixture);data.connectors[1].linkedin_url+='/%2Fother';expect(()=>buildFeatures(data)).toThrow('Invalid connector');
});
import {normalizeCollectedProfile} from '../plays/collection';
test('cached reads cannot turn 2024 evidence into a 2026 observation',()=>{
 const raw={linkedinUrl:'https://linkedin.com/in/fixture',scrapedAt:'2024-03-01T00:00:00Z',experience:[]};
 expect(normalizeCollectedProfile(raw,'fixture',raw.linkedinUrl,'fixture:receipt','2026-09-23','2026-09-23').observed_at).toBe('2024-03-01');
 expect(()=>normalizeCollectedProfile({...raw,scrapedAt:undefined},'fixture',raw.linkedinUrl,'fixture:receipt','2026-09-23')).toThrow('original observation');
});
import {expandFeatureCatalog} from '../plays/guardrails';
test('dangling catalog entries fail rather than zeroing a feature',()=>{
 expect(()=>expandFeatureCatalog({feature_catalog:[],paths:[{features:{work_overlap:3}}]})).toThrow('catalog index');
});
test('stable contact IDs exclude self pairs even if the URL changes',()=>{
 const data=structuredClone(fixture);data.connectors[1]={...data.profiles[0],linkedin_url:'https://linkedin.com/in/another-slug'};expect(buildFeatures(data).coverage.self_pairs_excluded).toBe(1);
});
import {renderReview} from '../plays/report';
test('unresolved target coverage is visible and safely escaped',()=>{
 const data=buildFeatures(structuredClone(fixture));data.coverage.unresolved.push({target:{name:'<script>Missing</script>',linkedin_url:'https://linkedin.com/in/missing',company:'Unknown',domain:'unknown.test'},reason:'missing_profile'});
 const html=renderReview(data);expect(html).toContain('1 unresolved targets');expect(html).toContain('&lt;script&gt;Missing&lt;/script&gt;');
});
test('coverage notes disclose omitted candidates and are escaped',()=>{
 const data:any=buildFeatures(structuredClone(fixture));data.coverage.notes=['<b>7 zero-evidence paths</b> omitted'];
 expect(renderReview(data)).toContain('&lt;b&gt;7 zero-evidence paths&lt;/b&gt; omitted');
});
test('investor company name collisions cannot earn portfolio points',()=>{
 const data:any=structuredClone(fixture);data.connectors[2].company='Example Fund';data.funding_edges=[{target_domain:'fictional.test',investor_key:'fund',investor_firm:'Example Fund',source:'fixture:fund',detail:'Fund invested',observed_at:'2026-08-02'}];data.verified_firms=[{target_domain:'fictional.test',investor_key:'fund',evidence:{id:'verified:fund',source:'https://fund.example/portfolio',detail:'Fund invested',observed_at:'2026-08-02'}}];expect(buildFeatures(data).paths.find(p=>p.connector_id==='company').features.investor_portfolio.value).toBe(0);
});
test('numeric and named profile months preserve the same overlap',()=>{
 const a:any=structuredClone(fixture),b:any=structuredClone(fixture);a.connectors[1].experience[0].startDate.month=3;b.connectors[1].experience[0].startDate.month='March';expect(buildFeatures(a).paths.find(p=>p.connector_id==='coworker').features.work_overlap).toEqual(buildFeatures(b).paths.find(p=>p.connector_id==='coworker').features.work_overlap);
});
test('investor-facing employee titles cannot qualify as investing roles',()=>{
 for(const title of ['Investor Engagement','Investor Partnerships','Investor Reporting','Investor Marketing','Head of Investor Engagement'])expect(isInvestorRole(title)).toBe(false);
});
test('member-ID URLs fail closed without a reviewed identity alias',()=>{
 const data=structuredClone(fixture);data.connectors[1].linkedin_url='https://linkedin.com/in/ACoAAAbCdEf123';expect(()=>buildFeatures(data)).toThrow('Invalid connector');
});
test('known LinkedIn detail and language suffixes retain identity',()=>{
 const data=structuredClone(fixture);data.connectors[1].linkedin_url+='/details/experience/';expect(buildFeatures(data).paths).toHaveLength(4);
});
test('local reports require the same evidence registry as cloud reports',()=>{
 const data:any=buildFeatures(structuredClone(fixture));delete data.evidence;expect(()=>renderReview(data)).toThrow('registry');
});
test('collection retains an explicit reviewed account assignment',()=>{
 const raw={linkedinUrl:'https://linkedin.com/in/fixture',experience:[]};expect(normalizeCollectedProfile(raw,'fixture',raw.linkedinUrl,'fixture:receipt','2026-09-23','2026-08-02','example.test').domain).toBe('example.test');
});
test('shows sourced job titles beside unresolved identities and escapes unsafe values',()=>{
 const data:any=buildFeatures(structuredClone(fixture));
 data.coverage.unresolved=[{target:{name:'Missing Person',title:'VP <Sales>',company:'Example & Co',linkedin_url:'https://www.linkedin.com/in/missing-person'},reason:'account_domain_mismatch'},{target:{name:'Unknown Role',linkedin_url:'javascript:alert(1)'},reason:'missing_profile'}];
 const section=renderReview(data).split('<section aria-label="Source coverage">')[1];
 expect(section).toContain('href="https://www.linkedin.com/in/missing-person"');
 expect(section).toContain('VP &lt;Sales&gt; · Example &amp; Co');
 expect(section).toContain('Job title unknown');
 expect(section).not.toContain('href="javascript:');
});

test('domain diagnostics remain visible and escape source text',()=>{
 const data=buildFeatures(structuredClone(fixture));
 data.coverage.unresolved=[{target:{name:'Target',title:'Engineer',company:'Example'},reason:'account_domain_mismatch',domain_check:{expected_domain:'example.test',profile_domain:'<script>bad</script>',status:'different_domains'}}];
 const html=renderReview(data);expect(html).toContain('Expected account: example.test');expect(html).toContain('Profile account: &lt;script&gt;bad&lt;/script&gt;');expect(html).not.toContain('Profile account: <script>');
});
