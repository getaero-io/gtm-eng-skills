import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';

const dir=path.dirname(fileURLToPath(import.meta.url));
const esc=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;');
const nodes=[
  ['find','Find five experts','One record per person','#e7f5ff'],
  ['agree','Agree on work','Check fit, time and terms','#fff4e6'],
  ['work','Get useful work','Review the result','#ebfbee'],
  ['return','Invite them back','Offer a suitable next task','#ebfbee'],
];
const elements=[];
function base(id,type,x,y,width,height){return {id,type,x,y,width,height,angle:0,strokeColor:'#343a40',backgroundColor:'transparent',fillStyle:'solid',strokeWidth:2,strokeStyle:'solid',roughness:1,opacity:100,groupIds:[],frameId:null,roundness:null,seed:100+elements.length,version:1,versionNonce:1000+elements.length,isDeleted:false,boundElements:null,updated:1,link:null,locked:false};}
function text(id,value,x,y,w,size=22){elements.push({...base(id,'text',x,y,w,size*1.3),text:value,fontSize:size,fontFamily:1,textAlign:'center',verticalAlign:'top',containerId:null,originalText:value,autoResize:true,lineHeight:1.25});}
text('title','Start with five experts',40,35,1160,36);
text('subtitle','Learn the process. Then automate what repeats.',40,90,1160,23);
nodes.forEach(([id,title,sub,color],i)=>{
  const x=40+i*300;
  elements.push({...base(id,'rectangle',x,180,260,110),backgroundColor:color,roundness:{type:3}});
  text(id+'-title',title,x+10,204,240,25);
  text(id+'-sub',sub,x+10,249,240,17);
  if(i<3)elements.push({...base(id+'-arrow','arrow',x+270,235,25,0),points:[[0,0],[25,0]],startBinding:null,endBinding:null,lastCommittedPoint:null,startArrowhead:null,endArrowhead:'arrow',elbowed:false});
});
elements.push({...base('learn-loop','arrow',470,305,600,70),strokeColor:'#868e96',strokeStyle:'dashed',points:[[600,0],[600,70],[0,70],[0,0]],startBinding:null,endBinding:null,lastCommittedPoint:null,startArrowhead:null,endArrowhead:'arrow',elbowed:false});
text('learn-label','Use what you learned',560,395,420,21);
text('metric','Goal: useful first contributions and repeat contributions',40,460,1160,22);
await fs.writeFile(path.join(dir,'expert-flow.excalidraw'),JSON.stringify({type:'excalidraw',version:2,source:'https://excalidraw.com',elements,appState:{gridSize:null,viewBackgroundColor:'#ffffff'},files:{}},null,2));

// A faithful geometric preview of the editable scene; it is not an Excalidraw renderer export.
let sketch='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1240 530"><rect width="1240" height="530" fill="white"/><defs><marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="none" stroke="#495057"/></marker></defs>';
for(const e of elements){
 if(e.type==='rectangle')sketch+=`<rect x="${e.x}" y="${e.y}" width="${e.width}" height="${e.height}" rx="12" fill="${e.backgroundColor}" stroke="#495057" stroke-width="2"/>`;
 if(e.type==='text')sketch+=`<text x="${e.x+e.width/2}" y="${e.y+e.fontSize}" text-anchor="middle" font-family="Arial,sans-serif" font-size="${e.fontSize}" fill="#343a40">${esc(e.text)}</text>`;
 if(e.type==='arrow')sketch+=`<polyline points="${e.points.map(([x,y])=>[e.x+x,e.y+y].join(',')).join(' ')}" fill="none" stroke="${e.strokeColor}" stroke-width="2" ${e.strokeStyle==='dashed'?'stroke-dasharray="7 7"':''} marker-end="url(#a)"/>`;
}
sketch+='</svg>';
await fs.writeFile(path.join(dir,'expert-flow-sketch-preview.svg'),sketch);

const template=await fs.readFile(path.join(dir,'expert-architecture.html'),'utf8');
const architecture=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 400"><defs><marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto"><polygon points="0 0,10 3.5,0 7" fill="#64748b"/></marker><pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0 L0 0 0 40" fill="none" stroke="#1e293b" stroke-width=".5"/></pattern></defs><rect width="1000" height="400" fill="#020617"/><rect width="1000" height="400" fill="url(#grid)"/><g fill="none" stroke="#64748b" stroke-width="2" marker-end="url(#arrowhead)"><path d="M280 190 H380"/><path d="M620 190 H720"/><path d="M840 250 V330 H160 V250"/></g><text x="500" y="350" text-anchor="middle" fill="#94a3b8" font-size="16">Results improve the next decision</text>${[
 [40,'Your expert records','Experience, availability, results','#22d3ee','rgba(8,51,68,.4)'],
 [380,'Deepline Plays','Research, check, route, follow up','#34d399','rgba(6,78,59,.4)'],
 [720,'Your tools','Email, tasks and payments','#94a3b8','rgba(30,41,59,.5)']
 ].map(([x,title,sub,stroke,fill])=>`<rect x="${x}" y="130" width="240" height="120" rx="8" fill="#0f172a"/><rect x="${x}" y="130" width="240" height="120" rx="8" fill="${fill}" stroke="${stroke}" stroke-width="1.5"/><text x="${x+120}" y="175" text-anchor="middle" fill="white" font-size="20">${title}</text><text x="${x+120}" y="210" text-anchor="middle" fill="#94a3b8" font-size="11">${sub}</text>`).join('')}<text x="500" y="60" text-anchor="middle" fill="#cbd5e1" font-size="18">You define the rules. The coding agent builds the Plays.</text></svg>`;
let html=template.replaceAll('[PROJECT NAME]','Expert workflow').replace('[Subtitle description]','How the system fits together. Proposed architecture.');
html=html.replace(/<svg xmlns="http:\/\/www.w3.org\/2000\/svg" viewBox="0 0 1000 400">[\s\S]*?<\/svg>/,architecture);
html=html.replace(/    <!-- Info Cards -->[\s\S]*?    <!-- Footer -->/,'    <!-- Footer -->');
// Some template versions label the card region differently.
html=html.replace(/    <div class="cards">[\s\S]*?    <!-- Footer -->/,'    <!-- Footer -->');
html=html.replace('[Project Name] • [Additional metadata]','GitHub stores the workflow code. Deepline runs it.');
html=html.split('\n').map(line=>line.trimEnd()).join('\n');
await fs.writeFile(path.join(dir,'expert-architecture.html'),html);
const browser=await chromium.launch({headless:true});
try{
 const page=await browser.newPage({viewport:{width:1280,height:750},deviceScaleFactor:2});
 await page.goto('file://'+path.join(dir,'expert-architecture.html'));
 await page.locator('#report-container').screenshot({path:path.join(dir,'expert-architecture.png')});
 await page.setContent(sketch);
 await page.locator('svg').screenshot({path:path.join(dir,'expert-flow-sketch-preview.png')});
 const d2=await fs.readFile(path.join(dir,'expert-flow-d2.svg'),'utf8');
 const gallery=`<!doctype html><html><head><meta charset="utf-8"><title>Three ways to explain the expert workflow</title><style>body{font:18px Arial,sans-serif;color:#222;background:#fafaf7;max-width:1200px;margin:50px auto;padding:0 30px}h1{font-size:36px}section{margin:48px 0;padding-top:20px;border-top:1px solid #ccc}svg{width:100%;height:auto}a{color:#155d66}p{max-width:780px;line-height:1.5}.dark{background:#020617;padding:20px;border-radius:8px}</style></head><body><h1>Start with five experts. Then automate.</h1><p>Same idea, three views. Use the first on the page; keep the others for editing and implementation.</p><section><h2>D2 · the clearest overview</h2><p>Four steps and a feedback loop. The diagram source can change with the code.</p>${d2}<a href="expert-flow.d2">Diagram source</a></section><section><h2>Excalidraw · the editable sketch</h2><p>Useful when you want to change the flow in a discussion. This is a geometric preview of the editable file.</p>${sketch}<a href="expert-flow.excalidraw">Editable Excalidraw file</a></section><section><h2>Architecture · the system view</h2><p>Shows where records, Plays and tools fit. Keep this below the main explanation.</p><div class="dark">${architecture}</div><a href="expert-architecture.html">Open the architecture view and exports</a></section></body></html>`;
 await fs.writeFile(path.join(dir,'diagram-options.html'),gallery);
 await page.setContent(gallery);
 await page.screenshot({path:path.join(dir,'diagram-options.png'),fullPage:true});
}finally{await browser.close();}
console.log('Created three diagram options and editable source.');
