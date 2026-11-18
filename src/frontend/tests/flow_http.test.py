"""Testes HTTP do fluxo Node-RED (JSON real executado pelo emulador): rotas, CORS, OPTIONS, validação, 503, duplicatas.
Uso: python3 tests/flow_http.test.py"""
import json, sys
from _helpers import *

OK, BAD = 'http://127.0.0.1:5500', 'http://evil.example'
flow = json.load(open(FLOW_NEW))

print('Estrutura do fluxo (análise dos nós HTTP In)')
ins = [n for n in flow if n['type'] == 'http in']
print('  rotas:', ', '.join(f"{n['method'].upper()} {n['url']}" for n in ins))
USED = [('get','/api/v1/telemetria'),('post','/api/v1/rooms/:room_id/ac/cut'),('post','/api/v1/rooms/:room_id/ac/on'),('post','/api/v1/comando-carga'),('post','/api/v1/mensagem')]
check('o fluxo tem as 5 rotas usadas pelo front-end (telemetria, ac cut/on, carga, mensagem)', all(r in [(n['method'], n['url']) for n in ins] for r in USED))
check('nenhum nó http in com método OPTIONS (o Node-RED não registra)', all(n['method'] in ('get','post','put','delete','patch') for n in ins))
check('sem rotas duplicadas (método+URL)', len({(n['method'], n['url']) for n in ins}) == len(ins))
check('uma única resposta HTTP e um único nó de CORS', sum(n['type']=='http response' for n in flow)==1 and sum(n.get('name','').startswith('CORS') for n in flow)==1)
ids = {n['id'] for n in flow}; check('fios do fluxo consistentes', all(w in ids for n in flow for ws in n.get('wires', []) for w in ws))

with Env(web=False):
    print('\nGET /api/v1/telemetria')
    s, h, j = jreq('GET', '/api/v1/telemetria', {'Origin': OK, 'Accept': 'application/json'})
    check('200 + campos usados pela interface', s == 200 and all(k in j for k in ('ocupada','temperatura','umidade','potencia_w','energia_kwh','ac','carga')) and 'ligada' in j['carga'] and 'modo' in j['carga'])
    check('Access-Control-Allow-Origin = origem do Live Server', h.get('access-control-allow-origin') == OK, str(h.get('access-control-allow-origin')))
    s, h, _ = jreq('GET', '/api/v1/telemetria', {'Origin': 'http://localhost:5500'})
    check('também permite http://localhost:5500', h.get('access-control-allow-origin') == 'http://localhost:5500')
    s, h, _ = jreq('GET', '/api/v1/telemetria', {'Origin': BAD})
    check('origem não listada NÃO recebe Allow-Origin', 'access-control-allow-origin' not in h)

    print('\nPOST com cabeçalhos CORS (requisição simples, text/plain)')
    T = {'Origin': OK, 'Content-Type': 'text/plain;charset=UTF-8'}
    s, h, j = jreq('POST', '/api/v1/rooms/101/ac/cut', T, json.dumps({'room_id': 101}))
    check('POST ac/cut 200', s == 200 and j.get('ok') is True)
    check('POST ac/cut tem Allow-Origin/Methods/Headers', all(k in h for k in ('access-control-allow-origin','access-control-allow-methods','access-control-allow-headers')))
    check('telemetria reflete AC cortado', jreq('GET','/api/v1/telemetria')[2]['ac']['ligado'] is False)
    print('\nPOST /api/v1/rooms/101/ac/on (ligar o ar-condicionado)')
    s, h, j = jreq('POST', '/api/v1/rooms/101/ac/on', T, json.dumps({'room_id': 101}))
    check('POST ac/on 200 e resposta "ligado"', s == 200 and j.get('ok') is True and j.get('ac') == 'ligado')
    check('POST ac/on tem Allow-Origin/Methods/Headers', h.get('access-control-allow-origin') == OK and 'access-control-allow-methods' in h and 'access-control-allow-headers' in h)
    t = jreq('GET', '/api/v1/telemetria')[2]; check('telemetria reflete AC ligado e potência volta a subir', t['ac']['ligado'] is True and t['potencia_w'] > 1000)
    check('ac/cut continua funcionando depois (ciclo desligar → ligar → desligar)', jreq('POST', '/api/v1/rooms/101/ac/cut', T, '{}')[0] == 200 and jreq('GET', '/api/v1/telemetria')[2]['ac']['ligado'] is False)
    check('ac/on sem corpo também funciona', jreq('POST', '/api/v1/rooms/101/ac/on', {'Origin': OK})[0] == 200)
    check('ac/on em sala inexistente → 404 com CORS', (lambda r: r[0] == 404 and r[1].get('access-control-allow-origin') == OK)(jreq('POST', '/api/v1/rooms/999/ac/on', T, '{}')))
    jreq('POST', '/api/v1/rooms/101/ac/cut', T, '{}')
    print('\nPOST no formato que o front-end envia AGORA (application/x-www-form-urlencoded)')
    F = {'Origin': OK, 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'}
    s, h, j = jreq('POST', '/api/v1/rooms/101/ac/on', F, 'room_id=101'); check('ac/on (form) 200 com CORS', s == 200 and j['ac'] == 'ligado' and h.get('access-control-allow-origin') == OK)
    s, h, j = jreq('POST', '/api/v1/rooms/101/ac/cut', F, 'room_id=101'); check('ac/cut (form) 200', s == 200 and j['ac'] == 'cortado')
    s, h, j = jreq('POST', '/api/v1/comando-carga', F, 'comando=AUTO'); check('comando-carga (form) 200', s == 200 and j['modo'] == 'AUTO')
    s, h, j = jreq('POST', '/api/v1/mensagem', F, 'mensagem=Aten%C3%A7%C3%A3o%3A+feche+a+porta+%26+janela')
    check('mensagem (form) 200, acentos e símbolos preservados', s == 200 and j['exibindo'] == 'Atenção: feche a porta & janela' and emu('stats')['state']['oled'] == 'Atenção: feche a porta & janela', str(j))
    check('mensagem (form) vazia → 400 com o motivo no corpo', (lambda r: r[0] == 400 and 'erro' in r[2])(jreq('POST', '/api/v1/mensagem', F, 'mensagem=')))
    check('mensagem (form) com 64 caracteres → 200; com 65 → 400', jreq('POST', '/api/v1/mensagem', F, 'mensagem=' + 'x' * 64)[0] == 200 and jreq('POST', '/api/v1/mensagem', F, 'mensagem=' + 'x' * 65)[0] == 400)
    jreq('POST', '/api/v1/comando-carga', F, 'comando=ON')
    print('\nPOST comando-carga')
    for cmd in ('ON', 'OFF', 'AUTO'):
        s, h, j = jreq('POST', '/api/v1/comando-carga', T, json.dumps({'comando': cmd}))
        check(f'comando-carga {cmd} (text/plain → Buffer)', s == 200 and j['modo'] == cmd and h.get('access-control-allow-origin') == OK)
    s, h, j = jreq('POST', '/api/v1/comando-carga', {'Origin': OK, 'Content-Type': 'application/json'}, json.dumps({'comando': 'ON'}))
    check('comando-carga também aceita application/json', s == 200 and j['modo'] == 'ON')
    print('\nModo da carga: ON / OFF / AUTO refletidos na telemetria (estado EFETIVO + potência)')
    reset(); jreq('GET', '/api/v1/telemetria')
    tel = lambda: jreq('GET', '/api/v1/telemetria', {'Origin': OK})[2]
    cmd = lambda c: jreq('POST', '/api/v1/comando-carga', T, json.dumps({'comando': c}))
    check('estado inicial: modo ON, carga energizada', tel()['carga'] == {'modo': 'ON', 'ligada': True})
    s, h, j = cmd('OFF'); check('resposta do comando já informa o estado efetivo (OFF → carga cortada)', s == 200 and j['carga'] == {'modo': 'OFF', 'ligada': False})
    t = tel(); check('OFF: telemetria com carga cortada e potência < 500 W', t['carga'] == {'modo': 'OFF', 'ligada': False} and t['potencia_w'] < 500, str(t['potencia_w']))
    check('OFF não altera a chave do ar-condicionado (continua "ligado")', t['ac']['ligado'] is True)
    s, h, j = cmd('ON'); t = tel(); check('ON: carga energizada e potência > 1000 W', j['carga']['ligada'] is True and t['carga']['ligada'] is True and t['potencia_w'] > 1000, str(t['potencia_w']))
    s, h, j = cmd('AUTO'); t = tel(); check('AUTO com sala vazia: carga cortada', j['carga'] == {'modo': 'AUTO', 'ligada': False} and t['carga']['ligada'] is False and t['potencia_w'] < 500)
    emu('inject/cs_inj_occ'); t = tel(); check('AUTO com sala ocupada: carga energizada e potência alta', t['ocupada'] is True and t['carga'] == {'modo': 'AUTO', 'ligada': True} and t['potencia_w'] > 1000)
    emu('inject/cs_inj_occ'); check('AUTO: sala volta a ficar vazia → carga cortada de novo', tel()['carga']['ligada'] is False)
    cmd('ON'); jreq('POST', '/api/v1/rooms/101/ac/cut', T, '{}'); t_ac_off = tel()
    check('potência reage ao AC com a carga energizada (AC cortado: < 800 W)', t_ac_off['potencia_w'] < 800, str(t_ac_off['potencia_w']))
    jreq('POST', '/api/v1/rooms/101/ac/on', T, '{}')
    print('\nConsumo acumulado (kWh) coerente')
    cmd('ON'); e1 = tel()['energia_kwh']; import time; time.sleep(1.2); e2 = tel()['energia_kwh']
    check('energia acumulada é monotônica e cresce com o tempo', e2 > e1, f'{e1} → {e2}')
    emu('set/ts/' + str(int(time.time() * 1000) - 2 * 3600 * 1000)); e3 = tel()['energia_kwh']
    check('após 2 h sem leituras o acumulado NÃO salta (intervalo limitado a 60 s: < 0,05 kWh)', 0 <= e3 - e2 < 0.05, f'{e2} → {e3}')
    check('telemetria traz potência (W) e energia (kWh) numéricas e distintas', isinstance(tel()['potencia_w'], (int, float)) and isinstance(tel()['energia_kwh'], (int, float)) and tel()['potencia_w'] != tel()['energia_kwh'])
    s, h, j = jreq('POST', '/api/v1/mensagem', T, json.dumps({'mensagem': 'Desligue o ar ao sair'}))
    check('mensagem (formato antigo, JSON em text/plain) continua aceita por este fluxo', s == 200 and emu('stats')['state']['oled'] == 'Desligue o ar ao sair')

    print('\nValidação e erros (também com CORS, para o navegador conseguir ler o status)')
    s, h, j = jreq('POST', '/api/v1/comando-carga', T, json.dumps({'comando': 'XYZ'}))
    check('comando inválido → 400 com CORS', s == 400 and h.get('access-control-allow-origin') == OK)
    s, h, j = jreq('POST', '/api/v1/comando-carga', T, 'não é json')
    check('corpo inválido → 400', s == 400)
    s, h, j = jreq('POST', '/api/v1/mensagem', T, json.dumps({'mensagem': 'x' * 65}))
    check('mensagem > 64 caracteres → 400', s == 400)
    s, h, j = jreq('POST', '/api/v1/rooms/999/ac/cut', T, '{}')
    check('sala inexistente → 404 com CORS', s == 404 and h.get('access-control-allow-origin') == OK)
    emu('inject/cs_inj_off')
    for m, p, b in [('GET','/api/v1/telemetria',None),('POST','/api/v1/rooms/101/ac/cut','{}'),('POST','/api/v1/rooms/101/ac/on','{}'),('POST','/api/v1/comando-carga','{"comando":"ON"}'),('POST','/api/v1/mensagem','{"mensagem":"oi"}')]:
        s, h, j = jreq(m, p, T, b)
        check(f'dispositivo offline → 503 com CORS em {m} {p}', s == 503 and h.get('access-control-allow-origin') == OK)
    emu('inject/cs_inj_off'); check('volta online', jreq('GET','/api/v1/telemetria')[0] == 200)
    st = emu('stats'); check('nenhuma resposta HTTP duplicada e nenhum erro de função', st['duplicateResponses'] == 0 and not st['errors'], str(st['errors']))

    print('\nOPTIONS sem httpNodeCors (comportamento real do Node-RED com este fluxo)')
    s, h, _ = req('OPTIONS', '/api/v1/rooms/101/ac/cut', {'Origin': OK, 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'content-type'})
    check('preflight sem httpNodeCors NÃO tem CORS (por isso o front envia requisições simples)', 'access-control-allow-origin' not in h, f'status {s}')

with Env(node_cors=True, web=False):
    print('\nOPTIONS com httpNodeCors habilitado no settings.js')
    for path in ('/api/v1/telemetria', '/api/v1/rooms/101/ac/cut', '/api/v1/rooms/101/ac/on', '/api/v1/comando-carga', '/api/v1/mensagem'):
        s, h, _ = req('OPTIONS', path, {'Origin': OK, 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'content-type'})
        check(f'preflight {path}: 204 + Allow-Origin/Methods/Headers', s == 204 and h.get('access-control-allow-origin') == OK and 'POST' in h.get('access-control-allow-methods','') and 'content-type' in h.get('access-control-allow-headers','').lower(), f'{s} {h}')
    s, h, _ = req('OPTIONS', '/api/v1/rooms/101/ac/cut', {'Origin': BAD, 'Access-Control-Request-Method': 'POST'})
    check('preflight de origem não permitida não recebe Allow-Origin', 'access-control-allow-origin' not in h)
    s, h, j = jreq('POST', '/api/v1/comando-carga', {'Origin': OK, 'Content-Type': 'application/json'}, '{"comando":"OFF"}')
    check('POST JSON real com httpNodeCors: 1 único Allow-Origin', s == 200 and h.get('access-control-allow-origin') == OK)
    check('sem respostas duplicadas', emu('stats')['duplicateResponses'] == 0)

print('\nPatch avulso (node-red/patch-ac-on.json) importado sozinho')
with Env(flow=ROOT / 'node-red' / 'patch-ac-on.json', web=False):
    s, h, j = jreq('POST', '/api/v1/rooms/101/ac/on', {'Origin': OK, 'Content-Type': 'text/plain'}, '{}')
    check('patch: ac/on 200 com CORS', s == 200 and j['ac'] == 'ligado' and h.get('access-control-allow-origin') == OK)
    check('patch: sala inexistente → 404', jreq('POST', '/api/v1/rooms/9/ac/on', {'Origin': OK}, '{}')[0] == 404)
    emu('inject/none'); st = emu('stats'); check('patch: sem respostas duplicadas', st['duplicateResponses'] == 0 and not st['errors'])
print('\nCAUSA DO ERRO 400 DO OLED: fluxo cuja função lê msg.payload.mensagem diretamente (fixture do fluxo antigo)')
with Env(flow=ROOT / 'tests' / 'fixtures' / 'flow-antigo-com-bug-cors.json', web=False):
    s, h, j = jreq('POST', '/api/v1/mensagem', {'Content-Type': 'text/plain;charset=UTF-8'}, json.dumps({'mensagem': 'Olá'}))
    check('REPRODUÇÃO: JSON enviado como text/plain (formato anterior do front) → 400 "mensagem vazia"', s == 400 and 'vazia' in j['erro'], f'{s} {j}')
    s, h, j = jreq('POST', '/api/v1/mensagem', {'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'}, 'mensagem=Ol%C3%A1')
    check('CORREÇÃO: mesmo fluxo, formato atual do front (form-urlencoded) → 200', s == 200 and j['exibindo'] == 'Olá', f'{s} {j}')
    s, h, j = jreq('POST', '/api/v1/comando-carga', {'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'}, 'comando=OFF')
    check('o mesmo vale para comando-carga nesse tipo de fluxo (form → 200)', s == 200 and j['modo'] == 'OFF')
sys.exit(summary())
