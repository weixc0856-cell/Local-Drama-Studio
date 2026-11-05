#!/usr/bin/env bash
# Wait for all 18 Wan jobs to report success, then assemble the 2-minute cut.
set -u
cd "$(dirname "$0")/.."
LOG=experiments/shinkai_scene/wan24_watch.log
while true; do
  ok=$(grep -l '"status": "success"' experiments/shinkai_scene/wan24/*/job.json 2>/dev/null | wc -l)
  bad=$(grep -l '"status": "failed"' experiments/shinkai_scene/wan24/*/job.json 2>/dev/null | wc -l)
  echo "$(date '+%F %T') ok=$ok failed=$bad" >> "$LOG"
  if [ "$ok" -ge 18 ]; then break; fi
  sleep 120
done
echo "$(date '+%F %T') assembling" >> "$LOG"
.venv/Scripts/python.exe scripts/assemble_scene_24.py --out experiments/shinkai_scene/renders_24 >> "$LOG" 2>&1
echo "$(date '+%F %T') assembler exit=$?" >> "$LOG"
