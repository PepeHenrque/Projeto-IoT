#!/usr/bin/env bash
# Executa toda a bateria. Requer: node, python3, playwright (pip install playwright && playwright install chromium)
# Opcional: NODERED_DIR=/caminho/com/node-red/instalado  -> inclui a suíte contra o Node-RED REAL (sem isso ela é ignorada).
cd "$(dirname "$0")/.." || exit 1
rc=0
for t in structure flow_http browser_cors app realnodered; do
  echo "=================== $t"; python3 tests/$t.test.py || rc=1
done
exit $rc
