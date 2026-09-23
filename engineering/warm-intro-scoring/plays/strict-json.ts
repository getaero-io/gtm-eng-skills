/** Parse JSON without accepting duplicate object keys or nonfinite numbers. */
export function strictJSON(text:string):any {
 let i=0;
 const space=()=>{while(i<text.length&&/\s/.test(text[i]))i++;};
 function quoted():string {const start=i++;while(i<text.length){if(text[i]==='\\'){i+=2;continue;}if(text[i++]==='"')return JSON.parse(text.slice(start,i));}throw new SyntaxError('Unclosed JSON string');}
 function value():void {
  space();const c=text[i];if(c==='"'){quoted();return;}
  if(c==='{'){i++;space();const keys=new Set();if(text[i]==='}'){i++;return;}while(i<text.length){space();if(text[i]!=='"')throw new SyntaxError('Object key required');const k=quoted();if(keys.has(k))throw new SyntaxError('Duplicate JSON key');keys.add(k);space();if(text[i++]!==':')throw new SyntaxError('Colon required');value();space();const end=text[i++];if(end==='}')return;if(end!==',')throw new SyntaxError('Comma required');}throw new SyntaxError('Unclosed JSON object');}
  if(c==='['){i++;space();if(text[i]===']'){i++;return;}while(i<text.length){value();space();const end=text[i++];if(end===']')return;if(end!==',')throw new SyntaxError('Comma required');}throw new SyntaxError('Unclosed JSON array');}
  const start=i;while(i<text.length&&!/[\s,}\]]/.test(text[i]))i++;if(i===start)throw new SyntaxError('JSON value required');JSON.parse(text.slice(start,i));
 }
 value();space();if(i!==text.length)throw new SyntaxError('Trailing JSON data');const result=JSON.parse(text);
 const check=(v:any)=>{if(typeof v==='number'&&!Number.isFinite(v))throw new SyntaxError('Nonfinite JSON number');if(v&&typeof v==='object')Object.values(v).forEach(check);};check(result);return result;
}
