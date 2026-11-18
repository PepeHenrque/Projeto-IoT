"""CORS no Chromium real: front em http://127.0.0.1:5500 e Node-RED (emulado) em http://localhost:1880.
Cobre: reprodução do erro original, correção por requisição simples, JSON com preflight via httpNodeCors
e o envio ao display OLED com um fluxo que lê msg.payload.mensagem diretamente (causa do erro 400)."""
import sys
from playwright.sync_api import sync_playwright
from _helpers import *

OLD = ROOT / 'tests' / 'fixtures' / 'flow-antigo-com-bug-cors.json'

def cut_ac(pg, simple):
    pg.goto(f'{WEB}/index.html?simple={1 if simple else 0}#/controle')
    pg.wait_for_selector('#connPill[data-state=online]', timeout=8000)
    pg.wait_for_selector('[data-action=toggle][data-equip=ac][data-turn=off]')
    pg.click('[data-action=toggle][data-equip=ac][data-turn=off]'); pg.click('#modalActions .btn.danger')
    pg.wait_for_selector('#modal .modal[data-type=success], #modal .modal[data-type=error]', timeout=8000)
    return pg.get_attribute('#modal .modal', 'data-type')

def scenario(b, title, simple, expect_ok, **envkw):
    print(f'\n{title}')
    with Env(**envkw):
        pg = b.new_page(); logs = []
        pg.on('console', lambda m: logs.append(m.text))
        res = cut_ac(pg, simple)
        cors_err = any('CORS' in l for l in logs)
        check('POST ac/cut ' + ('concluído com sucesso' if expect_ok else 'bloqueado pelo navegador'), (res == 'success') == expect_ok, res)
        check('console ' + ('sem erro de CORS' if expect_ok else 'mostra o erro de CORS'), cors_err != expect_ok)
        if expect_ok:
            ac = emu('stats')['state']['ac']; check('Node-RED realmente recebeu o comando (AC desligado no estado)', ac is False)
        preflights = [r for r in emu('stats')['requests'] if r['method'] == 'OPTIONS']   # o preflight é interno do navegador: vemos no servidor
        check('preflight OPTIONS ' + ('não é necessário' if simple else 'foi enviado'), (len(preflights) == 0) == simple, str(preflights))
        pg.close()

def oled(b, title, flow):
    print(f'\n{title}')
    with Env(flow=flow):
        pg = b.new_page(); logs = []; pg.on('console', lambda m: logs.append(m.text))
        pg.goto(f'{WEB}/index.html#/controle'); pg.wait_for_selector('#oledText', timeout=8000)
        pg.fill('#oledText', 'Olá, sala 101!'); pg.click('#oledSend')
        pg.wait_for_selector('#modal .modal[data-type=success], #modal .modal[data-type=error]', timeout=8000)
        check('mensagem aceita pelo Node-RED (modal de sucesso)', pg.get_attribute('#modal .modal', 'data-type') == 'success', pg.inner_text('#modalText'))
        check('o fluxo recebeu exatamente o texto digitado', emu('stats')['state']['oled'] == 'Olá, sala 101!', str(emu('stats')['state']))
        reqs = [r for r in emu('stats')['requests'] if r['path'] == '/api/v1/mensagem']
        check('enviada como formulário, sem preflight OPTIONS e sem erro de CORS', reqs and reqs[0]['contentType'].startswith('application/x-www-form-urlencoded') and not [r for r in emu('stats')['requests'] if r['method'] == 'OPTIONS'] and not any('CORS' in l for l in logs))
        pg.close()

with sync_playwright() as p:
    b = p.chromium.launch()
    oled(b, '0a) OLED com fluxo que lê msg.payload.mensagem diretamente (era o erro 400)', OLD)
    oled(b, '0b) OLED com o fluxo do projeto', FLOW_NEW)
    scenario(b, '1) REPRODUÇÃO: fluxo antigo + POST JSON (o erro relatado)', False, False, flow=OLD)
    scenario(b, '2) Fluxo novo + POST JSON, SEM httpNodeCors (limitação do Node-RED)', False, False)
    scenario(b, '3) Fluxo novo + requisição simples (configuração padrão do front)', True, True)
    scenario(b, '4) Fluxo novo + POST JSON + httpNodeCors no settings.js', False, True, node_cors=True)
    scenario(b, '5) Fluxo novo + requisição simples + httpNodeCors (sem conflito de cabeçalhos)', True, True, node_cors=True)
    b.close()
sys.exit(summary())
