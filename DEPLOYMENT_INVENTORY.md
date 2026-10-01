# Production Deployment Inventory — 178.105.160.62 (mambakkam-cx22)

**Scanned:** 2026-10-01 · **Host:** Hetzner VPS (mambakkam-cx22) · **Status:** 15 containers active

---

## Executive Summary

| Project | Service | Host Port | Container Port | Status | Issue |
|---------|---------|-----------|-----------------|--------|-------|
| **StudyBuddy** | nginx | 127.0.0.1:8443 | 8443 | ✅ Running | None |
| **StudyBuddy** | api | (internal) | 8000 | ✅ Running | None |
| **StudyBuddy** | web | (internal) | 3000 | ✅ Running | None |
| **StudyBuddy** | db (postgres) | 127.0.0.1:5432 | 5432 | ✅ Running | Loopback-only (correct) |
| **StudyBuddy** | redis | 127.0.0.1:6379 | 6379 | ✅ Running | Loopback-only (correct) |
| **Mentible** | api | 127.0.0.1:8092 | 8000 | ✅ Running | ✅ Fixed |
| **Mentible** | redis | (internal) | 6379 | ✅ Running | None |
| **Mentible** | celery-worker | (internal) | 8000 | ✅ Running | None |
| **Mentible** | celery-beat | (internal) | 8000 | ✅ Running | None |
| **Agastya** | app | 127.0.0.1:8083 | 8000 | ✅ Running | None |
| **Kaundinyalabs** | website | 127.0.0.1:8082 | 8080 | ✅ Running | None |
| **Mambakkam** | astrowind | 127.0.0.1:8081 | 8080 | ✅ Running | None |
| **Host** | nginx (reverse proxy) | 0.0.0.0:80, 0.0.0.0:443 | — | ✅ Running | Cloudflare Origin Cert |

---

## Active Host-Level Listening Ports

```
PORT       SERVICE                 BINDING
22         SSH                     0.0.0.0 + [::] (all interfaces)
53         systemd-resolve DNS     127.0.0.53 / 127.0.0.54
80         nginx (reverse proxy)   0.0.0.0 + [::] (all interfaces)
443        nginx (reverse proxy)   0.0.0.0 + [::] (all interfaces)
5432       StudyBuddy postgres     127.0.0.1 only
5433       Host postgres           127.0.0.1 only
6379       StudyBuddy redis        127.0.0.1 only
8081       Mambakkam astrowind     127.0.0.1 only (docker-proxy)
8082       Kaundinyalabs website   127.0.0.1 only (docker-proxy)
8083       Agastya app             127.0.0.1 only (docker-proxy)
8092       Mentible API            127.0.0.1 only (docker-proxy)
8443       StudyBuddy nginx HTTPS  127.0.0.1 only (docker-proxy)
```

**Summary:** No port conflicts. All loopback-bound services correctly isolated from public internet (Docker iptables evaluated before ufw).

---

## StudyBuddy Deployment Status

**Location:** `/opt/studybuddy`  
**Compose Project:** `studybuddy`  
**Environment:** Docker Compose (production-shaped)

### Services & Port Bindings

| Container | Image | Exposed Port | Binding | Notes |
|-----------|-------|--------------|---------|-------|
| studybuddy-nginx-1 | nginx:alpine | 80 (internal), 8443 | 127.0.0.1:8443 | Fronts StudyBuddy stack; TLS termination handled by host nginx |
| studybuddy-api-1 | ghcr.io/wegofwd2020-hub/studybuddy-api:latest | 8000 | (internal only) | FastAPI backend; pgbouncer pool connections |
| studybuddy-web-1 | ghcr.io/wegofwd2020-hub/studybuddy-web:latest | 3000 | (internal only) | Next.js frontend |
| studybuddy-db-1 | pgvector/pgvector:pg16 | 5432 | 127.0.0.1:5432 | PostgreSQL with pgvector; **loopback-only** to prevent BSI/CERT-Bund exposure |
| studybuddy-redis-1 | redis:7-alpine | 6379 | 127.0.0.1:6379 | In-memory cache/session store; **loopback-only** |
| studybuddy-celery-worker-1 | ghcr.io/wegofwd2020-hub/studybuddy-api:latest | 8000 | (internal only) | Async background job worker |
| studybuddy-celery-beat-primary-1 | ghcr.io/wegofwd2020-hub/studybuddy-api:latest | 8000 | (internal only) | Scheduled job coordinator |
| studybuddy-autoheal-1 | [internal health monitor] | — | (internal only) | Auto-healing container |
| studybuddy-migrate-1 | ghcr.io/wegofwd2020-hub/studybuddy-api:latest | — | (exited) | DB migrations; runs on startup, exits successfully |

### Nginx Configuration

Host-level nginx proxies `demo.usestudybuddy.com` → `127.0.0.1:8443` (StudyBuddy's nginx, which serves the stacked api/web/nginx).

**StudyBuddy docker-compose.yml ports:**
- ✅ **db**: `127.0.0.1:5432:5432` — loopback-only (security comment in file explains BSI/CERT-Bund risk)
- ✅ **redis**: `127.0.0.1:6379:6379` — loopback-only
- ✅ **api**: `8000:8000` — internal Docker bridge, no host binding
- ✅ **web**: `3000:3000` — internal Docker bridge, no host binding
- ✅ **nginx**: `80:80` (internal Docker), `127.0.0.1:8443:8443` — TLS to host loopback

**Conclusion:** StudyBuddy **does not conflict** with any existing services. Port 80 binding is within its isolated Docker network.

---

## Mentible Deployment Status ✅

**Location:** `/opt/mentible`  
**Compose Project:** `mentible`  
**Environment:** Docker Compose (production-shaped)  
**Compose File Used:** `docker-compose.demo.yml` (based on running container `127.0.0.1:8092`)

### Services & Port Bindings

| Container | Image | Exposed Port | Binding | Issue |
|-----------|-------|--------------|---------|-------|
| mentible-api | mentible-backend:latest | 8000 | 127.0.0.1:8092 | ✅ None |
| mentible-redis | redis:7-alpine | 6379 | (internal only) | None |
| mentible-celery-worker | [built image] | 8000 | (internal only) | None |
| mentible-celery-beat | [built image] | 8000 | (internal only) | None |

### Port Configuration ✅ RESOLVED

**Host nginx config** (`/etc/nginx/sites-enabled/mambakkam.net.conf`):
```nginx
location /mentible-api/ {
    proxy_pass http://127.0.0.1:8092/;  # ✅ FIXED
    proxy_set_header Host              $host;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    ...
}
```

**Mentible API binding:** `127.0.0.1:8092` ✅ Matches nginx config

**Status:** 
- ✅ Nginx config updated to proxy to correct port (8092)
- ✅ Mentible API confirmed running on 127.0.0.1:8092
- ✅ Endpoints `https://mambakkam.net/mentible-api/*` operational
- ✅ Verified 2026-10-01 13:05 UTC

---

## Other Services

### Agastya (Security Monitoring Demo)
- **Location:** `/opt/agastya`
- **Port:** 127.0.0.1:8083
- **Status:** ✅ Running
- **Notes:** Read-only demo with defense-in-depth (nginx limit_except + app-level demo mode stripping). No conflicts.

### Kaundinyalabs Website
- **Location:** `/opt/kaundinyalabs`
- **Port:** 127.0.0.1:8082
- **Status:** ✅ Running
- **Notes:** Static Astro export, pulled from GHCR (no local build). No conflicts.

### Mambakkam Portfolio Site
- **Location:** `/opt/mambakkam`
- **Port:** 127.0.0.1:8081 (astrowind container)
- **Status:** ✅ Running
- **Notes:** Hub dashboard + demo embeds (Mentible-lite, Atri-Sangam, etc.). No conflicts.

### Host PostgreSQL
- **Port:** 127.0.0.1:5433 (separate from StudyBuddy 5432)
- **Status:** ✅ Running
- **Notes:** System postgres (not Docker). Isolated.

---

## Summary: Deployment Status

**User's Concern:** StudyBuddy may conflict with existing services.

**Result:** ✅ **NO CONFLICTS DETECTED — ALL SERVICES HEALTHY**

### StudyBuddy Status
- StudyBuddy's internal nginx port 80 binding is **isolated within its Docker network** — no host-level conflict
- StudyBuddy's loopback bindings (5432, 6379) follow security best practices (BSI/CERT-Bund CB-Report guidance)
- StudyBuddy's external TLS port (8443) is correctly bound to loopback, fronted by host nginx
- ✅ **Conclusion:** No conflicts with other services

### Mentible Status
- ✅ nginx config correctly proxies to `127.0.0.1:8092`
- ✅ Mentible API running on `127.0.0.1:8092`
- ✅ Endpoints `https://mambakkam.net/mentible-api/*` operational
- ✅ **Port mismatch RESOLVED** (verified 2026-10-01)

---

## Configuration Files Referenced

- `/opt/studybuddy/docker-compose.yml` — StudyBuddy production compose (active)
- `/opt/mentible/docker-compose.demo.yml` — Mentible production compose (active)
- `/opt/mentible/docker-compose.yml` — Mentible dev compose (not in use on prod)
- `/etc/nginx/sites-enabled/mambakkam.net.conf` — Main host vhost (Mentible proxy corrected to 8092)
- `/etc/nginx/sites-enabled/demo.usestudybuddy.com.conf` — StudyBuddy demo vhost
- `/etc/nginx/sites-enabled/mentible.app.conf` — Mentible.app apex domain vhost
- `/etc/nginx/sites-enabled/kaundinyalabs.com.conf` — Kaundinyalabs vhost
- `/etc/nginx/sites-enabled/agastya.mambakkam.net.conf` — Agastya demo vhost
