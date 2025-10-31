#!/usr/bin/env python3
import sys,re
safe_keys={'TZ','PUID','PGID','UID','GID','UMASK','PORT','HOST','URL'}
data=sys.stdin.read()
out=[]
for line in data.splitlines():
    if '=' in line and not line.strip().startswith('#'):
        k,v=line.split('=',1)
        if k.strip() in safe_keys or v.strip()=='' or v.strip().upper()=='TRUE' or v.strip().upper()=='FALSE':
            out.append(f"{k}={v}")
        else:
            out.append(f"{k}=***REDACTED***")
    else:
        out.append(line)
sys.stdout.write("\n".join(out))
