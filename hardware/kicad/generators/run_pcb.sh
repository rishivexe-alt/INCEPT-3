#!/usr/bin/env bash
set -euo pipefail

GEN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KICAD_DIR="$(cd "$GEN_DIR/.." && pwd)"
ROUTE_DIR="$KICAD_DIR/routing"
FREEROUTING_JAR="${FREEROUTING_JAR:-$KICAD_DIR/../tools/freerouting.jar}"

mkdir -p "$ROUTE_DIR"
cd "$GEN_DIR"
BH=92 python3 build_pcb.py
python3 export_dsn.py

if [[ ! -f "$FREEROUTING_JAR" ]]; then
  echo "Freerouting JAR not found: $FREEROUTING_JAR" >&2
  echo "Set FREEROUTING_JAR to the path of your Freerouting JAR and rerun." >&2
  exit 2
fi

rm -f "$ROUTE_DIR/out.ses"
java -jar "$FREEROUTING_JAR" -de "$ROUTE_DIR/in.dsn" -do "$ROUTE_DIR/out.ses" -mp 60
python3 finish_pcb.py
python3 post_pcb.py
