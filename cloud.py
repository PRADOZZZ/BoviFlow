"""Serverless demo: replay validated commands, not untrusted SQLite files.
Optional shared Supabase journal uses compare-and-swap. Demo data only.
"""
import hashlib, json, math, os, secrets, tempfile, time, urllib.request, urllib.error
from pathlib import Path
from core import Store, Conflict
from simulator import simulate, benchmark
from integrations import executive_summary
MAX_ACTIONS=200
MUTATIONS={'action','claim','demo-signal','settings','reset'}
READS={'state','export','diagnostic','simulate','benchmark','openapi.json'}

def shared_config():
    url=os.getenv('SUPABASE_URL','').rstrip('/'); key=os.getenv('SUPABASE_SERVICE_ROLE_KEY',''); token=os.getenv('BOVIFLOW_TOKEN','')
    if any((url,key)) and not (url and key and token): raise RuntimeError('Configure SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY e BOVIFLOW_TOKEN juntos.')
    if url and not url.startswith('https://'): raise RuntimeError('SUPABASE_URL deve usar HTTPS.')
    return (url,key) if url else None

def fresh(): return {'seed':secrets.token_hex(12),'started':time.time(),'actions':[]}
def numeric(x): return type(x) in (int,float) and math.isfinite(x)
def validate(j):
    if not isinstance(j,dict) or set(j)!= {'seed','started','actions'}: raise ValueError('Sessão demonstrativa inválida.')
    seed=j['seed']; start=j['started']; actions=j['actions']; now=time.time()
    if not isinstance(seed,str) or len(seed)!=24 or any(c not in '0123456789abcdef' for c in seed): raise ValueError('Sessão inválida.')
    if not numeric(start) or not 0<start<=now+60 or not isinstance(actions,list) or len(actions)>MAX_ACTIONS: raise ValueError('Sessão inválida ou cheia.')
    prev=start
    for a in actions:
        if not isinstance(a,list) or len(a)!=3 or a[1] not in MUTATIONS-{'reset'} or not numeric(a[0]) or not prev<=a[0]<=now+60 or not isinstance(a[2],dict): raise ValueError('Histórico inválido.')
        prev=a[0]
    return j

def apply(store,op,b):
    if op=='action': return store.action(b.get('id'),b.get('action'),b.get('version'),b.get('actor','equipe'))
    if op=='claim': return store.claim_next(b.get('zone','Todos'))
    if op=='demo-signal': return store.demo_signal()
    if op=='settings': store.configure(b.get('goal'),b.get('demand')); return store.snapshot()
    if op=='state': return store.snapshot()
    if op=='export': return {'csv':store.export()}
    if op=='diagnostic':
        if type(b.get('external',False)) is not bool: raise ValueError('external deve ser booleano')
        shared=bool(shared_config()); result=executive_summary(store.snapshot(),b.get('external',False) and shared)
        if not shared:
            result['external_available']=False
            if b.get('external'): result['notice']='IA externa desativada na demonstração isolada. Diagnóstico local preservado.'
        return result
    raise ValueError('Operação inválida')

def run(j,op,b):
    if op=='reset': j=fresh(); op='state'
    j=validate(j if j is not None else fresh())
    if op=='simulate': return simulate(b),j
    if op=='benchmark': return benchmark(b),j
    if op=='openapi.json': return json.loads((Path(__file__).parent/'docs/openapi.json').read_text()),j
    with tempfile.TemporaryDirectory(prefix='bovi-') as tmp:
        ts=[j['started']]; seed=j['seed']; clock=lambda:ts[0]
        version=lambda i:int.from_bytes(hashlib.sha256(f'{seed}:{i}'.encode()).digest()[:6],'big')
        store=Store(Path(tmp)/'demo.db',clock=clock,seed_version=version)
        for stamp,action,params in j['actions']:
            ts[0]=stamp; apply(store,action,params)
        ts[0]=max(time.time(),ts[0]);
        if op in MUTATIONS:
            if len(j['actions'])>=MAX_ACTIONS: raise Conflict('Limite de 200 eventos da demonstração; exporte e reinicie o cenário.')
            # Keep only fields that the API actually consumes.
            keys={'action':('id','action','version','actor'),'claim':('zone',),'demo-signal':(),'settings':('goal','demand')}[op]
            b={k:b[k] for k in keys if k in b}
        result=apply(store,op,b)
        if op in MUTATIONS: j={**j,'actions':j['actions']+[[ts[0],op,b]]}
        return result,j

def supabase_request(config,method,path,body=None,prefer=None):
    url,key=config; headers={'apikey':key,'Authorization':'Bearer '+key,'Content-Type':'application/json'}
    if prefer: headers['Prefer']=prefer
    req=urllib.request.Request(url+'/rest/v1/boviflow_demo'+path,data=json.dumps(body).encode() if body is not None else None,headers=headers,method=method)
    with urllib.request.urlopen(req,timeout=8) as r: return json.load(r)

def shared_run(config,op,b):
    rows=supabase_request(config,'GET','?id=eq.1&select=revision,journal')
    if len(rows)!=1: raise RuntimeError('Execute o SQL de instalação do Supabase.')
    row=rows[0]; j=row['journal']; result,new=run(j,op,b)
    if j is None or op in MUTATIONS:
        updated=supabase_request(config,'PATCH',f"?id=eq.1&revision=eq.{int(row['revision'])}",{'revision':row['revision']+1,'journal':new},'return=representation')
        if not updated: raise Conflict('Outra sessão atualizou os dados; recarregue e tente novamente.')
    return result

def dispatch(envelope,config):
    if not isinstance(envelope,dict): raise ValueError('Objeto JSON obrigatório')
    op=envelope.get('op'); b=envelope.get('body',{})
    if not isinstance(op,str) or op not in MUTATIONS|READS or not isinstance(b,dict): raise ValueError('Operação inválida')
    if config: return {'result':shared_run(config,op,b),'shared':True}
    result,j=run(envelope.get('journal'),op,b)
    return {'result':result,'journal':j,'shared':False}
