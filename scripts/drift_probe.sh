#!/usr/bin/env bash
set -euo pipefail
# Compare running container images vs compose digests where available.
# Emits non-zero exit if drift detected (simple heuristic).
drift=0
while read -r line; do
  name=$(echo "$line" | awk '{print $1}')
  image=$(echo "$line" | awk '{print $2}')
  # This is a placeholder: your repo policy should pin tags/digests.
  if [[ "$image" == *":latest" ]]; then
    echo "DRIFT: $name uses :latest"
    drift=1
  fi
done < <(docker ps --format '{{.Names}} {{.Image}}')
exit $drift
