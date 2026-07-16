# Nginx + Systemd Quick Start

**Deploy in 5 minutes:**

### 1. Copy Nginx Config
```bash
sudo cp nginx/nginx.conf /etc/nginx/nginx.conf
sudo sed -i 's.consent.yourdomain.com/YOUR_DOMAIN.com/g' /etc/nginx/nginx.conf
sudo nginx -t
sudo systemctl reload nginx
```

### 2. Generate SSL Certificate
```bash
sudo certbot --nginx -d YOUR_DOMAIN.com --email admin@yourdomain.com --agree-tos
```

### 3. Create Systemd Service
```bash
sudo cp docs/consent-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable consent-api
sudo systemctl start consent-api
```

### 4. Verify Health
```bash
curl https://YOUR_DOMAIN.com/health
curl -I https://YOUR_DOMAIN.com/  # Check HSTS header
```

### 5. View Logs
```bash
sudo journalctl -u consent-api -f
sudo tail -f /var/log/nginx/access.log
```

---

## Key Nginx Routes

| Path | Rate Limit | Purpose |
|------|-----------|---------|
| `/v1/auth/*` | 10/min | Login, registration (strict) |
| `/v1/consents*` | 60/min | Consent operations (moderate) |
| `/v1/*` | 1000/min | All other API routes (global) |
| `/sdk/cmp.js` | CORS open | Public CMP widget script |
| `/docs` | 1000/min | Swagger UI (optional: IP restrict) |

---

## Critical Settings

- **TLS:** 1.2 + 1.3 only (no downgrade)
- **Cipher Suite:** ECDHE-first, no weak ciphers
- **HSTS:** 1 year max-age, preload enabled
- **CSP:** `default-src 'none'` (strict by default)
- **Session Cache:** Shared 10MB, 10-minute timeout
- **Gzip:** Enabled for JSON (min 1KB)
- **Upstream:** 127.0.0.1:8008 with keepalive 32
- **Body Size:** 64 KB (DPDP limit)

---

## Systemd Service File Template

See `docs/DEPLOYMENT.md` section 6.1 for the complete service unit file.

Key line:
```ini
ExecStart=/opt/consent-api/.venv/bin/python asgi.py --env prod
```

This automatically sets `workers = cpu_count()` (4 on most servers).

---

## Encryption Key Generation

**CRITICAL:** Do NOT commit keys to git. Use AWS Secrets Manager.

```bash
# Generate DEK (Data Encryption Key)
python3 -c "import os; print('DPDP_DEK_HEX=' + os.urandom(32).hex())"

# Generate HMAC key
python3 -c "import os; print('DPDP_HMAC_KEY_HEX=' + os.urandom(32).hex())"

# Generate JWT secret
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(64))"
```

Store in `.env` (dev only) or AWS Secrets Manager (production).

---

## Backup (Daily)

```bash
# Test backup
mysqldump -u consent_app -p consent_db | gzip > /tmp/backup_$(date +%Y%m%d).sql.gz

# Upload to S3
aws s3 cp /tmp/backup_*.sql.gz s3://consent-api-prod-backups/daily/
```

---

## Rate Limiting Debug

```bash
# Simulate 15 auth requests (limit is 10/min)
for i in {1..15}; do
  curl -s -o /dev/null -w "Request $i: %{http_code}\n" \
    https:/.consent.yourdomain.com/v1/auth/login
done

# Expect: 1-10 = 200/401, 11-15 = 429 (Too Many Requests)
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| 502 Bad Gateway | Check: `curl http://127.0.0.1:8008/health` |
| Certificate expired | Run: `sudo certbot renew --force-renewal` |
| Service won't start | Check: `sudo journalctl -u consent-api -n 50` |
| Rate limit too strict | Edit zone in `nginx.conf`, run `nginx -t`, reload |
| High memory usage | Reduce workers: edit `asgi.py` or systemd service |

---

## Security Checklist

- [ ] SSH key-only auth (no passwords)
- [ ] Firewall enabled (ufw status green)
- [ ] Fail2Ban running for brute force protection
- [ ] Encryption keys in Secrets Manager (not `.env`)
- [ ] Database remote access disabled
- [ ] TLS 1.3 working (test with `openssl s_client`)
- [ ] HSTS header present (curl -I over HTTPS)
- [ ] X-Frame-Options = DENY
- [ ] Rate limiting verified (429 after threshold)
- [ ] Backups automated and tested

---

**For full details, see `docs/DEPLOYMENT.md`**
