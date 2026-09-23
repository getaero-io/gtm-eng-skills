/** bun report-cli.ts input.json output.html [weights.json] */
import {readFileSync,writeFileSync} from 'node:fs';
import {renderReview} from './report';
const [input,output,config]=process.argv.slice(2);
if(!input||!output)throw new Error('Usage: bun report-cli.ts input.json output.html [weights.json]');
const data=JSON.parse(readFileSync(input,'utf8'));
const html=renderReview(data,config?JSON.parse(readFileSync(config,'utf8')):undefined);
writeFileSync(output,html,{flag:'wx',mode:0o600});
console.log(JSON.stringify({paths:data.paths.length,bytes:Buffer.byteLength(html),output}));
