"""Testes de ponta a ponta contra um Node-RED REAL (não o emulador) + Chromium real, origem http://127.0.0.1:5500 → http://localhost:1880.
Opcional: precisa de uma instalação do Node-RED.
    mkdir /tmp/nr && cd /tmp/nr && npm init -y && npm install node-red
    NODERED_DIR=/tmp/nr python3 tests/realnodered.test.py
Sem NODERED_DIR a suíte é ignorada (não conta como aprovada)."""
import os, sys, json, time, shutil, subprocess, tempfile, re
from playwright.sync_api import sync_playwright
from _helpers import *
from _helpers import _wait_port

NR = os.environ.get('NODERED_DIR')
if not NR or not (pathlib.Path(NR) / 'node_modules' / 'node-red' / 'red.js').exists():
    print('IGNORADO: defina NODERED_DIR com uma instalação do Node-RED (veja o topo deste arquivo).'); sys.exit(0)

ud = tempfile.mkdtemp(prefix='cs-nr-')
shutil.copy(FLOW_NEW, pathlib.Path(ud) / 'flows.json')
(pathlib.Path(ud) / 'settings.js').write_text("module.exports={uiPort:1880,flowFile:'flows.json',credentialSecret:false,editorTheme:{projects:{enabled:false}},logging:{console:{level:'warn'}}};")
log = open(pathlib.Path(ud) / 'nr.log', 'w')
nr = subprocess.Popen(['node', str(pathlib.Path(NR) / 'node_modules' / 'node-red' / 'red.js'), '-u', ud, '-s', str(pathlib.Path(ud) / 'settings.js')], stdout=log, stderr=log)
web = subprocess.Popen(['python3', '-m', 'http.server', '5500', '--bind', '127.0.0.1', '--directory', str(ROOT)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    _wait_port('localhost', 1880, 40); _wait_port('127.0.0.1', 5500)
    ORIGIN = {'Origin': 'http://127.0.0.1:5500'}
    T = dict(ORIGIN, **{'Content-Type': 'text/plain;charset=UTF-8'})
    tel = lambda: jreq('GET', '/api/v1/telemetria', ORIGIN)[2]
    inject = lambda i: req('POST', '/inject/' + i)[0]
    cmd = lambda c, h=T: jreq('POST', '/api/v1/comando-carga', h, json.dumps({'comando': c}))

    print('Node-RED REAL', json.load(open(pathlib.Path(NR) / 'node_modules' / 'node-red' / 'package.json'))['version'])
    print('\n[HTTP] telemetria e modos da carga no runtime real')
    s, h, t = jreq('GET', '/api/v1/telemetria', ORIGIN)
    check('GET /api/v1/telemetria 200 com CORS e potência/energia numéricas', s == 200 and h.get('access-control-allow-origin') == ORIGIN['Origin'] and isinstance(t['potencia_w'], (int, float)) and isinstance(t['energia_kwh'], (int, float)))
    for c in ('OFF', 'ON', 'AUTO'):
        s, h, j = cmd(c); check(f'POST comando-carga {c} (text/plain) → 200 e resposta com estado efetivo', s == 200 and j['modo'] == c and 'ligada' in j['carga'] and h.get('access-control-allow-origin') == ORIGIN['Origin'])
    cmd('OFF'); time.sleep(0.2); t = tel(); check('OFF: carga cortada e potência < 500 W', t['carga'] == {'modo': 'OFF', 'ligada': False} and t['potencia_w'] < 500, str(t['potencia_w']))
    cmd('ON'); t = tel(); check('ON: carga energizada e potência > 1000 W', t['carga'] == {'modo': 'ON', 'ligada': True} and t['potencia_w'] > 1000, str(t['potencia_w']))
    cmd('AUTO'); occ = tel()['ocupada']
    if occ: inject('cs_inj_occ')
    check('AUTO + sala vazia: carga cortada', tel()['carga']['ligada'] is False)
    inject('cs_inj_occ'); check('AUTO + sala ocupada: carga energizada', tel()['carga']['ligada'] is True); inject('cs_inj_occ')
    check('comando inválido → 400', cmd('XYZ')[0] == 400)
    s, h, j = cmd('OFF', dict(ORIGIN, **{'Content-Type': 'application/json'})); check('também aceita application/json', s == 200 and j['modo'] == 'OFF')
    cmd('ON'); e1 = tel()['energia_kwh']; time.sleep(2); e2 = tel()['energia_kwh']; check('energia acumulada cresce com o tempo', e2 > e1, f'{e1}→{e2}')

    print('\n[NAVEGADOR] Chromium real → Node-RED real')
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True).new_page()
        errs, cors, reqs = [], [], []
        pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: cors.append(m.text) if m.type == 'error' and ('CORS' in m.text or 'blocked' in m.text.lower()) else None)
        pg.on('request', lambda r: reqs.append((r.method, r.url.split('1880')[-1])) if '/api/v1/' in r.url else None)
        bodies = []; pg.on('request', lambda r: bodies.append((r.headers.get('content-type', ''), r.post_data)) if r.url.endswith('/api/v1/mensagem') else None)
        cmd('ON'); pg.goto('http://127.0.0.1:5500/index.html#/inicio'); pg.wait_for_function("!!CampusSmart.core.store.get().telemetry", timeout=10000)
        check('Dashboard: conexão Online', pg.inner_text('#connText') == 'Online')
        check('Dashboard: "Potência atual" e "Consumo acumulado" com valores reais', pg.inner_text('#mPower') != '—' and pg.inner_text('#mEnergy') != '—' and 'Potência atual' in pg.inner_text('#cardPower') and 'Consumo acumulado' in pg.inner_text('#cardEnergy'))
        raw = pg.evaluate("CampusSmart.lastRawTelemetry"); check('valores da tela = telemetria real recebida', abs(float(pg.inner_text('#mPower').replace(',', '.')) * (1000 if pg.inner_text('#mPowerUnit') == 'kW' else 1) - raw['potencia_w']) < 6 and abs(float(pg.inner_text('#mEnergy').replace(',', '.')) - raw['energia_kwh']) < 0.0006)
        a = float(pg.inner_text('#mEnergy').replace(',', '.')); pg.wait_for_function(f"parseFloat(document.querySelector('#mEnergy').textContent.replace(',','.'))>{a}", timeout=14000)
        check('atualização automática: consumo acumulado aumenta sozinho (polling de 5 s)', True)
        pg.evaluate("location.hash='#/controle'"); pg.wait_for_selector('#loadControl')
        def click_mode(c):
            pg.click(f'[data-cmd={c}]'); pg.wait_for_selector('#modal .modal[data-type=success]', timeout=8000); pg.evaluate('CampusSmart.ui.modal.close()')
            pg.wait_for_function(f"document.querySelector('[data-cmd={c}]').getAttribute('aria-pressed')==='true'", timeout=8000)
            pg.evaluate('CampusSmart.core.telemetry.fetchOnce()'); pg.wait_for_timeout(500)
        if tel()['ocupada']: inject('cs_inj_occ')
        click_mode('OFF'); check('botão OFF → Node-RED real em OFF, carga cortada na tela e potência baixa', tel()['carga']['modo'] == 'OFF' and pg.inner_text('#loadState') == 'cortada' and pg.evaluate("CampusSmart.core.store.get().telemetry.potencia") < 500)
        click_mode('ON'); check('botão ON → Node-RED real em ON, carga energizada na tela e potência alta', tel()['carga']['modo'] == 'ON' and pg.inner_text('#loadState') == 'energizada' and pg.evaluate("CampusSmart.core.store.get().telemetry.potencia") > 1000)
        click_mode('AUTO'); check('botão AUTO → Node-RED real em AUTO (sala vazia: carga cortada)', tel()['carga']['modo'] == 'AUTO' and pg.inner_text('#loadMode') == 'AUTO' and pg.inner_text('#loadState') == 'cortada')
        inject('cs_inj_occ'); pg.evaluate('CampusSmart.core.telemetry.fetchOnce()'); pg.wait_for_timeout(600); check('AUTO: sala ocupada → carga energizada na tela', pg.inner_text('#loadState') == 'energizada'); inject('cs_inj_occ')
        click_mode('ON')
        for turn, sel_ in (('off', 'ac'), ('on', 'ac')):
            pg.wait_for_selector(f'[data-action=toggle][data-equip={sel_}][data-turn={"off" if turn == "off" else "on"}]'); pg.click(f'[data-action=toggle][data-equip={sel_}][data-turn={turn}]')
            pg.click('#modalActions .btn.danger' if turn == 'off' else '#modalActions .btn.primary'); pg.wait_for_selector('#modal .modal[data-type=success]', timeout=8000); pg.evaluate('CampusSmart.ui.modal.close()')
            pg.evaluate('CampusSmart.core.telemetry.fetchOnce()'); pg.wait_for_timeout(500)
            check(f'AC {"desligado" if turn == "off" else "ligado"} pela interface (Node-RED real confirma)', tel()['ac']['ligado'] is (turn == 'on'))
        pg.fill('#oledText', 'Atenção: teste real & display'); pg.click('#oledSend'); pg.wait_for_selector('#modal .modal[data-type=success]', timeout=8000)
        check('OLED: Node-RED real respondeu 200 e devolveu o texto exato', '“Atenção: teste real & display”' in pg.inner_text('#modalText'), pg.inner_text('#modalText'))
        pg.evaluate('CampusSmart.ui.modal.close()')
        check('OLED: enviado como formulário (campo mensagem)', bodies and bodies[-1][0].startswith('application/x-www-form-urlencoded') and bodies[-1][1].startswith('mensagem='), str(bodies))
        pg.evaluate("CampusSmart.core.actions.sendOled('z'.repeat(65))"); pg.wait_for_selector('#modal .modal[data-type=error]', timeout=4000)
        check('OLED: texto acima do limite é recusado antes do envio', pg.inner_text('#modalTitle') == 'Mensagem inválida' and len(bodies) == 1); pg.evaluate('CampusSmart.ui.modal.close()')
        inject('cs_inj_off'); pg.evaluate('CampusSmart.core.telemetry.fetchOnce()'); pg.wait_for_timeout(600)
        pg.click('[data-cmd=OFF]'); pg.wait_for_selector('#modal .modal[data-type=error]', timeout=8000)
        check('Node-RED real offline (503): modal "Dispositivo offline" e nada de falso sucesso', pg.inner_text('#modalTitle') == 'Dispositivo offline' and pg.inner_text('#connText') == 'Dispositivo offline')
        pg.evaluate('CampusSmart.ui.modal.close()'); inject('cs_inj_off'); pg.evaluate('CampusSmart.core.telemetry.fetchOnce()'); pg.wait_for_timeout(600)
        check('dispositivo volta e a interface volta a "Online"', pg.inner_text('#connText') == 'Online')
        check('nenhum erro de CORS no console do Chromium', not cors, str(cors)); check('nenhum erro de JavaScript', not errs, str(errs))
        b.close()
finally:
    for pr in (nr, web): pr.terminate(); pr.wait()
    shutil.rmtree(ud, ignore_errors=True)
sys.exit(summary())
