import subprocess, time, json, http.client, pathlib, socket, os, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
FLOW_NEW = ROOT / 'node-red' / 'campussmart-flow.json'
WEB = 'http://127.0.0.1:5500'          # Live Server
API = ('localhost', 1880)               # Node-RED
results = []

def check(name, ok, extra=''):
    results.append(bool(ok)); print(('  ✔ ' if ok else '  ✘ ') + name + (f'  [{extra}]' if (extra and not ok) or (extra and os.environ.get('VERBOSE')) else ''))
    return ok

def summary():
    print(f'\n{sum(results)}/{len(results)} verificações passaram'); return 0 if all(results) else 1

def _wait_port(host, port, t=8):
    end = time.time() + t
    while time.time() < end:
        try: socket.create_connection((host, port), 0.3).close(); return
        except OSError: time.sleep(0.1)
    raise RuntimeError(f'porta {port} não abriu')

class Env:
    """Sobe emulador do Node-RED (:1880) e Live Server simulado (:5500)."""
    def __init__(self, flow=FLOW_NEW, node_cors=False, web=True):
        self.flow, self.node_cors, self.web = flow, node_cors, web
    def __enter__(self):
        env = dict(os.environ, NR_HTTPNODECORS='1' if self.node_cors else '0')
        self.emu = subprocess.Popen(['node', str(ROOT/'tests'/'nodered-emulator.js'), str(self.flow), '1880'], env=env, stdout=subprocess.DEVNULL)
        _wait_port('localhost', 1880)
        self.w = None
        if self.web:
            self.w = subprocess.Popen(['python3','-m','http.server','5500','--bind','127.0.0.1','--directory',str(ROOT)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            _wait_port('127.0.0.1', 5500)
        return self
    def __exit__(self, *a):
        for p in (self.emu, self.w):
            if p: p.terminate(); p.wait()

def req(method, path, headers=None, body=None):
    c = http.client.HTTPConnection(*API, timeout=5)
    c.request(method, path, body=body, headers=headers or {})
    r = c.getresponse(); data = r.read(); h = {k.lower(): v for k, v in r.getheaders()}
    c.close(); return r.status, h, data

def jreq(method, path, headers=None, body=None):
    s, h, d = req(method, path, headers, body)
    try: j = json.loads(d or b'null')
    except Exception: j = None
    return s, h, j

def emu(path): return jreq('GET', '/__emu/' + path)[2]
def reset(): emu('reset')
