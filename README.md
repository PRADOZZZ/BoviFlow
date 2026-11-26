# BoviFlow 4.0 — edição Vercel
Proposta independente para o Hackathon FMU × Bovinu'S, unidade Augusta. **Dados sintéticos; não é um sistema oficial implantado.**

## Publicar rapidamente (sem instalar Python, sem banco externo)
1. Extraia o ZIP. A pasta raiz é `BoviFlow` (onde está `vercel.json`).
2. Crie um repositório GitHub, de preferência privado se não houver autorização de publicação da marca. Envie **todo o conteúdo** de `BoviFlow`, inclusive `api/`, `public/`, `core.py`, `cloud.py`, `simulator.py`, `integrations.py`, `docs/` e `vercel.json`. Não envie somente `public/`.
3. Em https://vercel.com/new importe o repositório. Selecione a raiz que contém `vercel.json` (normalmente `./`; se o repositório contém a pasta externa BoviFlow, selecione `BoviFlow`). Framework Preset: **Other**. Build Command: em branco. Output Directory: `public`. Não informe comando de instalação ou servidor de desenvolvimento. Clique Deploy.
4. Abra a URL atribuída pela Vercel. Teste `/api/session` em outra aba: GET deve responder `{"status":"ok","shared":false,"mode":"demo"}`. `/staff` abre o painel dos funcionários. O site usa POST `/api/session` para operações reais processadas pelo Python serverless.
5. Em duas abas do **mesmo perfil e navegador**, registre uma saída, inicie e conclua a limpeza, e recarregue a página. Teste o simulador e a exportação. O estado demonstrativo fica no localStorage; navegadores/dispositivos diferentes têm dados independentes. Navegadores modernos com Web Locks serializam as ações das abas; se o recurso não existir, evite ações simultâneas entre abas. A atualização usa polling de cinco segundos e eventos de armazenamento. O cenário tem limite de 200 ações; exporte e reinicie antes de atingir o limite. Não é banco operacional.
6. Envie o link HTTPS aos jurados somente depois de testar em aba anônima (e confirmar autorização para compartilhar a marca/material). Se o acesso estiver protegido pela Vercel, conceda acesso aos avaliadores ou use o link de compartilhamento autorizado.

## Opcional: Supabase para sincronização de computadores e celulares
- Crie projeto Supabase e execute `supabase/setup.sql` no SQL Editor. A tabela tem uma única sessão demonstrativa compartilhada, RLS habilitada e sem acesso anônimo/autenticado direto.
- Vercel > projeto > Settings > Environment Variables: adicione `SUPABASE_URL` (URL HTTPS do projeto), `SUPABASE_SERVICE_ROLE_KEY` (chave de servidor legada service_role; nunca coloque no frontend ou GitHub) e `BOVIFLOW_TOKEN` (senha forte de acesso à demo). Redepploy. Não use dados reais; o cenário pode ser reiniciado por qualquer participante com o código de acesso. Não há contas/roles de produção.
- Acesse `/api/session` para confirmar `shared:true`. No dashboard e painel mobile, informe o mesmo código quando solicitado. A API usa revisão compare-and-swap para evitar sobrescritas concorrentes. Teste em dois aparelhos. O limite de 200 ações também vale neste modo. O SQL e o cliente REST foram preparados, mas a integração foi testada apenas com respostas simuladas; é necessário validar com a sua conta.
- IA externa opcional apenas no modo compartilhado: configure `OPENAI_API_KEY` e `OPENAI_MODEL` como variáveis de servidor. Há custos potenciais e o limite local de chamadas não é global entre instâncias serverless. Não é necessário para a apresentação.
- A webcam física do servidor não está disponível na Vercel; o laboratório conserva eventos simulados identificados. A visão experimental original continua no modo local (`vision.py`).

## Estrutura
`public/` contém os arquivos estáticos da versão cloud; `api/session.py` é a função serverless; `cloud.py` reconstitui uma base SQLite temporária a partir do histórico validado de ações (não aceita arquivos SQLite do cliente). A demonstração isolada não utiliza estado persistente no filesystem da Vercel. Supabase opcional armazena o histórico e sua revisão. `app.py`, `static/`, `iniciar.bat` preservam o modo local anterior; para ele, Python 3.10+ é necessário. `docs/README-LOCAL-V3.md` documenta essa versão local. O contrato cloud é descrito abaixo; `docs/openapi.json` descreve as operações originais locais, não rotas individuais da Vercel.

## API cloud
GET `/api/session`: diagnóstico/configuração pública sem dados.
POST `/api/session` JSON: `{"op":"state","body":{},"journal":null}`. Resposta: `{result, journal, shared:false}` ou `{result, shared:true}`. No modo isolado, reenvie `journal` retornado na próxima requisição. Operações: `state`, `action`, `claim`, `demo-signal`, `settings`, `reset`, `simulate`, `benchmark`, `diagnostic`, `export`, `openapi.json`. Em modo protegido envie `Authorization: Bearer <código>`. A resposta de export contém `result.csv`.

## Testes
`python -m unittest discover -s tests -v` (32 testes anteriores + 7 cloud, total 39). `node --check public/static/app.js` valida sintaxe. `tests/browser_cloud.py` usa Chromium e ponte HTTP para o handler real, com armazenamento simulado: validou 90 mesas, ciclo de limpeza, restauração em outra página e largura mobile. A navegação direta foi bloqueada pela política administrativa do ambiente. Não foi realizado deploy real na Vercel nem teste com Supabase/OpenAI reais; confira os passos acima antes de enviar. Relatórios antigos em docs são históricos.
