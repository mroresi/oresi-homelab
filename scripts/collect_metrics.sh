#!/usr/bin/env bash
set -euo pipefail
# Collect light health and capacity signals; emit JSON.
kuma_green=${KUMA_GREEN:-0}
kuma_amber=${KUMA_AMBER:-0}
kuma_red=${KUMA_RED:-0}
disk_free=$(df -Ph / | awk 'NR==2{print $4}')
cpu_count=$(nproc || sysctl -n hw.ncpu 2>/dev/null || echo 1)
host=$(hostname)
jq -n --arg host "$host" --arg disk_free "$disk_free"   --argjson cpu_count "$cpu_count"   --argjson kuma_green "$kuma_green" --argjson kuma_amber "$kuma_amber" --argjson kuma_red "$kuma_red"   '{host:$host,disk_free:$disk_free,cpu_count:$cpu_count,kuma:{green:$kuma_green,amber:$kuma_amber,red:$kuma_red}}'
