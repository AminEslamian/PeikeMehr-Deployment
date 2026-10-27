# Peykemehr — Production Readiness Audit

**Audit date:** 2026-10-26  
**Scope:** local Docker deployment, Django backend, React frontend, SQLite, media handling, OTP/SMS, deployment configuration  
**Auditor:** automated low-impact audit (read-only inspection + isolated test database)  
**Production target:** Ubuntu 24.04 VPS, 2 vCPU / 4 GB RAM / 40 GB SSD, ~700 registered users

---

## 1. Executive summary

The application runs and the core API behavior is sound: **106 backend tests were executed, 103 passed, 3 failed**, and the live SQLite database and media volume were not modified. Authentication, ownership checks, survey validation, ticket isolation, and admin-only API access are largely correct.

It is **not production-ready yet**. The blocking issues are:

1. **Secrets are committed to git** (`.env` is tracked and contains the Django secret key and SMS API key).
2. **OTP delivery is a stub** — `send_sms()` prints the code to stdout and always reports success. Real SMS is not implemented.
3. **File upload validation trusts the client `Content-Type`** — a test proved an HTML payload sent as `image/png` is accepted and stored. Combined with public `/media/` serving, missing `nosniff` on media responses, and JWTs in `localStorage`, this is a credible stored-XSS/account-takeover chain.
4. **No HTTPS/domain configuration and no secure cookie/HSTS/proxy settings**; `manage.py check --deploy` reports 4 security warnings.
5. **SQLite is not suitable for the production concurrency target**; PostgreSQL is not implemented (no driver, no settings, no staging test).
6. **S3-compatible object storage is implemented and verified locally** (private signed URLs, upload/read/delete round-trip); production bucket policy, versioning/lifecycle rules, and VPS rollout remain pending. The 40 GB SSD is very likely too small for the estimated media volume.
7. **No backups, health checks, resource limits, log rotation, monitoring, or CI**, and no frontend tests.

The VPS load test was **not executed**. A separate, gated plan is in section 14.

---

## 2. Scope, method, and safety

### What was inspected
- Git working tree, tracked files, branches, remotes, large/stray files.
- `docker-compose.yml`, both Dockerfiles, frontend `nginx.conf`, empty `nginx/default.conf`.
- Django settings, URL configuration, models, serializers, views, services, admin, migrations (read only, not applied).
- React app shell, API client, auth flow, dashboard/report upload, profile, survey, admin, and blog views.
- Live container status, health, process command, resource usage, security headers.
- Dependency files, test framework presence, migration consistency.

### Safety controls used
- No container was stopped, restarted, recreated, rebuilt, or removed.
- No volume, image, network, database, or media file was deleted.
- No migration was applied to the live database.
- Tests ran through `docker exec` in the already-running backend container using Django's **in-memory SQLite test database**.
- Test uploads were redirected to a temporary directory; `send_sms` was mocked; no real SMS was sent.
- No paid object-storage request was made.
- No load/stress test was run locally or against any VPS.
- No secret values were printed. Only non-sensitive configuration (DEBUG, ALLOWED_HOSTS) was read.

### Verified data footprint at audit time
| Item | Value |
|---|---|
| Live SQLite size | 311,296 bytes |
| Teachers | 1 |
| OTP rows | 4 |
| Reports | 1 |
| Surveys | 0 |
| Submissions | 0 |
| Tickets | 0 |
| Media files | 2 files, 46 MB total |

This is a very small live dataset, which makes a clean production cutover feasible.

---

## 3. Current architecture (verified)

```
Browser
  │  HTTP :8080
  ▼
frontend container (nginx:alpine)
  ├─ serves React production build (Vite)
  ├─ /api/, /admin/, /admin-panel/  ──proxy──► backend:8000
  └─ /media/, /static/              ──read-only volume mount
                                              │
                                              ▼
backend container (python:3.13-slim)
  └─ CMD: migrate → collectstatic → gunicorn config.wsgi (3 sync workers)
       ├─ /data/db.sqlite3        (named volume sqlite_data)
       ├─ /app/media              (named volume media_data)
       └─ /app/staticfiles        (named volume static_data)
```

### Verified runtime facts
| Fact | Evidence |
|---|---|
| Django 5.2.18, DRF 3.18.3, SimpleJWT 5.5.1, Python 3.13 | container introspection |
| Backend command uses Gunicorn, not `runserver` | container `Cmd` |
| Gunicorn workers = 3, bind `0.0.0.0:8000` | container `Cmd` |
| Backend port not published to host (only `expose`) | `docker ps`, compose |
| Frontend published on `0.0.0.0:8080` | `docker ps` |
| `DEBUG=False` | running container env + `check --deploy` |
| `ALLOWED_HOSTS=localhost,127.0.0.1` | running container env |
| Database engine = SQLite at `/data/db.sqlite3` | settings + compose |
| Media = local filesystem at `/app/media` | settings + compose |
| Frontend `/` returns 200; `/api/schema/` 200; `/api/docs/` 200 | smoke test |
| Anonymous protected APIs return 401 | smoke test |
| Invalid login input returns 400 | smoke test |
| Docker 28.3.2; Docker Desktop allocated 8.13 GB RAM / 12 CPUs | `docker info` |
| Containers use ~11 MB (frontend) and ~135–215 MB (backend) | `docker stats` |
| `makemigrations --check --dry-run` → “No changes detected” | container |
| All migrations applied in live DB | `showmigrations` |
| Pre-existing uncommitted changes were present before the audit | `git status` at start |
| Running image code matched host `accounts/serializers.py` and `accounts/tests.py` (SHA-256) | hash comparison |

> The running containers were built from code that includes the current uncommitted changes. Those changes must be committed before any reproducible production build.

---

## 4. Local resource baseline and observations

| Metric | Before tests | After tests |
|---|---|---|
| Host total RAM | 15.63 GB | 15.63 GB |
| Host free RAM | 1.64 GB | 2.65 GB |
| Host logical CPUs | 12 | 12 |
| C: free disk | 147.59 GB | 147.56 GB |
| Docker Desktop RAM / CPUs | 8.13 GB / 12 | 8.13 GB / 12 |
| Backend container memory | 135.3 MiB | 215.6 MiB |
| Frontend container memory | 10.9 MiB | 11.1 MiB |
| Live DB size / mtime | 311,296 B / unchanged | 311,296 B / unchanged |
| Media file count | 2 | 2 |

**Observation:** the host had only ~1.6–2.7 GB free RAM even before testing. The audit stayed within a small envelope (peak ~216 MB for the backend container). This is not a promise that the host is suitable for load generation: a 100-VU scenario should be run from a separate machine, not from this laptop.

---

## 5. Tests added and executed

### Test files added / replaced (test code only)
| File | Purpose |
|---|---|
| `backend/accounts/tests_audit.py` | OTP lockout/reuse/expiry, JWT invalid/expired/missing, teacher→admin authorization, registration grade validation |
| `backend/reports/tests.py` | report ownership, required fields, tag rules, file type/size/count, image+video upload, spoofed upload, file deletion, no pagination |
| `backend/survey/tests.py` | active-only surveys, required answers, choice validation, cross-survey/cross-question rejection, resubmission, per-user scoping |
| `backend/tickets/tests.py` | identity binding, ownership isolation, admin-field protection |
| `backend/blogs/tests.py` | read vs admin-write permissions, extension validation, mandatory media |
| `backend/adminpanel/tests.py` | admin API authz, teacher search/detail, points, ticket answers, media list, staff exclusion, public admin shell |

The original `reports/survey/tickets/blogs/adminpanel` test files were stubs (`# Create your tests here.`); they were replaced with real tests. `backend/accounts/tests.py` was **not** modified (it already had uncommitted changes before this audit).

### Commands used
```powershell
docker exec -e PYTHONUNBUFFERED=1 peykemehr-deployment-backend-1 python manage.py test accounts.tests.NormalizePhoneNumberTests -v 2
docker exec -e PYTHONUNBUFFERED=1 peykemehr-deployment-backend-1 python manage.py test accounts -v 1
docker exec -e PYTHONUNBUFFERED=1 peykemehr-deployment-backend-1 python manage.py test accounts.tests_audit -v 2
docker exec -e PYTHONUNBUFFERED=1 peykemehr-deployment-backend-1 python manage.py test reports -v 2
docker exec -e PYTHONUNBUFFERED=1 peykemehr-deployment-backend-1 python manage.py test survey -v 2
docker exec -e PYTHONUNBUFFERED=1 peykemehr-deployment-backend-1 python manage.py test tickets -v 2
docker exec -e PYTHONUNBUFFERED=1 peykemehr-deployment-backend-1 python manage.py test blogs -v 2
docker exec -e PYTHONUNBUFFERED=1 peykemehr-deployment-backend-1 python manage.py test adminpanel -v 2
docker exec -e PYTHONUNBUFFERED=1 peykemehr-deployment-backend-1 python manage.py test accounts reports survey tickets blogs adminpanel -v 1
docker exec peykemehr-deployment-backend-1 python manage.py check --deploy
docker exec peykemehr-deployment-backend-1 python manage.py makemigrations --check --dry-run
docker exec peykemehr-deployment-backend-1 python manage.py showmigrations
```

New test files were copied into the running container with `docker cp` only to execute them (the container has no bind mount for code). This is ephemeral; no host production file was changed by that step.

### Results
| Suite | Tests | Result |
|---|---:|---|
| Existing `accounts` | 43 | **OK** |
| New `accounts` audit | 13 | 12 pass, **1 fail** |
| `reports` | 14 | 13 pass, **1 fail** |
| `survey` | 11 | **OK** |
| `tickets` | 7 | **OK** |
| `blogs` | 7 | **OK** |
| `adminpanel` | 11 | 10 pass, **1 fail** |
| **Total** | **106** | **103 pass / 3 fail** |

Total wall time for the consolidated run: **1.58 s**. Test database: `file:memorydb_default?mode=memory&cache=shared`. Live DB size/mtime and media file count were identical before and after.

### The 3 failures (confirmed bugs, not test defects)
1. `accounts.tests_audit.RegistrationValidationTests.test_unknown_grade_is_rejected` — returned **201** instead of 400.
2. `reports.tests.ReportAPITests.test_create_rejects_spoofed_html_disguised_as_image` — returned **201** instead of 400.
3. `adminpanel.tests.AdminAPIAccessTests.test_teacher_list_excludes_staff_accounts` — staff account was present in the teacher list.

### Coverage
**Not measured.** `coverage` is not installed in the backend image. Installing it would violate the audit rule against changing dependencies. No coverage number is claimed.

### Frontend tests
**BLOCKED / NOT IMPLEMENTED.** `frontend/package.json` has no test runner and `frontend/node_modules` is absent. Adding Vitest/Jest/Testing Library would change dependencies, which the audit rules forbid. Frontend findings below are from code inspection plus the fact that the production image built and serves successfully.

---

## 6. Confirmed bugs and security risks

Severity is an audit judgement, not a CVSS score.

| # | Severity | Issue | Evidence | Impact |
|---|---|---|---|---|
| 1 | **Critical** | `.env` is tracked in git and contains `DJANGO_SECRET_KEY` and `SMS_IR_API_KEY` | `git ls-files` shows `.env`; no root `.gitignore`; file is in the initial commit | Secret disclosure if the repo is shared/pushed. Django secret allows session/token forgery if leaked; SMS key allows paid abuse. |
| 2 | **Critical** | Upload validation trusts client `Content-Type`; HTML stored as “image” | failing test returned 201 | Stored XSS on the app origin, JWT theft from `localStorage`, account takeover. |
| 3 | **Critical** | Media is publicly served from `/media/` with no authorization | `frontend/nginx.conf` `alias /var/www/media/`; no auth check | Any teacher’s private photos/videos are readable by anyone with the URL. |
| 4 | **Critical** | Nginx does not add `X-Content-Type-Options` to frontend/static/media responses | smoke test: header empty on `/`; nginx config has no `add_header` | Amplifies #2: browsers may sniff an uploaded HTML file and execute it. |
| 5 | **High** | OTP SMS is a stub; it prints the code and always “succeeds” | `accounts/services.py` `send_sms` prints `[SMS] ...`; provider code commented out | Production OTP does not work; codes leak to container logs; users see “sent” when no SMS was sent. |
| 6 | **High** | No HTTPS, no secure cookies, no HSTS, no proxy SSL header | `check --deploy` warnings W004, W008, W012, W016 | Session/JWT exposure on the wire; Django admin CSRF can fail behind a TLS proxy; no HSTS protection. |
| 7 | **High** | SQLite + 3 Gunicorn sync workers for a multi-user service | settings/compose | `database is locked` under concurrent writes; no online backup; not the production plan. |
| 8 | **High** | Media capacity is incompatible with 40 GB SSD | estimate below | 700 users × 3 videos (1–2 min) can exceed 40 GB by a wide margin; S3 is required. |
| 9 | **Medium** | Object storage is integrated locally; production hardening is pending | `django-storages`/`boto3`/`STORAGES`/`AWS_*` configured; `check_storage` verified write/read/signed URL/private access/delete | Local disk is no longer the only storage option; bucket policy, versioning/lifecycle, and VPS rollout still need review. |
| 10 | **High** | User enumeration via login `send-otp` (404 for unknown phone) and duplicate registration messages | `SendOTPView` returns 404; existing tests assert it | Attackers can discover registered phone numbers. |
| 11 | **High** | Verify endpoint has no throttle; only 5 attempts per OTP and a 4-digit code | `verify_otp_code`, no DRF throttles | Brute-force/abuse across many accounts; 4-digit space is small. |
| 12 | **Medium** | Admin teacher list includes staff/superusers | failing test; also documented in `frontend/PROBLEMS.md` | Staff accounts are exposed in the educator list; confusing and unnecessary data exposure. |
| 13 | **Medium** | Registration accepts unknown grade values and creates a teacher with zero grades | failing test | Silent data corruption; broken profile/survey targeting. |
| 14 | **Medium** | 7-day access token, 30-day refresh, no rotation/blacklist/refresh endpoint | `SIMPLE_JWT` settings | Long-lived token theft window; no revocation. |
| 15 | **Medium** | No health endpoint/healthchecks, resource limits, log rotation, or non-root user | compose/Dockerfile/inspect | Hard to operate safely; disk can fill with logs; a bad upload can exhaust RAM. |
| 16 | **Medium** | Unpinned base images and Python dependency ranges | Dockerfiles/requirements | Non-reproducible builds; silent breaking upgrades. |
| 17 | **Medium** | No backups/restore procedure | repo | Data loss risk; SQLite file + media volume are single copies. |
| 18 | **Medium** | No logging/monitoring/error tracking | no `LOGGING`, no Sentry | Failures are invisible; OTP codes are logged by the stub. |
| 19 | **Medium** | Public Swagger/OpenAPI and public admin UI shell | `SERVE_PERMISSIONS=AllowAny`; test `admin template page is public` | API surface disclosure; admin shell exposure (data APIs are still protected). |
| 20 | **Medium** | Frontend `resolveMediaUrl` strips the host from absolute URLs | `frontend/src/api.ts` | S3 migration will break every image/video URL unless the frontend is changed. |
| 21 | **Low** | `backend/templates/admin_panel.rar` is tracked (81 KB) | `git ls-files` | Stray archive in repo/image; may contain old source or secrets. |
| 22 | **Low** | Empty `nginx/default.conf` (0 bytes) | file listing | Dead configuration; confusing. |
| 23 | **Low** | Migrations `0010` and `0011` are untracked | `git status` | Production build from git would miss them. |
| 24 | **Low** | Redundant `0009`/`0010` national-ID alterations; `0004` drops old grade data without a data migration; `0005` adds non-null gender | migration files | Fresh DB is fine; upgrading an old DB needs care. |
| 25 | **Low** | OTP expires after 1 minute; no expired-row cleanup | `create_otp` default | Poor UX; table growth (slow). |
| 26 | **Low** | National ID not validated at registration (plain serializer field) | `RegisterSendOTPSerializer` | Invalid IDs can be stored (profile serializer does apply model validators). |

### Stored-XSS chain (most important security finding)
1. `ReportCreateSerializer.validate_media()` checks only `file.content_type.startswith("image/")`.
2. A file named `payload.html` with `Content-Type: image/png` is accepted and saved under `/media/reports/images/payload.html`.
3. Nginx serves `/media/...` directly and does not send `X-Content-Type-Options: nosniff`.
4. The frontend stores JWTs in `localStorage` and has no CSP.
5. An attacker who gets a victim to open the media URL can run same-origin JavaScript and read the JWT.

This was **confirmed by an automated test**, not just inferred.

---

## 7. Production requirements checklist

Legend: **PASS** = verified by evidence; **FAIL** = confirmed problem; **PARTIAL** = partly implemented/tested; **BLOCKED** = cannot verify here; **NOT IMPLEMENTED** = absent.

### 7.1 Django and security
| Requirement | Status | Evidence / note |
|---|---|---|
| `DEBUG=False` | **PASS** | running env `DJANGO_DEBUG=False`; no W018 |
| Explicit `ALLOWED_HOSTS` | **PARTIAL** | set, but only `localhost,127.0.0.1`; production domain absent |
| CSRF middleware | **PASS** | enabled |
| CSRF trusted origins / secure CSRF cookie | **FAIL** | not set; `check --deploy` W016 |
| CORS configuration | **NOT IMPLEMENTED** | `django-cors-headers` installed but not in middleware/settings; acceptable only for same-origin nginx |
| Secret handling | **FAIL** | `.env` tracked in git; no root `.gitignore` |
| Session cookie secure | **FAIL** | `SESSION_COOKIE_SECURE` not set; W012 |
| HTTPS / reverse-proxy awareness | **FAIL** | no `SECURE_PROXY_SSL_HEADER`, `SECURE_SSL_REDIRECT`, HSTS; W004/W008 |
| File-upload validation | **FAIL** | client `Content-Type` trusted; spoof test failed |
| No development server in production | **PASS** | Gunicorn is the container command |
| Default API permission = authenticated | **PASS** | anonymous `/api/reports/`, `/api/surveys/`, `/api/blogs/`, `/api/tickets/`, `/api/auth/profile/` → 401 |
| Admin API = staff only | **PASS** | teacher → 403; anon → 401 (tests) |
| OTP attempt limiting | **PARTIAL** | 5 attempts per OTP; no verify throttle, no IP/global limit |
| OTP send rate limiting | **PARTIAL** | 1 request/minute/phone; no IP/global limit |
| Swagger/OpenAPI exposure | **PARTIAL** | intentionally public; should be restricted in production |
| Logging / error monitoring | **FAIL** | no `LOGGING`, no error tracker; stub logs OTP codes |
| Password validators | **PASS** | four Django validators configured |
| JWT lifetime/rotation | **PARTIAL** | 7-day access, 30-day refresh, no rotation/blacklist/refresh route |

`manage.py check --deploy` output: 4 warnings (HSTS, SSL redirect, session cookie secure, CSRF cookie secure), 0 errors.

### 7.2 Docker and web serving
| Requirement | Status | Evidence / note |
|---|---|---|
| Production Dockerfiles | **PARTIAL** | frontend multi-stage build; backend slim; both run as root; base images unpinned |
| Gunicorn (or equivalent) | **PASS** | 3 sync workers in CMD |
| Gunicorn production tuning | **PARTIAL** | no timeout/max-requests/access-log/forwarded-IP config |
| React production build via Nginx | **PASS** | multi-stage `npm run build`; `/` returns 200 |
| Internal networking / port exposure | **PASS** | backend `expose` only; frontend publishes 8080 |
| Health checks | **NOT IMPLEMENTED** | none in compose/Dockerfiles; no `/health/` endpoint |
| Restart policy | **PASS** | `unless-stopped` |
| Log rotation | **FAIL** | `json-file` with no `max-size`/`max-file` |
| Resource limits | **FAIL** | `Memory=0`, `NanoCpus=0` |
| Persistent storage | **PASS** | named volumes for SQLite, media, static |
| Non-root containers | **FAIL** | backend `User=` empty (root); frontend nginx runs as root by default |
| Reproducible builds | **FAIL** | `python:3.13-slim`, `node:22-alpine`, `nginx:alpine` unpinned; Python ranges not pinned |
| Secrets not baked into images | **PASS** | `.dockerignore` excludes `.env`; compose uses `env_file` |
| Secrets not in git | **FAIL** | `.env` tracked |

### 7.3 Database
| Requirement | Status | Evidence / note |
|---|---|---|
| Current SQLite works locally | **PASS** | 311 KB DB; all migrations applied; app healthy |
| SQLite write concurrency/locking | **FAIL** (for production) | single writer + 3 Gunicorn workers; no WAL/busy-timeout tuning; no concurrency test run |
| PostgreSQL configured | **NOT IMPLEMENTED** | no `psycopg`, no PG settings, no `DATABASE_URL` |
| PostgreSQL compatibility of schema/queries | **PARTIAL** | no SQLite-specific SQL found; migrations look portable; not executed against PG |
| Migration consistency | **PASS** | `makemigrations --check` → no changes; all applied |
| Migration files tracked | **PARTIAL** | `0010`, `0011` are untracked |
| Migration data safety on upgrade | **PARTIAL** | `0004` removes old grade field without data migration; `0005` adds non-null gender; fresh DB is fine |
| Constraints / uniqueness | **PASS** | unique phone/national ID; survey `unique_together`; verified by tests |
| Backup / restore | **NOT IMPLEMENTED** | no dump/restore jobs or docs |

### 7.4 Object storage
| Requirement | Status | Evidence / note |
|---|---|---|
| S3-compatible support | **PASS (local)** | `django-storages[s3]`, `boto3`, `STORAGES`, and `AWS_*` settings |
| Default storage | **PASS (local)** | `S3Storage` when `STORAGE_BACKEND=s3`; local `FileSystemStorage` fallback |
| Provider configuration | **PASS (local)** | ArvanCloud endpoint/bucket/region verified with `check_storage` |
| Upload/download error handling | **PARTIAL** | storage check covers failures; retries/timeouts for large uploads still need tuning |
| Local vs remote behavior | **PASS** | `resolveMediaUrl` preserves absolute signed URLs; legacy `/media/` remains served |
| File access permissions | **PASS** | private bucket, signed URLs; unsigned access denied in the storage check |
| Accidental-deletion protection | **PARTIAL** | `post_delete` deletes files; no versioning/soft delete |
| Capacity fit for 40 GB SSD | **PASS (with object storage)** | media no longer consumes the VPS disk; see capacity note |

**Capacity estimate (assumption-based):** 700 users × (7 photos + 3 videos). If photos average 3 MB → ~14.7 GB. Videos dominate: at 20 MB/min × 1.5 min × 3 = 90 MB/user → ~63 GB; at 50 MB/video → ~105 GB; at 100 MB/video → ~210 GB. Even the low end exceeds 40 GB once the OS, database, logs, and backups are included. **S3 is mandatory, not optional.**

### 7.5 OTP / SMS
| Requirement | Status | Evidence / note |
|---|---|---|
| Real SMS provider | **NOT IMPLEMENTED** | `send_sms` prints to stdout; sms.ir code commented |
| Credential handling | **FAIL** | API key in tracked `.env` |
| OTP expiration | **PASS** | `expires_at`, `is_expired`; default 1 minute |
| Resend controls | **PARTIAL** | 1/minute per phone; frontend 60 s countdown |
| Abuse/rate limiting | **PARTIAL** | no verify throttle, no IP/global limit, enumeration possible |
| Reuse prevention | **PASS** | login deletes OTP; registration marks verified; tests pass |
| Attempt lockout | **PASS** | 5 attempts then invalidate; test passes |
| Mocked tests | **PASS** | `send_sms` patched; 13 audit tests |
| Provider failure handling | **FAIL** | return value ignored; API reports success on failure |

### 7.6 Nginx, domain, HTTPS
| Requirement | Status | Evidence / note |
|---|---|---|
| Reverse proxy for API/admin | **PASS** | `frontend/nginx.conf` proxies `/api/`, `/admin/`, `/admin-panel/` |
| HTTP→HTTPS redirect / TLS | **NOT IMPLEMENTED** | HTTP only; no certs |
| HSTS / CSP / security headers | **PARTIAL** | Django sends `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin`; no HSTS/CSP; nginx responses lack `nosniff` |
| Upload size limit | **PARTIAL** | nginx 500 MB; app allows 300 MB × 10 files; no timeouts; nginx buffers uploads |
| Proxy/read timeouts | **FAIL** | none set; Gunicorn default 30 s |
| Static caching / compression | **NOT IMPLEMENTED** | no cache headers or gzip config |
| Server token hiding | **FAIL** | `Server: nginx/1.31.8` |
| Domain / DNS | **BLOCKED** | no domain configured |
| TLS certificates / renewal | **NOT IMPLEMENTED** | none |
| Firewall / SSH hardening | **BLOCKED** | not inspected; out of scope |

### 7.7 Frontend
| Requirement | Status | Evidence / note |
|---|---|---|
| Existing test framework | **NOT IMPLEMENTED** | none in `package.json`; no `node_modules` |
| Form validation | **PARTIAL** | phone/OTP length, required text/tag; no file size/count or national-ID format client-side |
| Login/OTP flows | **PARTIAL** | implemented; depends on backend; no refresh flow |
| Loading/success/empty/error states | **PARTIAL** | present in code; not tested |
| API failure handling | **PARTIAL** | translated errors, 401 clears session; no retry/backoff |
| Session expiration | **PARTIAL** | 401 → clear + redirect; no silent refresh |
| Protected routes | **PARTIAL** | client-side hash guard; server enforces API |
| File upload validation | **PARTIAL** | `accept` + `startsWith`; no size/count enforcement before upload |
| Duplicate submission prevention | **PARTIAL** | buttons disabled while loading; no idempotency keys |
| XSS posture | **FAIL** | JWT in `localStorage`; no CSP; public media |
| S3 URL compatibility | **FAIL** | `resolveMediaUrl` strips absolute URL host |

### 7.8 Integration / smoke
| Check | Status | Evidence |
|---|---|---|
| Frontend accessible | **PASS** | `/` → 200 |
| Backend schema/docs | **PASS** | `/api/schema/` → 200; `/api/docs/` → 200 |
| Django admin reachable | **PASS** | `/admin/` → 200 (login page) |
| Static assets served | **PASS** | `/static/admin/css/base.css` → 200 |
| Missing media | **PASS** | 404 |
| Anonymous protected APIs | **PASS** | 401 on reports/surveys/blogs/tickets/profile/admin |
| Invalid/malformed input | **PASS** | 400 |
| Authenticated live smoke | **BLOCKED** | intentionally not performed to avoid writing to the live DB |
| Live upload smoke | **BLOCKED** | intentionally not performed; verified in isolated temp media instead |
| External services mocked | **PASS** | SMS patched in tests |

---

## 8. SQLite and PostgreSQL assessment

### Current SQLite
- File: `/data/db.sqlite3` on a named Docker volume.
- Live size: 311 KB; 1 teacher; 1 report; 4 OTP rows.
- Works correctly for local development and the current tests.
- **Not suitable for production** at the stated target: SQLite allows one writer at a time. With 3 Gunicorn sync workers, concurrent report/ticket/survey/OTP writes can produce `database is locked`. No WAL mode, no explicit busy timeout, no online backup, no replication.
- Migrations are executed automatically on every container start (`migrate` in CMD). This is acceptable for a single instance but fragile for rollbacks/zero-downtime.

### PostgreSQL migration requirements
1. Add a driver (`psycopg[binary]` preferred for Python 3.13, or `psycopg2-binary`).
2. Make `DATABASES` environment-driven (host, port, name, user, password, `CONN_MAX_AGE`, `connect_timeout`, optional `OPTIONS`).
3. Provision PostgreSQL (container or managed). For 2 vCPU/4 GB, tune `shared_buffers` (~512 MB), `work_mem` (~8–16 MB), `max_connections` (~50–100), and keep the DB on fast disk.
4. Run the existing migrations on a **fresh** PostgreSQL database; verify `0011_seed_grades` populates grades.
5. Do **not** expect `migrate` to copy data between SQLite and PostgreSQL. For the 1 existing teacher/1 report, use `dumpdata`/`loaddata` or a small export/import script, then verify M2M grades, OTP rows (probably discard), and media paths.
6. Re-run the full backend suite against PostgreSQL in staging. The suite currently passes on SQLite; PostgreSQL can expose ordering, `distinct`, and locking differences.
7. Add `pg_dump` (daily) + WAL archiving or managed backups; test a restore.
8. Add a health check that verifies DB connectivity (not just HTTP 200).

### Migration history risks (upgrade only)
- `accounts/0004` removes the old `grade` CharField and adds an M2M with no data migration. Any pre-0004 grade values would be lost. Fresh production DB is unaffected.
- `accounts/0005` adds a non-null `gender` with `default=None, preserve_default=False`. It was applied to an empty table here; applying it to a populated old table can fail.
- `accounts/0009` and `0010` both alter `national_id`; redundant but harmless.
- `0011_seed_grades` uses `get_or_create(value=..., defaults={"name": ...})`. If a grade with the same `name` but different `value` already exists, the unique `name` constraint can fail.
- `0010` and `0011` are untracked in git; a clean clone/build would omit them.

**Recommendation:** for the first production cutover, start from a fresh PostgreSQL database and import only the real teacher/report data deliberately. Do not rely on replaying the whole SQLite migration history on a populated legacy DB.

---

## 9. Object-storage readiness

**Status: IMPLEMENTED LOCALLY.** The backend uses `django-storages`/`boto3` against ArvanCloud S3-compatible storage when `STORAGE_BACKEND=s3`. The local round-trip was verified with `python manage.py check_storage` (write, read, signed-URL download, unsigned access denied, delete). VPS rollout is not done yet.

### Implemented
- `django-storages[s3]` and `boto3` dependencies; `STORAGES` configuration with `S3Storage`.
- Environment-driven endpoint, region, bucket, credentials, path-style addressing, and SigV4.
- Private media by default: no public ACL, time-limited signed URLs (`AWS_QUERYSTRING_AUTH=True`).
- Upload prefixes preserved: `reports/images/`, `reports/videos/`, `blogs/`.
- File deletion on `ReportImage`, `ReportVideo`, and `Blog` deletion.
- Frontend `resolveMediaUrl` preserves absolute signed URLs; legacy `/media/` remains available for existing files.

### Remaining production work
- Confirm bucket policy, CORS for the frontend origin, encryption, versioning, and lifecycle rules.
- Add a migration/copy job for existing local media if it must move to the bucket.
- Tune retries/timeouts and consider presigned browser uploads for large videos.
- Repeat `check_storage` against the production bucket during the gated VPS rollout.

### Recommended upload architecture
- Small images (≤ 5–10 MB): direct API upload to Django → S3, with Pillow validation.
- Large videos (tens/hundreds of MB): **presigned PUT directly from browser to S3**, then confirm the object key to Django. This avoids buffering 300 MB through Gunicorn/nginx on a 4 GB VPS.
- Enforce per-user quotas and per-file size limits; reject unsupported types by extension + magic bytes.
- Add a cleanup job for orphaned objects (upload initiated but report not created).

### Capacity
As shown in section 7.4, the 40 GB SSD cannot hold the estimated media. Object storage is required, and the provider’s egress/request costs should be modeled before launch.

**The local bucket was verified with a single tiny object that was deleted immediately. No VPS or production bucket configuration was changed.**

---

## 10. OTP / SMS readiness

**Status: NOT IMPLEMENTED for production.** The only implementation is:

```python
def send_sms(phone_number, message):
    print(f"[SMS] To: {phone_number} | Message: {message}")
```

The sms.ir `POST https://api.sms.ir/v1/send/verify` code is commented out. Callers ignore the return value and always return “OTP sent successfully.”

### Required work
1. Implement the provider call with `timeout`, retry/backoff, and explicit handling of HTTP/non-200/`status != 1`.
2. Return a 5xx/503 to the client when delivery fails; do not claim success.
3. Never print the OTP or full phone number to logs. Log a correlation ID and masked phone.
4. Rate-limit per phone **and** per IP and globally (DRF throttles + cache). Current limits: 1 send/minute/phone, 5 attempts/OTP, 4-digit code, 1-minute expiry.
5. Add resend cooldown (60 s), hourly/daily caps, and lockout after repeated failures.
6. Increase expiry to a practical 2–5 minutes; clean up expired rows.
7. Add monitoring/alerts for provider errors and delivery rate.
8. Rotate the SMS API key; remove it from git.
9. Test exclusively with a mocked provider; never send real SMS in tests or audits.
10. Estimate cost/volume for ~700 users and set a spending cap.

### Existing strengths
- OTP reuse prevention works (login deletes; registration marks verified).
- 5-attempt lockout works.
- `send_sms` is mocked in tests, and the OTP logic is covered.
- Phone normalization (`+98` → `0…`) is implemented and tested.

---

## 11. Docker, Gunicorn, Nginx, domain, and HTTPS readiness

### Docker
**PARTIAL.** Good: two-service compose, named volumes, `restart: unless-stopped`, backend not published, `.dockerignore` excludes `.env`/DB/media. Gaps: root user, unpinned images, no healthchecks, no resource limits, no log rotation, no secrets manager, migrations in the startup command, no separate production compose override.

### Gunicorn
**PASS (used), PARTIAL (hardened).** 3 sync workers is reasonable for 2 vCPU. Add: `--timeout`, `--graceful-timeout`, `--max-requests`/`--max-requests-jitter`, access/error logs, `--forwarded-allow-ips`, and run as a non-root user. Consider `gthread` workers if S3/SMS I/O dominates.

### Nginx
**PARTIAL.** It correctly serves the React build and proxies API/admin. Missing: TLS, HTTP→HTTPS redirect, HSTS, CSP, `nosniff` on static/media, `server_tokens off`, gzip/brotli, static caching, proxy timeouts, request-body handling for large uploads, and rate limiting on auth endpoints. `client_max_body_size 500M` is too high for a 4 GB VPS unless uploads are presigned. `nginx/default.conf` is empty and should be removed.

### Domain / HTTPS
**NOT IMPLEMENTED / BLOCKED.** No domain, DNS, certificate, or TLS configuration exists. Required: DNS A/AAAA records, Let's Encrypt (certbot) or a TLS-terminating proxy with auto-renewal, ports 80/443 open, SSH key-only, firewall, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SECURE_PROXY_SSL_HEADER`, `SECURE_SSL_REDIRECT`, HSTS after validation, and secure cookies.

### Admin exposure
Django admin is reachable at `/admin/` and the React admin shell at `/admin-panel/`. The data APIs require `is_staff`, but the shell and the Django login page are public. Consider restricting `/admin/` by IP/VPN, adding rate limiting, and not exposing the admin shell to unauthenticated users.

---

## 12. Frontend assessment

- **No automated tests** and no test framework. This is a major gap for a production release.
- Auth flow: phone → OTP → JWT in `localStorage`; 401 clears tokens and redirects. No refresh-token flow, no token rotation.
- Client-side guards are UX only; the server correctly enforces authorization.
- Upload UI accepts `image/*,video/*`, filters by `file.type`, but does not enforce count or size before upload. Server enforces 10 files / 300 MB each.
- `resolveMediaUrl` strips the host from absolute URLs — incompatible with S3.
- No CSP; JWT in `localStorage`; public media — the stored-XSS chain is realistic.
- Error messages are translated and generally do not leak stack traces.
- Duplicate submission is mitigated by disabled buttons, not by idempotency keys.

**Recommended:** add Vitest + React Testing Library, test auth/OTP forms, upload validation, error/loading/empty states, route guards, and 401 handling. Keep it lightweight; no browser E2E is required for the first pass.

---

## 13. Verified facts vs assumptions and recommendations

### Verified facts
- The two containers were running and healthy at audit time; frontend `/` returned 200; schema/docs returned 200.
- Backend uses Gunicorn with 3 workers; `DEBUG=False`; `ALLOWED_HOSTS=localhost,127.0.0.1`.
- 106 backend tests ran on an in-memory test DB; 103 passed; 3 failed as listed.
- The live SQLite DB size/mtime and media file count did not change during testing.
- `.env` is tracked in git and contains secret material.
- Upload content-type spoofing is accepted (test evidence).
- Admin teacher list includes staff (test evidence).
- Unknown registration grade is accepted (test evidence).
- No S3/storages/boto/AWS settings, no psycopg/PostgreSQL settings, no DRF throttles, no `LOGGING`, no secure-cookie/HSTS/proxy settings.
- `manage.py check --deploy` produced 4 warnings.
- `makemigrations --check` produced no changes; all migrations are applied in the live DB.
- Migrations `0010` and `0011` are untracked.
- Frontend/static responses lack `X-Content-Type-Options`; the `Server` header exposes the nginx version.
- No frontend test framework is present.

### Assumptions
- Average photo size (~3 MB) and video bitrate (20–100 MB per 1–2 minute video) are estimates, not measured.
- The 700 registered users will not all be concurrent; concurrency is unknown.
- The S3-compatible provider supports the S3 API features needed (presigned URLs, multipart, path-style).
- The VPS will run PostgreSQL on the same host; a managed DB is an alternative.
- The existing 2 media files are representative only in count, not in size distribution.

### Recommendations (not yet implemented)
- Use presigned uploads for videos; keep images on the API path.
- Use private S3 objects + signed URLs.
- Start production on a fresh PostgreSQL DB; import the 1 teacher/1 report deliberately.
- Add a dedicated `/health/` endpoint and Docker healthchecks.
- Add CI (lint, tests, build, dependency/secret scanning) before the first deploy.
- Do not claim 700-user capacity without load-test evidence.

---

## 14. VPS load-testing plan (planning only — NOT executed)

> **This plan must not be executed until the application is deployed to a staging environment with PostgreSQL, S3 (test bucket), and mocked SMS, and the user explicitly approves each stage.** Do not load-test the current SQLite local deployment and treat the result as production capacity.

### 14.1 Preconditions
- Staging deployment on the target VPS class (2 vCPU / 4 GB / 40 GB) or an equivalent staging host.
- PostgreSQL (not SQLite), Gunicorn behind Nginx, S3 test bucket, SMS provider mocked or disabled.
- Monitoring enabled: CPU, RAM, disk, network, PostgreSQL (`pg_stat_activity`, locks, slow queries), Nginx, container stats.
- Backups/snapshot of staging before the test.
- Dedicated test accounts and test data; no real users, no real SMS, no paid storage requests beyond the approved test bucket.
- Run off-peak; one load generator at a time; obtain approval before each ramp stage.

### 14.2 Workload model (based on actual workflows)
Suggested mix for authenticated teacher traffic:
| Workload | Share | Endpoints |
|---|---:|---|
| Dashboard reads | 40% | `GET /api/auth/profile/`, `/api/reports/tags/`, `/api/reports/points/`, `/api/blogs/`, `/api/tickets/`, `/api/surveys/` |
| Report browsing | 20% | `GET /api/reports/`, `GET /api/reports/{id}/` |
| Survey browsing | 10% | `GET /api/surveys/`, `GET /api/surveys/{id}/` |
| Ticket list/create | 10% | `GET /api/tickets/`, `POST /api/tickets/` (small, cleaned up) |
| Report create | 10% | `POST /api/reports/` with a small image or no media |
| Survey submit | 5% | `POST /api/surveys/{id}/submit/` |
| Admin reads | 5% | `GET /admin-panel/api/teachers/`, `/reports/` (few admin tokens) |

OTP send/verify should be tested **separately at low rate** with a mocked provider, because real SMS costs money and is rate-limited. Pre-issue JWTs for the main scenarios.

### 14.3 Scenarios and gates
1. **Baseline:** 5 virtual users, 5 minutes, 1–3 s think time. Establish p50/p95 and error rate.
2. **Ramp:** 10 → 25 → 50 VUs, 5–10 minutes each, 2–5 minute ramp. Review results after each stage.
3. **100 VUs:** only after the 50-VU results are reviewed and approved. Use a separate load-generation machine if the local machine is unstable or the network is the bottleneck.
4. **Stress test (separate, explicitly labeled):** 150–200 VUs or until failure, on **staging only**, with additional approval. Never run it against production.

**700 registered users ≠ 700 concurrent users.** Capacity claims require evidence from the approved stages.

### 14.4 Authentication and test data
- Create dedicated `loadtest_` teacher accounts (e.g., 20–50) via a management command; pre-generate JWT access tokens.
- Use `Authorization: Bearer <token>`; avoid OTP send for the main scenarios.
- Use a dedicated `loadtest` tag and survey; prefix reports/tickets for cleanup.
- Never use real user accounts or real phone numbers.
- Mock the SMS provider; do not send real messages.
- Use the S3 **test** bucket only; clean up objects after the run.

### 14.5 Metrics
- Latency: p50, p95, p99 per endpoint (reads, writes, uploads).
- Throughput: requests/second, successful writes/second.
- Errors: HTTP 4xx/5xx rate, timeouts, connection errors.
- VPS: CPU, RAM, disk I/O, disk free, network; container stats.
- PostgreSQL: active connections, locks, slow queries, deadlocks.
- Nginx: active connections, upstream response time, 5xx.
- S3: upload/download throughput, latency, error rate.
- Gunicorn: worker utilization, timeouts, restarts.

### 14.6 Stop conditions
Abort the current stage immediately if any of the following occurs:
- 5xx rate > 1% or error rate > 5% overall.
- p95 > 1 s for reads or > 3 s for writes/uploads.
- CPU > 85% sustained for 2 minutes.
- RAM > 90% or OOM/container restart.
- Disk free < 10 GB.
- PostgreSQL lock waits/timeouts or deadlocks.
- Any sign of data corruption or unexpected writes to real data.

Stop the load generator, not the application containers, and record the state before any recovery action.

### 14.7 Upload/download tests (separate)
- Small image (1 MB) via the API; measure latency/error rate at 5–10 concurrent uploads.
- Medium video (10–20 MB) via presigned upload if implemented; measure throughput and S3 errors.
- Avoid 300 MB files in the first pass; avoid filling disk; clean up objects.
- Verify that concurrent uploads do not exhaust Gunicorn memory or Nginx temp disk.

### 14.8 SQLite vs PostgreSQL
- Run the load test only against PostgreSQL staging. SQLite results are not representative.
- If SQLite must be tested for comparison, expect `database is locked` and do not use the result to size production.
- Re-run the 106-test suite against PostgreSQL before load testing.

### 14.9 Tooling
- Prefer **k6** (lightweight, scriptable, arrival-rate scenarios) or Locust.
- Run from the local machine for 5–50 VUs only if CPU/RAM/network remain stable; otherwise use a separate cloud VM.
- Rate-limit the generator (`--rps`/arrival rate) and run one generator at a time.
- Store results as JSON/CSV for the report.

### 14.10 Cleanup
- Delete `loadtest_` reports/tickets/submissions/points via a management command.
- Delete test S3 objects.
- Restore the staging DB snapshot if needed (staging only).
- Verify no real data was touched.
- Keep logs and result files for the report.

---

## 15. Prioritized remediation checklist

### P0 — before any public exposure
1. **Rotate and remove secrets**: remove `.env` from git, add a root `.gitignore`, rotate `DJANGO_SECRET_KEY` and `SMS_IR_API_KEY`, inject secrets via the host/secret manager.
2. **Implement real SMS** with timeout/retry/failure handling; stop printing OTP codes; return 503 on provider failure.
3. **Fix upload security**: validate extension + magic bytes/Pillow; store safe extensions; add `nosniff`; add CSP; make media private (signed URLs) or serve from a separate domain; add `Content-Disposition` for untrusted files.
4. **Add HTTPS/domain** and secure settings: `SECURE_PROXY_SSL_HEADER`, `SECURE_SSL_REDIRECT`, HSTS, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `CSRF_TRUSTED_ORIGINS`, production `ALLOWED_HOSTS`.
5. **Migrate to PostgreSQL**; add backups and test a restore.
6. **Implement S3 storage** (private bucket, presigned uploads for video); update frontend URL handling; plan capacity/cost.
7. **Add health endpoint + Docker healthchecks**, resource limits, log rotation, non-root users, pinned images/dependencies.
8. **Fix confirmed bugs**: reject unknown grades; exclude staff/superusers from the teacher list; commit migrations `0010`/`0011`; remove `admin_panel.rar`.
9. **Add rate limiting** for OTP send/verify and admin login; add per-IP/global limits; reduce user enumeration.

### P1 — before launch / first weeks
10. JWT: shorter access token, refresh endpoint, rotation/blacklist, consider HttpOnly cookies instead of `localStorage`.
11. Restrict Swagger/OpenAPI and admin shell in production; add security headers/CSP at Nginx.
12. Add structured logging, error tracking, uptime/latency alerts.
13. Add frontend test framework and tests; add backend coverage in CI.
14. Add CI: lint, tests, build, dependency/secret scanning.
15. Fix N+1 queries and pagination for admin teachers/media; add DB indexes where needed.
16. Add idempotency/duplicate-submission protection for reports/tickets.
17. Align Nginx/Gunicorn timeouts and upload limits; disable request buffering for large uploads or use presigned URLs.
18. Write the SQLite→PostgreSQL data migration/verification plan for the existing 1 teacher/1 report.
19. Privacy: media access control, retention policy, PII handling in admin/logs.

### P2 — hardening and scale
20. Gunicorn/DB tuning; caching for tags/blogs/surveys.
21. Execute the gated load-test plan; document capacity with evidence.
22. Backup/restore drills and disaster recovery.
23. Dependency pinning/update policy and vulnerability scanning.
24. Accessibility/i18n review; remove legacy unused templates/assets if confirmed unused.

---

## 16. Exact files changed by this audit

### Added
- `backend/accounts/tests_audit.py`
- `docs/production-readiness-audit.md`

### Replaced (were stubs)
- `backend/reports/tests.py`
- `backend/survey/tests.py`
- `backend/tickets/tests.py`
- `backend/blogs/tests.py`
- `backend/adminpanel/tests.py`

### Not changed by this audit
- All production code, settings, Dockerfiles, compose, nginx config, dependencies, migrations, and the live database.
- The following files were already modified in the working tree before the audit and were left as-is:
  `backend/accounts/serializers.py`, `backend/accounts/tests.py`, `backend/accounts/views.py`, `frontend/nginx.conf`, `frontend/src/api.ts`, `frontend/src/views/AdminView.tsx`, `frontend/src/views/DashboardView.tsx`.
- Untracked files that already existed: `backend/accounts/migrations/0010_alter_teacher_national_id.py`, `backend/accounts/migrations/0011_seed_grades.py`.

> `docker cp` was used to place the new test files into the running backend container for execution. That does not modify host production files and is lost on container recreation.

---

## 17. Remaining production-readiness gaps (summary)

- Secrets in git; no secret manager.
- No real SMS provider; OTP is non-functional in production.
- Upload validation and media access control are unsafe.
- No HTTPS/domain/secure settings.
- SQLite is not production-ready; PostgreSQL is not implemented or tested.
- S3 storage is not implemented; media capacity exceeds the 40 GB SSD.
- No backups/restore, health checks, resource limits, log rotation, monitoring, or CI.
- No frontend tests; no coverage measurement.
- JWT lifetime/rotation and OTP throttling need hardening.
- Admin UI/Swagger exposure and user enumeration need review.
- Untracked migrations and stray files must be cleaned up before the production build.

---

## 18. Proposed next steps (awaiting approval)

1. Review this report and the 3 failing tests; approve fixes.
2. Rotate secrets and remove `.env` from git (P0).
3. Stand up a **staging** environment with PostgreSQL and an S3 test bucket; run the 106-test suite against PostgreSQL.
4. Implement SMS, upload validation, media access control, and HTTPS in that order.
5. Add health checks, backups, resource limits, and monitoring.
6. Only then execute the load-test plan, starting with the 5-VU baseline, and review results before each ramp stage.
7. Do not run any VPS load test or stress test without explicit approval.

**No fixes, infrastructure changes, or load tests have been performed. The audit stops here.**
