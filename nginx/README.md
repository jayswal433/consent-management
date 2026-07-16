# DPDP Consent Management API — Deployment Files

This directory contains production-ready configuration files and deployment automation for the DPDP Consent Management FastAPI microservice.

## Files Included

### 1. `nginx.conf` (322 lines)
**Production-hardened reverse proxy configuration**

- TLS 1.2/1.3 with ECDHE-first cipher suite
- HTTP → HTTPS redirect (port 80 → 443)
- Rate limiting zones: auth (10/min), consent (60/min), global (1000/min)
- Security headers: HSTS, CSP, X-Frame-Options, Referrer-Policy
- Upstream: FastAPI on 127.0.0.1:8008 with keepalive pooling
- Public CORS for `/sdk/cmp.js` (CMP widget)
- Client body size limited to 64 KB (DPDP compliance)
- Access/error logging with structured format

**Installation:**
```bash
sudo cp nginx.conf /etc/nginx/nginx.conf
sudo sed -i 's.consent.yourdomain.com/YOUR_DOMAIN.com/g' /etc/nginx/nginx.conf
sudo nginx -t
sudo systemctl reload nginx
```

### 2. `consent-api.service` (22 lines)
**Systemd unit file for FastAPI app lifecycle management**

- Type: simple (single process)
- User: consent (dedicated service account)
- Auto-restart on crash with exponential backoff
- Security isolation: PrivateTmp, NoNewPrivileges, ProtectSystem
- Graceful shutdown timeout: 120 seconds (Uvicorn default)
- Logging to systemd journal

**Installation:**
```bash
sudo cp consent-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable consent-api
sudo systemctl start consent-api
```

### 3. `QUICK_START.md` (80 lines)
**5-minute deployment guide**

Quick reference for:
- Copying Nginx config and generating SSL certificate
- Creating systemd service and starting app
- Verifying health checks
- Viewing logs
- Key Nginx routes and their rate limits
- Critical settings and encryption key generation
- Rate limiting debug commands
- Troubleshooting common issues
- Security checklist

**Use this when you need the fastest path to production.**

### 4. `PRE_DEPLOYMENT_CHECKLIST.md` (250 lines)
**Comprehensive pre-flight checklist for operations teams**

Sections:
- Infrastructure provisioning (2 hours)
- Application setup (1 hour)
- Configuration & secrets management (1 hour)
- Database setup (30 minutes)
- Systemd service verification (30 minutes)
- Nginx reverse proxy setup (1 hour)
- Security headers verification (20 minutes)
- Rate limiting verification (10 minutes)
- Logging configuration (15 minutes)
- Backup & recovery testing (30 minutes)
- Monitoring & observability setup (optional, 30 minutes)
- Post-deployment verification (20 minutes)
- Rollback plan documentation
- Go/No-go decision sign-off
- Post-deployment follow-up (24 hours)

**Use this for formal deployments with audit/compliance requirements.**

---

## Related Documentation

See `docs/DEPLOYMENT.md` for the **complete 1220-line deployment playbook** with:
- Detailed system preparation (SSH hardening, Fail2Ban, firewall)
- Application deployment (git clone, Poetry, environment setup)
- Database setup with Alembic migrations
- Encryption key generation and Secrets Manager integration
- Systemd service creation and troubleshooting
- Nginx configuration with Certbot SSL certificate generation
- Health checks and connectivity testing
- Log management and rotation
- Backup strategy with S3 integration
- Security hardening checklist (15 items)
- Rollback procedures (code, database, schema)
- Environment-specific configuration table
- Troubleshooting (15+ common issues)
- Monitoring & observability (CloudWatch, ELK, APM)

---

## Architecture Overview

```
Internet
    |
    | HTTPS (443)
    v
Nginx Reverse Proxy (nginx.conf)
    | Rate limiting zones
    | Security headers (HSTS, CSP, X-Frame-Options)
    | Gzip compression
    |
    v Proxy pass
127.0.0.1:8008 (FastAPI + Uvicorn)
    |
    | 4 workers (auto-scaled by CPU count)
    |
    v
MySQL (localhost:3306) + Redis (6379, optional)
```

---

## Key Configuration Points

| Setting | Value | Purpose |
|---------|-------|---------|
| **TLS Min** | 1.2 | DPDP §8 encryption requirement |
| **Cipher Suite** | ECDHE-first | Forward secrecy, modern clients |
| **HSTS Max-Age** | 31536000s (1 year) | Force HTTPS, prevent SSL stripping |
| **Auth Rate Limit** | 10/min | Prevent brute force attacks |
| **Consent Rate Limit** | 60/min | Prevent API abuse |
| **Global Rate Limit** | 1000/min | Catch-all per OWASP |
| **Body Size Limit** | 64 KB | DPDP data minimization |
| **Session Cache** | Shared 10MB | TLS performance optimization |
| **Upstream Keepalive** | 32 connections | Connection pooling |
| **Workers** | `cpu_count()` | Auto-scale to server capacity |
| **Graceful Shutdown** | 120s | Uvicorn request draining |

---

## Deployment Timeline

| Phase | Time | Owner |
|-------|------|-------|
| Infrastructure setup | 2 hours | DevOps/Platform |
| Application deployment | 1 hour | DevOps |
| Database migrations | 30 min | DBA/DevOps |
| Systemd service | 30 min | DevOps |
| Nginx + SSL | 1 hour | DevOps/Security |
| Health checks | 20 min | QA/DevOps |
| Security verification | 20 min | Security team |
| Monitoring setup (optional) | 30 min | Observability team |
| **Total** | **~5.5 hours** | **Team** |

---

## Compliance Coverage

- ✓ **DPDP Act 2023 § 6:** Encryption (DEK, HMAC, JWT keys)
- ✓ **DPDP Act 2023 § 8:** TLS 1.2+, 64KB payload limit
- ✓ **OWASP Top 10 (2021):** Rate limiting, HTTPS, CSP, input validation
- ✓ **ISO/IEC 27001:** Key rotation, access control, logging
- ✓ **CIS Benchmarks:** SSH hardening, firewall, least privilege

---

## Support

**For deployment help:**
1. Start with `QUICK_START.md` for a 5-minute setup
2. Use `PRE_DEPLOYMENT_CHECKLIST.md` for formal deployments
3. Refer to `docs/DEPLOYMENT.md` for comprehensive guidance
4. Check nginx.conf comments for individual directive explanations

**For troubleshooting:**
- See section 14 of `docs/DEPLOYMENT.md` for 6+ common issues and solutions
- View systemd logs: `sudo journalctl -u consent-api -f`
- View Nginx logs: `sudo tail -f /var/log/nginx/{access,error}.log`

**For security concerns:**
- Review section 11 of `docs/DEPLOYMENT.md` (security hardening checklist)
- Verify section 13 (environment-specific configuration)
- Check nginx.conf security headers section

---

**Version:** 1.0  
**Last Updated:** 2026-05-22  
**Maintained By:** DevOps Team
