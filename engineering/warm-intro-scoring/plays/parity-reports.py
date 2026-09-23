#!/usr/bin/env python3
"""Check report payload/content parity and escaping with fictional source fixtures."""
import html,json,re,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import evaluate,score,render

def run():
    raw=json.loads((ROOT/'assets/example.json').read_text())
    rows=score.score(raw,ROOT/'vendor')
    rows[0]['connector_name']='Example </script><script>alert(1)</script> & "quoted"'
    report=evaluate.evaluate(json.loads((ROOT/'assets/evaluation-example.json').read_text()))
    report['warnings'].append('Fictional <script>alert(1)</script>')
    payload={'rows':rows,'report':report,'template':(ROOT/'assets/review.html').read_text()}
    runner="""import {renderLegacy,renderEvaluation}from'./reports';import{strictJSON}from'./strict-json';const d=await Bun.file(process.argv[2]).json();const rejected=['{\\"a\\":1,\\"a\\":2}','{\\"n\\":1e999}','{\\"x\\":NaN}'].map(x=>{try{strictJSON(x);return false}catch{return true}});console.log(JSON.stringify({legacy:renderLegacy(d.rows,d.template),evaluation:renderEvaluation(d.report),rejected}));"""
    with tempfile.NamedTemporaryFile(mode='w',suffix='.json')as inp:
        json.dump(payload,inp);inp.flush()
        with tempfile.NamedTemporaryFile(mode='w',suffix='.ts',dir=ROOT/'plays')as ts:
            ts.write(runner);ts.flush();result=json.loads(subprocess.check_output(['bun',ts.name,inp.name],text=True))
    assert all(result['rejected'])
    data=lambda s:json.loads(s.split('<script id="data" type="application/json">')[1].split('</script>')[0])
    assert data(render.render(rows))==data(result['legacy'])
    assert '</script><script>alert(1)' not in result['legacy']
    python=evaluate.html_report(report)
    for section in ['thead','tbody','ul']:
        assert re.findall(f'<{section}>(.*?)</{section}>',python,re.S)==re.findall(f'<{section}>(.*?)</{section}>',result['evaluation'],re.S),section
    embedded=lambda s:json.loads(html.unescape(s.split('<pre>')[1].split('</pre>')[0]))
    assert embedded(python)==embedded(result['evaluation'])
    assert '<script>alert(1)'not in result['evaluation']
    print('PASS: legacy report payload, evaluation tables/warnings/full report and script-escape protection; strict JSON duplicate/nonfinite rejection.')
if __name__=='__main__':run()
