"""Optional external AI; only synthetic demonstration aggregates, never camera images."""
import os, json, time, threading, urllib.request, urllib.error
_lock=threading.Lock(); _last=0

def executive_summary(snapshot, external=False):
    a=snapshot['alerts']; m=snapshot['metrics']; c=snapshot['counts']
    worst=max(snapshot['zones'],key=lambda z: snapshot['zones'][z]['dirty']+snapshot['zones'][z]['cleaning'])
    text=(f"Há {c['dirty']} mesas aguardando limpeza e {a['overdue']} ciclos acima da meta. "
          f"O salão {worst} tem o maior número de mesas aguardando ou em limpeza. "
          + ('Priorize '+snapshot['priority'][0]['id']+' pela regra operacional. ' if snapshot['priority'] else 'Não há limpeza pendente. ')
          + (f"A amostra inclui {m['n']} ciclos concluídos; valide em campo antes de alterar a equipe." if m['n'] else 'Ainda não há ciclos concluídos para avaliar desempenho.'))
    fallback={'source':'regras locais','text':text,'external_available':bool(os.getenv('OPENAI_API_KEY') and os.getenv('OPENAI_MODEL') and snapshot['mode']=='demo')}
    if not external: return fallback
    if not fallback['external_available']: return {**fallback,'notice':'API externa não configurada ou indisponível neste modo.'}
    global _last
    with _lock:
        now=time.monotonic()
        if _last and now-_last<60: return {**fallback,'notice':'Limite de uma consulta externa por minuto; diagnóstico local exibido.'}
        _last=now
    payload={'model':os.environ['OPENAI_MODEL'],'store':False,'max_output_tokens':500,'instructions':'Responda em português brasileiro, em até 100 palavras. Analise somente os indicadores sintéticos recebidos. Não invente números, não prometa ganhos e diferencie hipótese de resultado. Sugira uma ação operacional e uma forma de validar. Não identifique pessoas.', 'input':json.dumps({'modo':'simulacao','contagens':c,'alertas':a,'metricas':m,'por_salao':snapshot['by_zone']},ensure_ascii=False)}
    req=urllib.request.Request('https://api.openai.com/v1/responses',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+os.environ['OPENAI_API_KEY'],'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=12) as r: result=json.load(r)
        output='\n'.join(p['text'] for item in result.get('output',[]) if item.get('type')=='message' for p in item.get('content',[]) if p.get('type')=='output_text' and isinstance(p.get('text'),str)).strip()
        if not output: raise ValueError('empty')
        return {**fallback,'source':'OpenAI Responses API','text':output[:4000]}
    except (OSError,ValueError,KeyError,TypeError): return {**fallback,'notice':'Falha ou limite da API externa. Diagnóstico local preservado.'}
