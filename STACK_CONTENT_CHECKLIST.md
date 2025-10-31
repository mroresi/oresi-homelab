# Stack Checklist — Content

**Purpose**
Serve and manage content systems (e.g. Nextcloud, Nginx Proxy Manager, Calibre).

**Pre-deploy Checks**
- `/srv/content` NFS share mounted.
- Proxy routes defined in `nginx_proxy.conf`.
- TLS certs present or Let's Encrypt enabled.

**Post-deploy Validation**
- Nextcloud reachable on 443 with valid cert.
- NPM dashboard online.
- Calibre-web connects to library path `/srv/content/books`.

**Maintenance**
- Confirm cron for file indexing.
- Ensure `healthcheck` endpoints return HTTP 200.
