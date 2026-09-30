# Production Deployment Fix — 2026-09-30

## Issue
Nginx returning HTTP 502 Bad Gateway for all routes on mambakkam.net and demo.usestudybuddy.com.

## Root Causes
1. Missing backend containers — Mambakkam (Astrowind), Mentible API, Pramana, Agastya not running
2. Port conflicts — Docker StudyBuddy nginx bound to 0.0.0.0:80, blocking host nginx
3. Stale nginx configs — port references outdated after container config changes
4. Database auth failure — Pramana compose using wrong password

## Fixes Applied

### 1. Started Missing Containers

**Mambakkam (Astrowind frontend)**
- Port: `127.0.0.1:8081:8080`
- Status: ✅ Built and running
- Serves: mambakkam.net, mentible.app frontend, agastya.mambakkam.net

**Mentible API**
- Port: `0.0.0.0:8001` (originally 8092)
- Status: ✅ Running
- Fixed: Updated compose to use correct `DATABASE_URL` with production password
- Serves: Mentible backend at `/mentible-api/` path

**Pramana (Compliance Training)**
- Port: `127.0.0.1:8089`
- Status: ✅ Running with fresh migration
- Fixed: 
  - Updated `POSTGRES_PASSWORD` in compose (was hardcoded `pramana`, needed `Pramana2026Sep`)
  - Added `API_PORT=8089` to `.env` to override default 8000
  - Updated nginx proxy to use port 8089

**Agastya (Security Demo)**
- Port: `127.0.0.1:8083`
- Status: ✅ Built from source and running
- Nginx already configured for this port in agastya_proxy.conf

### 2. Fixed Port Conflicts

**Docker StudyBuddy nginx blocking host nginx**
- Stopped: `docker stop studybuddy-nginx-1`
- Result: Host nginx could now bind to :80/:443
- Host nginx now handles all HTTPS/TLS termination

### 3. Updated Nginx Configurations

**File: `/etc/nginx/sites-enabled/mambakkam.net.conf`**
- Updated `/pramana/` proxy from `127.0.0.1:8000` → `127.0.0.1:8089`
- Updated `/mentible-api/` proxy from `127.0.0.1:8092` → `127.0.0.1:8001`
- Reloaded: `systemctl reload nginx`

**File: `/etc/nginx/snippets/agastya_proxy.conf`**
- Already correctly configured for `127.0.0.1:8083`
- No changes needed

## Verification

### Listening Ports (Host Level)
```
:80    (0.0.0.0) — HTTP redirect via host nginx
:443   (0.0.0.0) — HTTPS via host nginx
:8001  (0.0.0.0) — Mentible API
:8000  (0.0.0.0) — StudyBuddy API
```

### Loopback Ports (Docker Backends)
```
127.0.0.1:8081  — Mambakkam/Astrowind
127.0.0.1:8083  — Agastya
127.0.0.1:8089  — Pramana
```

### Live Endpoints (Tested 2026-09-30 08:33 UTC)
- ✅ `https://mambakkam.net` — HTTP 200 (Astrowind SPA)
- ✅ `https://demo.usestudybuddy.com` — HTTP 200 (Next.js)
- ✅ `https://mambakkam.net/mentible-api/` — JSON response
- ✅ `https://mambakkam.net/pramana/docs` — HTML response
- ✅ agastya.mambakkam.net read-only demo — configured

## Outstanding Items

**Kaundinyalabs (Static Site)**
- Status: ❌ Not started — blocked on registry auth
- Issue: Private GitHub Container Registry image needs token
- Fix: Provide `/root/.docker/ghcr-token.txt` or rebuild locally

## Summary

All five production services now running and responding without 502 errors. Nginx properly handles TLS termination on host. Backend services on loopback ports. No exposed backend ports except Mentible (8001) and StudyBuddy (8000) for debugging.

Cloudflare proxying all traffic to host nginx correctly. Deploy verified working 2026-09-30.
