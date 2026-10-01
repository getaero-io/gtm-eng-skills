"""Execute a packaged blueprint graph locally, using the Deepline CLI for every model and provider call.

Node types:
  agent        -> `deepline tools execute deeplineagent` (web-search capable) with a JSON schema built from outputSchema.
                  listMode=true runs one call per entry of listEntriesRef (the Repeat pattern), in parallel.
  code         -> the node's Python `handler(context)` runs in-process; context.get_input(name) reads mapped inputs.
  conditional  -> rules mode; the first matching rule id is chosen, otherwise the default (fallback) route.
  tool         -> `deepline tools execute <toolId>` with inputMappingConfig ({{var}} references or static values).
                  A static value '$ENV:NAME' is read from the environment at call time and never written to the run record.

Every node's inputs and outputs are written to a local run record (JSON), which replaces hosted run history.
"""
import json, os, re, subprocess, tempfile, time
from concurrent.futures import ThreadPoolExecutor

PARALLEL = int(os.environ.get('ALPHA_PARALLEL', '5'))


def deepline(tool, payload):
    """Run one Deepline tool and return its raw tool output. Raises on CLI or provider failure."""
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump(payload, f)
    try:
        env = {**os.environ, 'DEEPLINE_SKIP_SELF_UPDATE': '1'}
        p = subprocess.run(['deepline', 'tools', 'execute', tool, '--input', '@' + f.name, '--json'],
                           capture_output=True, text=True, env=env)
    finally:
        os.unlink(f.name)
    try:
        out = json.loads(p.stdout)
    except ValueError:
        raise RuntimeError(f'{tool}: unreadable CLI output: {(p.stdout + p.stderr)[:500]}')
    if p.returncode or out.get('ok') is False:
        raise RuntimeError(f'{tool}: {json.dumps(out.get("error", out))[:800]}')
    return (out.get('toolResponse') or {}).get('raw', out)


def path_get(value, path):
    if path in (None, '$'):
        return value
    for key in path[2:].split('.'):
        value = value.get(key) if isinstance(value, dict) else None
    return value


def render(template, values):
    def sub(m):
        v = values.get(m.group(1))
        return v if isinstance(v, str) else json.dumps(v)
    return re.sub(r'\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}', sub, template)


def agent_schema(spec):
    props = {k: {'type': v.get('type', 'string'), 'description': v.get('description', '')}
             for k, v in (spec.get('outputSchema') or {}).items()}
    return {'type': 'object', 'properties': props, 'required': list(props), 'additionalProperties': False}


def run_agent(spec, values):
    prompt = render(spec['agentPrompt'], values)
    raw = deepline('deeplineagent', {'prompt': prompt, 'model': spec.get('agentModel', 'openai/gpt-5.4'),
                                     'jsonSchema': agent_schema(spec), **({'maxToolCalls': spec['maxToolCalls']} if 'maxToolCalls' in spec else {})})
    obj = raw.get('extracted_json') or (raw.get('result') or {}).get('object')
    if not isinstance(obj, dict):
        raise RuntimeError(spec['name'] + ': agent returned no structured output')
    cost = (raw.get('meta') or {}).get('totalCostUsd')
    return obj, cost


class Context:
    def __init__(self, values): self.values = values
    def get_input(self, key): return self.values.get(key)


def run_code(spec, values):
    ns = {'__name__': 'node'}
    exec(compile(spec['code'], spec['name'], 'exec'), ns)
    return ns['handler'](Context(values))


def rule_matches(cond, values):
    results = []
    for item in cond.get('items', []):
        if item.get('type') == 'GroupOp':
            results.append(rule_matches(item, values)); continue
        v = values.get(item['dataPath'][0])
        op, target = item['operator'], item.get('value')
        num = isinstance(v, (int, float)) and not isinstance(v, bool) and isinstance(target, (int, float))
        results.append({'True': lambda: v is True, 'False': lambda: v is False,
                        'GreaterThan': lambda: num and v > target,
                        'LessThan': lambda: num and v < target,
                        'Equals': lambda: v == target}[op]())
    return all(results) if cond.get('combinationMode', 'And') == 'And' else any(results)


def run_tool(spec, values):
    payload = {}
    for k, m in spec['inputMappingConfig'].items():
        if m['type'] == 'reference':
            payload[k] = render(m['expression'], values)
            try: payload[k] = json.loads(payload[k]) if payload[k][:1] in '{[' else payload[k]
            except ValueError: pass
        elif isinstance(m['value'], str) and m['value'].startswith('$ENV:'):
            name = m['value'][5:]
            if not os.environ.get(name): raise RuntimeError(f'{spec["name"]}: set {name} in the environment')
            payload[k] = os.environ[name]
        else:
            payload[k] = m['value']
    nested = {}
    for k, v in payload.items():  # 'headers|x-api-key' -> {'headers': {'x-api-key': ...}}
        head, _, rest = k.partition('|')
        if rest: nested.setdefault(head, {})[rest] = v
        else: nested[k] = v
    try:
        return deepline(spec['toolId'], nested)
    except RuntimeError as e:  # provider misses are data for the next code node, not a crash
        return {'ok': False, 'error': str(e)}


def edge_open(edge, done, routes):
    src = edge['sourceNode'][5:]
    if src not in done or routes.get(src) is None:
        return False
    if 'ruleId' in edge:
        return routes.get(src) == edge['ruleId']
    if edge.get('isDefaultRoute'):
        return routes.get(src) == '__default__'
    return True


def execute(graph, trigger_inputs, record_path=None, log=print):
    outputs, routes, record = {'trigger': trigger_inputs}, {'trigger': True}, {'started_at': time.time(), 'nodes': [], 'cost_usd': 0.0}
    done, pending = {'trigger'}, list(graph['nodes'])
    while pending:
        ready = [n for n in pending if all(e['sourceNode'][5:] in done for e in n['spec'].get('incomingEdges', []))]
        if not ready:
            break
        for node in ready:
            pending.remove(node)
            key, spec = node['key'], node['spec']
            done.add(key)
            if not all(edge_open(e, done, routes) for e in spec.get('incomingEdges', [])):
                routes[key] = None  # skipped branch: downstream nodes stay skipped too
                continue
            values = {name: path_get(outputs.get((p.get('sourceNodeId') or 'NODE:')[5:]), p.get('sourcePath'))
                      for name, p in spec.get('inputSchema', {}).get('properties', {}).items() if p.get('sourceNodeId')}
            log(f'-> {spec["name"]}')
            kind = spec['nodeType']
            if kind == 'agent' and spec.get('listMode'):
                ref = spec['listEntriesRef']
                items = path_get(outputs[ref['sourceNodeId'][5:]], ref['path']) or []

                def one(item):
                    try:
                        return run_agent(spec, {**values, '__item': item})
                    except RuntimeError as e:
                        return {'_error': str(e)}, None
                results = list(ThreadPoolExecutor(PARALLEL).map(one, items))
                out = [r for r, _ in results]
                record['cost_usd'] += sum(c or 0 for _, c in results)
            elif kind == 'agent':
                obj, cost = run_agent(spec, values)
                out = {**obj, 'structuredOutputs': obj}
                record['cost_usd'] += cost or 0
            elif kind == 'code':
                out = run_code(spec, values)
            elif kind == 'tool':
                out = run_tool(spec, values)
            elif kind == 'conditional':
                rules = spec['rulesConditionalConfig']['rules']
                routes[key] = next((r['id'] for r in rules if rule_matches(r['condition'], values)), '__default__')
                out = {'route': routes[key]}
            else:
                raise ValueError('Unsupported node type ' + kind)
            outputs[key] = out
            routes.setdefault(key, True)
            record['nodes'].append({'key': key, 'name': spec['name'], 'inputs': values, 'outputs': out})
            if record_path:
                save(record_path, record)
    record['finished_at'] = time.time()
    record['outputs'] = outputs
    if record_path:
        save(record_path, record)
    return outputs, record


def save(path, value):
    from pathlib import Path
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, default=str))
