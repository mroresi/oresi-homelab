#!/usr/bin/env python3
import sys

safe_keys = {"TZ", "PUID", "PGID", "UID", "GID", "UMASK", "PORT", "HOST", "URL"}
data = sys.stdin.read()
out = []

for line in data.splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        v_stripped = v.strip()
        if (
            k.strip() in safe_keys
            or v_stripped == ""
            or v_stripped.upper() == "TRUE"
            or v_stripped.upper() == "FALSE"
        ):
            out.append(f"{k}={v}")
        else:
            out.append(f"{k}=***REDACTED***")
    else:
        out.append(line)

sys.stdout.write("\n".join(out))
