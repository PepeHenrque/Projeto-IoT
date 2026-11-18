"""Estrutura: Sala 101 exclusiva + separação de camadas preparada para o futuro back-end/banco de dados."""
import re, sys, json
from _helpers import *
strip = lambda t: re.sub(r'(?<![:"\'])//[^\n]*', '', re.sub(r'/\*.*?\*/', '', t, flags=re.S))   # ignora comentários
js = {str(p.relative_to(ROOT)): strip(p.read_text()) for p in (ROOT/'js').rglob('*.js')}
html = (ROOT/'index.html').read_text(); css = (ROOT/'css'/'style.css').read_text()
app_code = '\n'.join(js.values()) + html
layers = {k: v for k, v in js.items() if k.startswith(('js/views/', 'js/ui/', 'js/core/', 'js/app.js'))}

print('Exclusividade da Sala 101 (item 14)')
check('arquivos multi-sala removidos', not any((ROOT/f).exists() for f in ('js/views/rooms.js','js/views/roomDetail.js','js/views/flow.js','js/data/simulatedRooms.js','js/data/simulatedProvider.js','js/core/rooms.js')))
check('sem referências a outras salas, lista ou seleção de salas', not re.search(r'Sala 10[2-9]|Sala 20\d|Auditório|Biblioteca|Lab\. Inform|Lista de [Ss]alas|roomCard|#/salas|ROOMS_SOURCE|simulatedRooms|simulatedProvider|salas ocupadas|Ociosas', app_code), str(re.findall(r'Sala 10[2-9]|Auditório|Biblioteca|#/salas|ROOMS_SOURCE', app_code)))
check('menu inferior com exatamente 4 telas: Início, Controle, Alertas, Histórico', re.findall(r'data-nav="(\w+)"', html) == ['inicio','controle','alertas','historico'])
check('um único ROOM_ID configurado (101) e todas as rotas de equipamento usam essa sala', "ROOM_ID: 101" in js['js/config.js'] and 'cfg.ROOM_ID' in js['js/services/campusApi.js'])

print('\nSeparação interface × comunicação × dados')
check('fetch() só é chamado em js/services/http.js', [k for k, v in js.items() if re.search(r'\bfetch\(', v)] == ['js/services/http.js'])
check('views/ui/core não acessam fetch nem URLs', not [k for k, v in layers.items() if re.search(r'\bfetch\(|https?://|/api/v1', v)])
check('views não chamam serviços diretamente (usam store/selectors/actions)', not [k for k, v in js.items() if k.startswith('js/views/') and re.search(r'CS\.services\.(?!history)|CampusSmart\.services\.(?!history)', v)])
check('URLs e endpoints só em config.js (e mock de desenvolvimento)', sorted(k for k, v in js.items() if '/api/v1' in v) == ['js/config.js', 'js/dev/mockServer.js'])
check('todas as chamadas ao Node-RED passam por CS.services.api', all(f in js['js/services/campusApi.js'] for f in ('getTelemetria', 'setEquipment', 'sendLoadCommand', 'sendOledMessage', 'getRoomProfile')))
check('perfil da Sala 101 (equipamentos) isolado em js/data/roomProfile.js', "id: 101" in js['js/data/roomProfile.js'] and 'roomProfile' not in ''.join(v for k, v in js.items() if k.startswith('js/views/')))
raw_js = {str(p.relative_to(ROOT)): p.read_text() for p in (ROOT/'js').rglob('*.js')}
def endpoints_exist():
    """Todo caminho /api/v1/... declarado em config.js precisa existir como nó 'http in' do fluxo (nada fictício)."""
    cfg = js['js/config.js'].replace('${room(id)}', '/api/v1/rooms/101')
    paths = [re.sub(r'\$\{[^}]+\}', '101', m) for m in re.findall(r"[`'](/api/v1/[^`']+)[`']", cfg)]
    routes = [re.compile('^' + re.sub(r':\w+', '[^/]+', n['url']) + '$') for n in json.load(open(ROOT / 'node-red' / 'campussmart-flow.json')) if n['type'] == 'http in']
    paths = [p for p in paths if p != '/api/v1/rooms/101']          # prefixo auxiliar room(id), não é um endpoint
    missing = [p for p in paths if not any(r.match(p) for r in routes)]
    return bool(paths) and not missing, str(missing)
ok, info = endpoints_exist()
check('nenhum endpoint fictício: todo caminho de config.js existe como nó http in do fluxo', ok, info)
check('sem ramo de histórico dependente de back-end inexistente (HISTORY_SOURCE/future/history)', not re.search(r'HISTORY_SOURCE|future\s*:|/history/|isApi', '\n'.join(js.values())))
check('pontos de integração com o back-end documentados no código ([BACKEND] em config, http, campusApi e historyService)', all('[BACKEND]' in raw_js[f] for f in ('js/config.js', 'js/services/http.js', 'js/services/campusApi.js', 'js/services/historyService.js')))
check('endereço da API em um único lugar (API_BASE) e usado só por http.js', 'API_BASE' in js['js/config.js'] and [k for k, v in js.items() if 'API_BASE' in v] == ['js/config.js', 'js/services/http.js'])
check('nenhum código de banco de dados ou back-end (sem indexedDB/localStorage/WebSocket/SQL)', not re.search(r'indexedDB|localStorage|sessionStorage|WebSocket|SELECT\s+\w+\s+FROM|INSERT\s+INTO', '\n'.join(js.values())))
check('CSS em css/style.css e referenciado no index.html', (ROOT/'css'/'style.css').exists() and 'href="css/style.css"' in html and not (ROOT/'style.css').exists())
print('\nArquivos e compatibilidade')
check('HTML/CSS/JS puros, sem módulos ES (Live Server e file://)', not [k for k, v in js.items() if re.search(r'^\s*(import|export)\s', v, re.M)] and 'type="module"' not in html)
check('todos os scripts do index.html existem', all((ROOT/m).exists() for m in re.findall(r'src="([^"]+)"', html)))
check('todos os arquivos js/ estão referenciados no index.html', all(k in html for k in js))
check('fluxo Node-RED, patch do AC e README presentes', all((ROOT/f).exists() for f in ('node-red/campussmart-flow.json','node-red/patch-ac-on.json','README.md')))

print('\nIluminação removida e ar-condicionado como único equipamento')
check('nenhuma referência à iluminação no front-end (código, HTML e CSS)', not re.search(r'ilumina|\bluz\b|luzLigada|\blight\b|lightO(n|ff)|/light/|lâmpada|💡', app_code + css, re.I), str(re.findall(r'ilumina\w*|\bluz\b|\blight\b|/light/', app_code + css, re.I)[:5]))
check('patch de iluminação do Node-RED removido do projeto', not (ROOT/'node-red'/'patch-iluminacao.json').exists())
check('perfil da sala com um único equipamento: ar-condicionado', re.findall(r"\{\s*id:\s*'(\w+)'", js['js/data/roomProfile.js']) == ['ac'])
check('README não menciona iluminação', not re.search(r'ilumina', (ROOT/'README.md').read_text(), re.I))
check('POST como formulário (x-www-form-urlencoded) no modo padrão, sem text/plain', 'application/x-www-form-urlencoded' in js['js/services/http.js'] and 'text/plain' not in js['js/services/http.js'])
sys.exit(summary())
