#!/usr/bin/env bash
set -euo pipefail
# forte-vision: сайт + API жюри одним процессом.
# Использование: FORTE_API_KEY=<ключ жюри> [FORTE_PORT=8000] services/api/deploy.sh
cd "$(dirname "$0")"
: "${FORTE_API_KEY:?нужен FORTE_API_KEY (ключ жюри)}"
if [ ! -f ../web/dist/index.html ] && [ -z "${FORTE_STATIC_DIR:-}" ]; then
  echo "ВНИМАНИЕ: ../web/dist не найден — сайт отключён (только API)." >&2
  echo "Сборка фронта: cd ../web && VITE_USE_MOCK=false VITE_API_URL=/web npm ci && npm run build" >&2
fi
export FORTE_STATIC_DIR="${FORTE_STATIC_DIR:-../web/dist}"
export FORTE_PIPELINE_CMD="${FORTE_PIPELINE_CMD:-python3 ../ml/run.py}"
echo "pipeline: $FORTE_PIPELINE_CMD (мок удалён — только реальный ML зоны ml)"
exec python3 -m app.main
