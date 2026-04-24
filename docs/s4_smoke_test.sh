#!/usr/bin/env bash
# S4 ingest smoke test — exercises backend endpoints end-to-end.
#
# Pre-requisites:
#   cd Omniver-RAN && docker compose up -d postgres
#   ./shell/run_migrations.sh
#   python manage.py runserver 0.0.0.0:8001
#
# Kit may or may not be running — `kit_errors` counts failures for the signal
# push step (backend DB write is independent).
set -euo pipefail

BASE="${BASE:-http://localhost:8001}"

echo "==> 1. SceneStateReader (expects 502 if Kit down, 200 if up)"
curl -s -X POST "$BASE/api/v0.1/RAN/Scene/SceneStateReader/read" \
  -H 'Content-Type: application/json' -d '{}' | python3 -m json.tool || true
echo

echo "==> 2. SceneIngestor — register one gNB"
curl -s -X POST "$BASE/api/v0.1/RAN/Ingest/SceneIngestor/create" \
  -H 'Content-Type: application/json' \
  -d '{
    "scene_id": "umi_3sector_v1",
    "buildings": [],
    "gnbs": [{"name":"gNB_Macro_NW","frequency_ghz":3.5,"power_dbm":43,"bandwidth_mhz":100}],
    "ues": []
  }' | python3 -m json.tool
echo

echo "==> 3. SignalIngestor — push 2 UE signals"
curl -s -X POST "$BASE/api/v0.1/RAN/Ingest/SignalIngestor/create" \
  -H 'Content-Type: application/json' \
  -d '{
    "ts": "2026-04-18T07:00:00Z",
    "signals": [
      {"ue_name":"UE_Handover_Path","serving_cell":"gNB_Macro_NW","rsrp_dbm":-78.2,"sinr_db":12.5,
       "rsrp_map":{"gNB_Macro_NW":-78.2,"gNB_Macro_SE":-92.1}},
      {"ue_name":"UE_LOS_Reference","serving_cell":"gNB_Small_Plaza","rsrp_dbm":-65.0,"sinr_db":20.1,
       "rsrp_map":{"gNB_Small_Plaza":-65.0,"gNB_Macro_NW":-88.0}}
    ]
  }' | python3 -m json.tool
echo

echo "==> 4. History query — last hour for UE_Handover_Path"
curl -s -X POST "$BASE/api/v0.1/RAN/History/SignalHistoryReader/read" \
  -H 'Content-Type: application/json' \
  -d '{"ue_name":"UE_Handover_Path","since":"-1h"}' | python3 -m json.tool
echo

echo "==> 5. PlatformReporter stub — upstream UE positions"
curl -s -X POST "$BASE/api/v0.1/RAN/Platform/PlatformReporter/create" \
  -H 'Content-Type: application/json' \
  -d '{"event":"ue_positions","payload":{"ts":"2026-04-18T07:05:00Z","ues":[{"name":"UE_1","x":10,"y":0,"z":20}]}}' \
  | python3 -m json.tool
echo

echo "==> 6. Validation error (expected failure)"
curl -s -X POST "$BASE/api/v0.1/RAN/Ingest/SignalIngestor/create" \
  -H 'Content-Type: application/json' \
  -d '{"signals":[{"ue_name":"X"}]}' | python3 -m json.tool
echo

echo "==> DONE. Verify DB contents:"
echo "  docker exec omniver_ran_postgres psql -U ran -d ran_dt \\"
echo "    -c \"SELECT ue_name, serving_cell, rsrp_dbm FROM signal_history ORDER BY signal_ts DESC LIMIT 5;\""
