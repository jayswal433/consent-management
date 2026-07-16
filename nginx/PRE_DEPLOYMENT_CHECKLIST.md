# Pre-Deployment Checklist

Complete all items below before deploying to production.

---

## Infrastructure (2 hours)

- [ ] **Server provisioned:** Ubuntu 22.04 LTS, 2+ vCPU, 4 GB RAM, 20 GB disk
- [ ] **Domain registered:** DNS propagated for `api.consent.yourdomain.com`
- [ ] **Database created:** MySQL 8.0 running, user `consent_app` with SELECT/INSERT/UPDATE/DELETE/ALTER grants
- [ ] **Redis optional:** If using token blacklist, Redis 7.x running and accessible on localhost:6379
- [ ] **AWS account (optional):** S3 bucket for backups, Secrets Manager access (if using)
- [ ] **Firewall configured:** UFW rules: SSH (22), HTTP (80), HTTPS (443), all others denied
- [ ] **SSH keys deployed:** No password-based SSH allowed, key-only auth for root+user

---

## Application Setup (1 hour)

- [ ] **Repository cloned:** `git clone` complete, latest commit on target branch verified
- [ ] **Python 3.12 installed:** `python3.12 --version` shows 3.12.x
- [ ] **Virtual environment created:** `/opt/consent-api/.venv` exists and activation works
- [ ] **Dependencies installed:** `poetry install --no-dev` completes without errors
- [ ] **Imports verified:** `python -c "from app.api.server import app"` succeeds
- [ ] **Database migrations ready:** Alembic revision created and migration scripts reviewed
- [ ] **Tests passing locally:** `pytest` or `python -m pytest` runs with 0 failures (optional but recommended)

---

## Configuration & Secrets (1 hour)

- [ ] **`.env` file created:** `/opt/consent-api/.env` present with all required variables
- [ ] **Database credentials tested:** `mysql -u consent_app -p -h 127.0.0.1 consent_db -e "SELECT 1;"` succeeds
- [ ] **Encryption keys generated:** `DPDP_DEK_HEX`, `DPDP_HMAC_KEY_HEX`, `JWT_SECRET_KEY` all present (256+ bits)
- [ ] **Keys in Secrets Manager (prod):** If prod, verify keys stored in AWS Secrets Manager or Vault (not in `.env`)
- [ ] **AWS credentials configured:** If using S3, `aws s3 ls` works without interactive prompts
- [ ] **SMTP credentials verified:** `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` are valid
- [ ] **File permissions locked down:** `.env` chmod 600, owned by `consent:consent`

---

## Database (30 minutes)

- [ ] **Database schema created:** `mysql -u consent_app -p consent_db -e "SHOW TABLES;" | wc -l` returns > 0
- [ ] **Migrations run:** `alembic current` shows latest revision applied
- [ ] **Backup user created:** `consent_backup` user exists with SELECT, LOCK TABLES grants (optional)
- [ ] **Test data (optional):** Sample user/consent records inserted if needed for testing
- [ ] **Indexes verified:** Run `SHOW INDEX FROM consent_forms;` and confirm key columns are indexed

---

## Systemd Service (30 minutes)

- [ ] **Service file deployed:** `/etc/systemd/system/consent-api.service` exists and is readable
- [ ] **Service syntax valid:** `systemctl status consent-api --no-pager` shows no parsing errors
- [ ] **Service enabled:** `systemctl is-enabled consent-api` returns "enabled"
- [ ] **Service starts:** `systemctl start consent-api` succeeds, no errors in `journalctl -u consent-api -n 20`
- [ ] **Port listening:** `ss -tuln | grep 8008` shows `LISTEN 127.0.0.1:8008`
- [ ] **Health check passes:** `curl http://127.0.0.1:8008/health` returns 200 OK

---

## Nginx Reverse Proxy (1 hour)

- [ ] **Nginx config copied:** `/etc/nginx/nginx.conf` contains full config (not just snippet)
- [ ] **Domain substituted:** `grep api.consent.yourdomain.com /etc/nginx/nginx.conf` finds YOUR domain, not placeholder
- [ ] **Config syntax valid:** `nginx -t` returns "syntax ok" and "configuration successful"
- [ ] **SSL certificate obtained:** `ls /etc/letsencrypt/live.consent.yourdomain.com/` shows fullchain.pem, privkey.pem
- [ ] **Certbot renewal tested:** `certbot renew --dry-run` completes without errors
- [ ] **Nginx reloaded:** `systemctl reload nginx` completes cleanly
- [ ] **HTTPS endpoint accessible:** `curl -I https:/.consent.yourdomain.com/` returns 404 (expected for `/`)
- [ ] **HTTP redirects to HTTPS:** `curl -I http:/.consent.yourdomain.com/` returns 301 Location: https://

---

## Security Headers Verification (20 minutes)

```bash
# Test command:
curl -I https:/.consent.yourdomain.com/v1/docs

# Verify all headers present:
```

- [ ] **HSTS header present:** `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
- [ ] **X-Frame-Options set:** `X-Frame-Options: DENY`
- [ ] **X-Content-Type-Options set:** `X-Content-Type-Options: nosniff`
- [ ] **CSP header present:** `Content-Security-Policy: default-src 'none'`
- [ ] **Referrer-Policy set:** `Referrer-Policy: no-referrer`
- [ ] **Server version hidden:** No `Server: nginx/x.x.x` header in response

---

## Rate Limiting Verification (10 minutes)

```bash
# Test auth rate limit (should allow 10/min):
for i in {1..15}; do
  curl -s -o /dev/null -w "Auth req $i: %{http_code}\n" \
    https:/.consent.yourdomain.com/v1/auth/login
done

# Expected: requests 1-10 = 200/401, requests 11-15 = 429
```

- [ ] **Auth limit enforced:** Requests 1-10 succeed, 11-15 return 429 Too Many Requests
- [ ] **Consent limit enforced:** 60/min zone allows 60 requests, blocks 61st with 429
- [ ] **Global limit enforced:** 1000/min zone allows 1000 requests, blocks 1001st with 429
- [ ] **Burst buffer working:** Requests up to limit + burst allowed within window

---

## Logging Configuration (15 minutes)

- [ ] **Log directory created:** `/var/log/consent-api/` exists, owned by `consent:consent`
- [ ] **Logs being written:** `ls -la /var/log/consent-api/` shows files with recent timestamps
- [ ] **Logrotate configured:** `/etc/logrotate.d/consent-api` exists with `daily`, `rotate 30`, `compress`
- [ ] **Logrotate tested:** `logrotate -f /etc/logrotate.d/consent-api` completes without errors
- [ ] **Nginx logs accessible:** `/var/log/nginx/access.log` and `/var/log/nginx/error.log` present
- [ ] **Application logs readable:** `journalctl -u consent-api -n 50` shows recent entries

---

## Backup & Recovery (30 minutes)

- [ ] **Backup script created:** `/usr/local/bin/backup-consent-db.sh` executable and tested
- [ ] **Backup runs successfully:** Manual run produces `.sql.gz` file in backup directory
- [ ] **S3 upload works (if used):** `aws s3 ls s3://consent-api-prod-backups/` shows recent backup file
- [ ] **Backup encryption verified (if used):** `aws s3api head-object --bucket consent-api-prod-backups --key ...` shows encryption metadata
- [ ] **Restore test passed:** Backup restored to temporary database and schema validated
- [ ] **Cron job scheduled:** `crontab -l` shows backup job at 3 AM daily

---

## Monitoring & Observability (optional, 30 minutes)

- [ ] **CloudWatch agent installed (AWS):** `systemctl status amazon-cloudwatch-agent` is active
- [ ] **Datadog agent installed (Datadog):** `systemctl status datadog-agent` is active (if using)
- [ ] **Application logs sent to central log system:** ELK/Datadog dashboard shows recent logs
- [ ] **Metrics being collected:** CloudWatch/Datadog dashboard shows CPU, memory, request counts
- [ ] **Alerts configured:** PagerDuty/Slack/OpsGenie integration verified for key metrics

---

## Post-Deployment Verification (20 minutes)

```bash
# Run these commands after everything is deployed:
```

- [ ] **Service is running:** `systemctl is-active consent-api` returns "active"
- [ ] **Listening on correct port:** `ss -tuln | grep 8008` shows LISTEN 127.0.0.1:8008
- [ ] **Nginx is running:** `systemctl is-active nginx` returns "active"
- [ ] **No errors in app logs:** `journalctl -u consent-api -n 100 | grep -i error` returns empty
- [ ] **No errors in Nginx logs:** `grep " 5[0-9][0-9] " /var/log/nginx/error.log | wc -l` returns 0 or very low count
- [ ] **Health endpoint returns 200:** `curl -s https:/.consent.yourdomain.com/health | jq .status`
- [ ] **API docs accessible:** `curl -s https:/.consent.yourdomain.com/docs | head -20` returns HTML
- [ ] **Database connection working:** `curl -s https:/.consent.yourdomain.com/v1/health/db | jq .` shows database status
- [ ] **Rate limiting active:** Manual 429 response received after threshold (tested above)
- [ ] **HTTPS certificate valid:** `openssl s_client -connect api.consent.yourdomain.com:443 -servername api.consent.yourdomain.com 2>/dev/null | grep "Verify return code"` shows `0 (ok)`

---

## Rollback Plan (document before deployment)

- [ ] **Current commit recorded:** `git rev-parse HEAD > /var/backups/rollback.txt`
- [ ] **Database backup taken:** `mysqldump consent_db | gzip > /var/backups/consent_db_pre_deploy.sql.gz`
- [ ] **Nginx config backed up:** `cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup`
- [ ] **Rollback steps documented:** Team knows how to revert code, downgrade database, restart service
- [ ] **Rollback tested (optional):** Simulated rollback in dev environment to verify procedure

---

## Go/No-Go Decision

**Date:** ________________  
**Deployment Lead:** ________________  
**All checklist items complete?** ☐ YES ☐ NO

**Sign-off:**

- [ ] Infrastructure team: ________________
- [ ] Application team: ________________
- [ ] Security team: ________________
- [ ] DevOps team: ________________

**Notes/Exceptions:**

```
_________________________________________________________________

_________________________________________________________________
```

---

## Post-Deployment Follow-up (24 hours)

- [ ] Error rates normal (< 1% 5xx errors)
- [ ] Response times acceptable (p95 < 500ms)
- [ ] No suspicious access patterns in logs
- [ ] All health checks passing
- [ ] Backup job ran successfully
- [ ] Monitoring alerts (if configured) all green

---

**Print this checklist and complete it on paper before deploying. Keep a signed copy in version control.**
