import deepline from 'deepline';
import { roleFit, emailFit } from './enrollment-policy';
export const config = { name:'erm-qualify-candidate-v1', description:'Check current professional role and strict-domain verified work email for recruiting; no expert or license assessment.', billing:{maxCreditsPerRun:2} };
export default async function(input:{profile:string;domain:string;vertical:string}) {
  const profile = await deepline.runPlay<any>('current-role','prebuilt/person-linkedin-to-company',{linkedin_url:input.profile,profile_depth:'main'},{description:'Verify current employer and role from the profile'});
  if (!roleFit(input,profile)) return {status:'held',reason:'Current role, employer or identity requires review',profile};
  const email = await deepline.runPlay<any>('verified-email','prebuilt/person-to-email',{
    linkedin_url:input.profile,first_name:profile.first_name,last_name:profile.last_name,
    domain:input.domain,strict_domain:'strict',alternate_domains:[],validation:'kitt',confirm_catch_all:false,
    staleAfterSeconds:86400,
  },{description:'Resolve a verified email on the expected employer domain'});
  if (!emailFit(input.domain,email)) return {status:'held',reason:'No verified work email on expected employer domain',profile,email};
  return {status:'qualified',reason:'Current-role match and verified employer email',profile,email};
}
