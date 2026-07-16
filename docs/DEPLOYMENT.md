# DPDP Consent Management API — Production Deployment Guide

**Document Version:** 1.0  
**Last Updated:** 2026-05-22  
**Target OS:** Ubuntu 22.04 LTS  
**Python Version:** 3.12  
**FastAPI Version:** 0.125.0  
**Compliance:** DPDP Act 2023, TLS 1.2+, OWASP Top 10

---

## 1. Prerequisites

Ensure your deployment environment meets the following requirements before starting:

### 1.1 System Requirements
- **OS:** Ubuntu 22.04 LTS (xenial kernel 5.15+)
- **CPU:** Minimum 2 vCPU (4 vCPU recommended for production)
- **RAM:** Minimum 2 GB (4 GB recommended)
- **Disk:** 20 GB free space (SSD preferred)
- **Network:** Public/private subnet with outbound HTTPS access

### 1.2 Required Software
```bash
# Verify installed versions before proceeding
python3 --version          # Should be 3.12.x
pip --version              # Should be 24.x or later
nginx -v                   # Should be 1.24 or later
mysql --version            # Should be 8.0.x
redis-server --version     # Should be 7.x or later (optional)
git --version              # For cloning repository
```

### 1.3 Required Accounts & Access
- **Git repository:** SSH key configured for `git clone`
- **Database:** MySQL user with `CREATE, ALTER, DROP, GRANT` privileges
- **AWS (optional):** S3 bucket for audit logs, credentials with `s3:PutObject` permission
- **Certificate:** Domain ownership for Let's Encrypt (DNS/HTTP validation)
- **Secrets Manager:** AWS Secrets Manager or HashiCorp Vault (for encryption keys)

---

## 2. Server Preparation

### 2.1 Create Dedicated Service User

Run these commands as root or with `sudo`:

```bash
# Create user without login shell (security best practice)
useradd -r -s /bin/false -m -d /opt/consent-api consent

# Verify user creation
id consent
# Output: uid=XXX(consent) gid=XXX(consent) groups=XXX(consent)
```

### 2.2 Configure Firewall Rules (ufw)

```bash
# Enable firewall
ufw enable

# Allow SSH (critical: do this first to avoid lockout)
ufw allow 22/tcp

# Allow HTTP and HTTPS traffic
ufw allow 80/tcp
ufw allow 443/tcp

# Deny all other inbound traffic by default
ufw default deny incoming
ufw default allow outgoing

# Verify rules
ufw status
```

### 2.3 Install System Dependencies

```bash
# Update package cache
apt-get update
apt-get upgrade -y

# Install runtime dependencies
apt-get install -y \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    python3-pip \
    build-essential \
    curl \
    wget \
    git \
    nginx \
    mysql-server \
    mysql-client \
    redis-server \
    certbot \
    python3-certbot-nginx \
    supervisor \
    logrotate

# Install additional security tools
apt-get install -y \
    fail2ban \
    aide \
    auditd

# Verify Nginx installation
nginx -v

# Verify Python
python3.12 --version
```

### 2.4 Configure SSH Hardening

Edit `/etc/ssh/sshd_config`:

```bash
# Backup original
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

# Use a text editor to modify
nano /etc/ssh/sshd_config
```

Add/modify these lines:

```
# Restrict SSH access
Port 22
AddressFamily inet
ListenAddress 0.0.0.0

# Authentication
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys .ssh/authorized_keys2

# Security
ClientAliveInterval 300
ClientAliveCountMax 2
X11Forwarding no
AllowAgentForwarding no
AllowTcpForwarding no
PermitTunnel no
```

Reload SSH daemon:

```bash
systemctl reload sshd
```

### 2.5 Configure Fail2Ban (prevent brute force)

Create `/etc/fail2ban/jail.local`:

```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
logpath = /var/log/auth.log

[nginx-http-auth]
enabled = true
logpath = /var/log/nginx/error.log

[nginx-noscript]
enabled = true
logpath = /var/log/nginx/access.log
```

Start Fail2Ban:

```bash
systemctl enable fail2ban
systemctl start fail2ban
systemctl status fail2ban
```

---

## 3. Application Deployment

### 3.1 Clone Repository

```bash
# Create application directory
mkdir -p /opt/consent-api
cd /opt/consent-api

# Clone repository (requires SSH key in ~/.ssh/id_rsa)
git clone git@github.com:yourdomain/everycred-consent-management-backend.git .

# Verify clone
git log --oneline | head -5
```

### 3.2 Set Up Python Virtual Environment

```bash
# Create venv
python3.12 -m venv .venv

# Activate venv
source .venv/bin/activate

# Upgrade pip, setuptools
pip install --upgrade pip setuptools wheel

# Install Poetry (dependency manager)
pip install poetry==1.8.3

# Verify Poetry
poetry --version
```

### 3.3 Install Application Dependencies

```bash
# Ensure venv is active
source .venv/bin/activate

# Install production dependencies (no dev tools)
poetry install --no-dev

# Verify key packages installed
python -c "import fastapi; print(f'FastAPI {fastapi.__version__}')"
python -c "import sqlalchemy; print(f'SQLAlchemy {sqlalchemy.__version__}')"
```

### 3.4 Create Production Environment File

Create `.env` in `/opt/consent-api/` with production configuration:

```bash
cat > .env << 'EOF'
# Environment and Debug
ENV=prod
DEBUG=False
SERVER_HOST=127.0.0.1
SERVER_PORT=8008

# Database (MySQL)
DB_HOST=localhost
DB_PORT=3306
DB_NAME=consent_db
DB_USER=consent_app
DB_PASSWORD=CHANGE_ME_STRONG_PASSWORD
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_RECYCLE=3600

# Redis (for token blacklist and caching)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Authentication & Encryption (CRITICAL: use secrets manager in production!)
JWT_SECRET_KEY=CHANGE_ME_USE_SECRETS_MANAGER_IN_PROD
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# DPDP Encryption Keys (CRITICAL: generate with os.urandom())
# See section 5 below for key generation
DPDP_DEK_HEX=CHANGE_ME_GENERATE_WITH_SCRIPT
DPDP_HMAC_KEY_HEX=CHANGE_ME_GENERATE_WITH_SCRIPT

# AWS S3 (for audit logs and exports)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
S3_BUCKET_NAME=consent-api-prod-logs

# Email (for notifications)
SMTP_HOST=smtp.yourdomain.com
SMTP_PORT=587
SMTP_USERNAME=noreply@yourdomain.com
SMTP_PASSWORD=
SMTP_FROM_ADDRESS=noreply@yourdomain.com

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/consent-api/app.log
EOF
```

**SECURITY WARNING:** Never commit `.env` to version control. Use a secrets manager (AWS Secrets Manager, HashiCorp Vault) in production.

### 3.5 Set Secure File Permissions

```bash
# Change ownership to consent user
chown -R consent:consent /opt/consent-api

# Restrict .env to consent user only
chmod 600 /opt/consent-api/.env

# Make venv executable
chmod -R u+x /opt/consent-api/.venv/bin

# Verify permissions
ls -la /opt/consent-api/.env
# Output: -rw------- 1 consent consent XXX .env
```

---

## 4. Database Setup

### 4.1 MySQL User and Database Creation

```bash
# Connect to MySQL as root
mysql -u root -p

# Run these SQL commands in MySQL shell:
```

```sql
-- Create database
CREATE DATABASE consent_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user
CREATE USER 'consent_app'@'localhost' IDENTIFIED BY 'CHANGE_ME_STRONG_PASSWORD';

-- Grant privileges (principle of least privilege)
GRANT SELECT, INSERT, UPDATE, DELETE, ALTER, CREATE, DROP ON consent_db.* TO 'consent_app'@'localhost';

-- For Alembic migrations, grant these additional privileges
GRANT ALTER, CREATE, DROP ON consent_db.* TO 'consent_app'@'localhost';

-- Apply changes
FLUSH PRIVILEGES;

-- Verify user
SELECT user, host FROM mysql.user WHERE user='consent_app';
```

Exit MySQL:

```sql
EXIT;
```

### 4.2 Test Database Connection

```bash
# Test connection from application server
mysql -u consent_app -p -h localhost consent_db -e "SELECT 1;"

# Expected output: 1 (single row)
```

### 4.3 Run Database Migrations (Alembic)

```bash
# Activate venv
source /opt/consent-api/.venv/bin/activate

# Change to app directory
cd /opt/consent-api

# Create alembic revision (if not already in repo)
alembic init alembic
alembic revision --autogenerate -m "Initial schema"

# Run migrations (upgrade to latest)
alembic upgrade head

# Verify migrations
alembic current
# Output: ... (heads)
```

### 4.4 Create MySQL Backup User (optional)

For automated backups:

```sql
-- Connect as root
mysql -u root -p

-- Create backup user
CREATE USER 'consent_backup'@'localhost' IDENTIFIED BY 'BACKUP_PASSWORD_CHANGE_ME';

-- Grant backup privileges only
GRANT SELECT, LOCK TABLES ON consent_db.* TO 'consent_backup'@'localhost';

FLUSH PRIVILEGES;
```

---

## 5. Generating Encryption Keys (CRITICAL)

DPDP Act §6 requires strong encryption for personal data. These keys must be:
- Cryptographically random (minimum 256 bits / 32 bytes)
- Stored in a secrets manager (not in `.env` files on disk)
- Rotated annually
- Backed up securely

### 5.1 Generate DEK (Data Encryption Key)

```bash
# Activate venv
source /opt/consent-api/.venv/bin/activate

# Generate 256-bit random key and convert to hex
python3 << 'EOF'
import os
import sys

dek = os.urandom(32)  # 256 bits / 32 bytes
dek_hex = dek.hex()

print(f"DPDP_DEK_HEX={dek_hex}")
print(f"Length: {len(dek)} bytes ({len(dek) * 8} bits)", file=sys.stderr)
EOF
```

Output will look like:

```
DPDP_DEK_HEX=a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1
```

Copy the hex string to your `.env` file.

### 5.2 Generate HMAC Key

```bash
python3 << 'EOF'
import os
import sys

hmac_key = os.urandom(32)  # 256 bits
hmac_hex = hmac_key.hex()

print(f"DPDP_HMAC_KEY_HEX={hmac_hex}")
print(f"Length: {len(hmac_key)} bytes ({len(hmac_key) * 8} bits)", file=sys.stderr)
EOF
```

### 5.3 Generate JWT Secret Key

```bash
python3 << 'EOF'
import secrets

jwt_secret = secrets.token_urlsafe(64)  # 512 bits equivalent
print(f"JWT_SECRET_KEY={jwt_secret}")
EOF
```

### 5.4 Store Keys in AWS Secrets Manager (Recommended)

Instead of storing keys in `.env`, use AWS Secrets Manager:

```bash
# Create secret in AWS Secrets Manager
aws secretsmanager create-secret \
  --name consent-api/prod/encryption-keys \
  --description "DPDP encryption keys for consent API" \
  --secret-string '{
    "DPDP_DEK_HEX": "'$DPDP_DEK_HEX'",
    "DPDP_HMAC_KEY_HEX": "'$DPDP_HMAC_KEY_HEX'",
    "JWT_SECRET_KEY": "'$JWT_SECRET_KEY'"
  }' \
  --region us-east-1
```

Update `.env` to reference the secret:

```bash
# In .env, instead of hardcoding:
USE_SECRETS_MANAGER=true
AWS_SECRET_ARN=arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:consent-api/prod/encryption-keys
```

Update `app/core/config.py` to load from Secrets Manager at startup.

---

## 6. Systemd Service Setup

### 6.1 Create Systemd Unit File

Create `/etc/systemd/system/consent-api.service`:

```bash
sudo tee /etc/systemd/system/consent-api.service > /dev/null << 'EOF'
[Unit]
Description=DPDP Consent Management API
Documentation=https://docs.yourdomain.com/consent-api
After=network.target mysql.service redis.service
Wants=mysql.service redis.service
PartOf=multi-user.target

[Service]
Type=simple
User=consent
Group=consent
WorkingDirectory=/opt/consent-api
Environment="PYTHONUNBUFFERED=1"
Environment="ENV=prod"
EnvironmentFile=/opt/consent-api/.env

# Startup command: run uvicorn with 4 workers
ExecStart=/opt/consent-api/.venv/bin/python asgi.py --env prod

# Auto-restart on crash (with exponential backoff)
Restart=always
RestartSec=5
StartLimitInterval=300
StartLimitBurst=10

# Process isolation and security
PrivateTmp=true
NoNewPrivileges=true
ProtectHome=yes
ProtectSystem=strict
ReadWritePaths=/opt/consent-api /var/log/consent-api

# Timeout for graceful shutdown (Uvicorn default is 120s)
TimeoutStopSec=120

# Log configuration
StandardOutput=journal
StandardError=journal
SyslogIdentifier=consent-api

[Install]
WantedBy=multi-user.target
EOF
```

### 6.2 Enable and Start the Service

```bash
# Reload systemd daemon
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable consent-api

# Start the service
sudo systemctl start consent-api

# Check status
sudo systemctl status consent-api

# View recent logs
sudo journalctl -u consent-api -n 50 -f
```

### 6.3 Verify Service Health

```bash
# Check if service is running
sudo systemctl is-active consent-api
# Output: active

# Check if it's listening on port 8008
sudo ss -tuln | grep 8008
# Output: tcp  LISTEN  0  128  127.0.0.1:8008

# Check service status
curl http://127.0.0.1:8008/health
# Expected: 200 OK response
```

---

## 7. Nginx Reverse Proxy Setup

### 7.1 Copy Nginx Configuration

```bash
# Copy production Nginx config to system location
sudo cp nginx/nginx.conf /etc/nginx/nginx.conf

# Backup original config
sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup

# Set correct ownership and permissions
sudo chown root:root /etc/nginx/nginx.conf
sudo chmod 644 /etc/nginx/nginx.conf
```

### 7.2 Update Domain in Nginx Config

Replace `api.consent.yourdomain.com` with your actual domain:

```bash
# Edit the config
sudo nano /etc/nginx/nginx.conf

# Or use sed to replace (one-liner)
sudo sed -i 's.consent.yourdomain.com.consent.YOUR_DOMAIN.com/g' /etc/nginx/nginx.conf
```

### 7.3 Test Nginx Configuration

```bash
# Dry-run test (no reload)
sudo nginx -t

# Expected output:
# nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
# nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### 7.4 Generate SSL Certificate with Certbot

```bash
# Request certificate from Let's Encrypt
sudo certbot --nginx \
  --agree-tos \
  --no-eff-email \
  --email admin@yourdomain.com \
  -d api.consent.yourdomain.com

# Certbot will:
# 1. Validate domain ownership (HTTP challenge)
# 2. Generate certificate at /etc/letsencrypt/live.consent.yourdomain.com/
# 3. Auto-update Nginx config with SSL directives
# 4. Reload Nginx
```

### 7.5 Verify Certificate Installation

```bash
# Check certificate details
sudo certbot certificates

# Test HTTPS endpoint
curl -I https:/.consent.yourdomain.com/

# Should see: HTTP/2 404 (404 is expected for unknown path)
```

### 7.6 Enable Automatic Certificate Renewal

```bash
# Certbot automatically creates a renewal timer
# Verify it's enabled
sudo systemctl list-timers | grep certbot

# Test renewal (dry-run)
sudo certbot renew --dry-run

# View renewal log
sudo tail -f /var/log/letsencrypt/renewal.log
```

### 7.7 Reload Nginx

```bash
# Reload Nginx (graceful, no downtime)
sudo systemctl reload nginx

# Verify status
sudo systemctl status nginx

# Check for errors in logs
sudo tail -f /var/log/nginx/error.log
```

---

## 8. Health Check and Connectivity Test

### 8.1 Verify Backend is Running

```bash
# Local health check (via Nginx reverse proxy)
curl -v https:/.consent.yourdomain.com/health

# Expected response:
# HTTP/2 200
# Content-Type: application/json
# {"status": "ok"}
```

### 8.2 Test API Endpoint (with rate limiting)

```bash
# Test a safe endpoint (e.g., OpenAPI schema)
curl -s https:/.consent.yourdomain.com/openapi.json | jq '.info.title'

# Expected output:
# "Consent Management API"
```

### 8.3 Check Rate Limiting

```bash
# Simulate 15 requests quickly (limit is 10/min for auth)
for i in {1..15}; do
  curl -s -o /dev/null -w "Request $i: %{http_code}\n" \
    https:/.consent.yourdomain.com/v1/auth/login
done

# You should see:
# Request 1-10: 200-401 (normal responses)
# Request 11-15: 429 (Too Many Requests - rate limited)
```

### 8.4 View Access Logs

```bash
# Real-time access log stream
sudo tail -f /var/log/nginx/access.log

# Parse for errors (4xx, 5xx)
sudo grep " [45][0-9][0-9] " /var/log/nginx/access.log | tail -20
```

---

## 9. Log Management and Rotation

### 9.1 Create Log Directory

```bash
# Create directory for application logs
sudo mkdir -p /var/log/consent-api
sudo chown consent:consent /var/log/consent-api
sudo chmod 755 /var/log/consent-api
```

### 9.2 Configure Logrotate

Create `/etc/logrotate.d/consent-api`:

```bash
sudo tee /etc/logrotate.d/consent-api > /dev/null << 'EOF'
/var/log/consent-api/*.log {
    daily                   # Rotate daily
    rotate 30               # Keep 30 days of logs
    compress                # Gzip compressed logs
    delaycompress           # Don't compress until next rotation
    missingok               # Don't error if file is missing
    notifempty              # Don't rotate empty logs
    create 0640 consent consent  # New log file permissions
    postrotate              # After rotation, reload systemd logging
        systemctl reload consent-api > /dev/null 2>&1 || true
    endscript
}

/var/log/nginx/access.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 www-data www-data
    postrotate
        nginx -s reload > /dev/null 2>&1 || true
    endscript
}

/var/log/nginx/error.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 www-data www-data
    postrotate
        nginx -s reload > /dev/null 2>&1 || true
    endscript
}
EOF
```

### 9.3 Test Logrotate Configuration

```bash
# Dry-run test (verbose)
sudo logrotate -d /etc/logrotate.d/consent-api

# Force rotation (for testing)
sudo logrotate -f /etc/logrotate.d/consent-api

# Verify logs were rotated
ls -la /var/log/consent-api/
```

### 9.4 Archive Old Logs to S3 (Optional)

Create `/usr/local/bin/archive-logs.sh`:

```bash
#!/bin/bash
# Archive logs older than 90 days to S3 Glacier

BUCKET="s3://consent-api-prod-logs"
LOG_DIR="/var/log/consent-api"
DAYS_THRESHOLD=90

find "$LOG_DIR" -name "*.log.*.gz" -mtime +$DAYS_THRESHOLD | while read file; do
    filename=$(basename "$file")
    aws s3 cp "$file" "$BUCKET/archive/$filename" \
        --storage-class GLACIER \
        --region us-east-1
    rm "$file"
done
```

Add to crontab:

```bash
sudo crontab -e

# Add this line (runs daily at 2 AM):
0 2 * * * /usr/local/bin/archive-logs.sh
```

---

## 10. Backup Strategy

### 10.1 Database Backup (MySQL)

Create `/usr/local/bin/backup-consent-db.sh`:

```bash
#!/bin/bash
# Daily MySQL backup to S3

DB_HOST="localhost"
DB_USER="consent_backup"
DB_NAME="consent_db"
S3_BUCKET="s3://consent-api-prod-backups"
BACKUP_DIR="/var/backups/consent-db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Dump database
mysqldump -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" \
    --single-transaction \
    --routines \
    --triggers \
    "$DB_NAME" | gzip > "$BACKUP_DIR/consent_db_${TIMESTAMP}.sql.gz"

# Upload to S3
aws s3 cp "$BACKUP_DIR/consent_db_${TIMESTAMP}.sql.gz" \
    "$S3_BUCKET/daily/$TIMESTAMP.sql.gz" \
    --region us-east-1

# Verify upload
if [ $? -eq 0 ]; then
    echo "Backup successful: $TIMESTAMP"
    # Clean old local backups (keep 7 days)
    find "$BACKUP_DIR" -name "*.sql.gz" -mtime +7 -delete
else
    echo "Backup failed: $TIMESTAMP" >&2
    exit 1
fi
```

Make executable and add to crontab:

```bash
chmod +x /usr/local/bin/backup-consent-db.sh
sudo crontab -e

# Add this line (daily at 3 AM):
0 3 * * * /usr/local/bin/backup-consent-db.sh >> /var/log/consent-api/backup.log 2>&1
```

### 10.2 Encryption Key Backup

**CRITICAL:** Never backup keys to disk. Use AWS Secrets Manager as the authoritative source:

```bash
# Verify keys are in Secrets Manager (not in .env)
aws secretsmanager describe-secret \
  --secret-id consent-api/prod/encryption-keys \
  --region us-east-1
```

### 10.3 Verify Backups

```bash
# List S3 backups
aws s3 ls s3://consent-api-prod-backups/daily/ --region us-east-1

# Test restoration (in a separate DB)
aws s3 cp s3://consent-api-prod-backups/daily/LATEST.sql.gz - \
    --region us-east-1 | gunzip | mysql -u root -p consent_db_restore
```

---

## 11. Security Hardening Checklist

Complete all items below before marking deployment as production-ready:

| Item | Status | Notes |
|------|--------|-------|
| SSH keys only (no passwords) | [ ] | Verify `PasswordAuthentication no` in `/etc/ssh/sshd_config` |
| Firewall enabled (ufw) | [ ] | Only ports 22, 80, 443 open |
| Fail2Ban enabled | [ ] | `systemctl status fail2ban` |
| SELinux or AppArmor enabled | [ ] | OS-level MAC policy enforced |
| MySQL remote access disabled | [ ] | User grants only `localhost`, test with `mysql -u consent_app -h 127.0.0.1` |
| Encryption keys in Secrets Manager | [ ] | Not in `.env` file |
| JWT secret strong (64+ chars) | [ ] | Use `secrets.token_urlsafe(64)` |
| TLS 1.3 enabled in Nginx | [ ] | `ssl_protocols TLSv1.2 TLSv1.3;` |
| Strong cipher suite configured | [ ] | No RC4, DES, MD5, or export ciphers |
| HSTS header enabled | [ ] | `add_header Strict-Transport-Security` |
| X-Frame-Options set to DENY | [ ] | Clickjacking protection |
| X-Content-Type-Options set | [ ] | MIME sniffing prevention |
| CSP header configured | [ ] | `Content-Security-Policy` header present |
| Rate limiting enabled | [ ] | Auth (10/min), Consent (60/min), Global (1000/min) |
| Debug mode disabled in prod | [ ] | `DEBUG=False` in `.env` |
| Nginx version hidden | [ ] | `server_tokens off;` |
| Logging configured | [ ] | Access and error logs to `/var/log/nginx/` |
| Log rotation enabled | [ ] | `/etc/logrotate.d/consent-api` configured |
| Backup strategy tested | [ ] | Restore test completed successfully |
| Health check verified | [ ] | `/health` endpoint responds 200 OK |
| Rate limit verified | [ ] | Auth endpoint returns 429 after threshold |
| Monitoring configured | [ ] | CloudWatch, Datadog, or ELK stack |
| Alerting configured | [ ] | PagerDuty, OpsGenie, or Slack notifications |
| Incident response plan documented | [ ] | Rollback procedures documented |

---

## 12. Rollback Procedure

### 12.1 Prepare for Rollback (Before Deploying)

```bash
# Record current git commit
CURRENT_COMMIT=$(cd /opt/consent-api && git rev-parse HEAD)
echo "Current commit: $CURRENT_COMMIT" > /var/backups/rollback.txt

# Record current database state
mysqldump -u consent_app -p -h localhost consent_db | gzip > \
    /var/backups/consent_db_pre_deploy_$(date +%Y%m%d_%H%M%S).sql.gz

# Record current Nginx config
cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.pre_deploy_$(date +%Y%m%d_%H%M%S)
```

### 12.2 If Deployment Fails (Immediate Rollback)

```bash
# Stop the application
sudo systemctl stop consent-api

# Revert code to previous commit
cd /opt/consent-api
ROLLBACK_COMMIT=$(cat /var/backups/rollback.txt | cut -d' ' -f3)
git reset --hard $ROLLBACK_COMMIT

# Downgrade database (if schema changed)
cd /opt/consent-api
source .venv/bin/activate
alembic downgrade -1  # Downgrade one migration

# Restart service
sudo systemctl start consent-api

# Verify health
curl http://127.0.0.1:8008/health

# Check logs for errors
sudo journalctl -u consent-api -n 100
```

### 12.3 If Database Migration Fails

```bash
# Restore from backup (ensure you have a recent backup)
BACKUP_FILE="/var/backups/consent_db_pre_deploy_*.sql.gz"

# Stop application
sudo systemctl stop consent-api

# Restore database
gunzip < $(ls -t $BACKUP_FILE | head -1) | \
    mysql -u root -p consent_db

# Verify data integrity
mysql -u consent_app -p consent_db -e "SELECT COUNT(*) FROM consent_forms;"

# Restart
sudo systemctl start consent-api
```

---

## 13. Environment-Specific Configuration

Use these recommendations to tailor deployment for different environments:

| Setting | Local | Development | Production |
|---------|-------|-------------|-----------|
| **Workers** | 1 + reload | 2 | 4+ |
| **Debug** | True | True | False |
| **TLS** | No / self-signed | Self-signed | Let's Encrypt |
| **Database** | Local SQLite | Dev MySQL | Production RDS/Cloud SQL |
| **Encryption Keys** | Random (session) | Env var | AWS Secrets Manager |
| **Log Level** | DEBUG | DEBUG | INFO |
| **Rate Limiting** | Disabled | Relaxed (100/min) | Strict (see config) |
| **CORS Origins** | `*` | Dev domains | Specific domains |
| **Session TTL** | 24h | 24h | 8h |
| **Backups** | None | Weekly | Daily + incremental |
| **Monitoring** | Basic | Standard | Full (APM + alerts) |
| **HSTS Max-Age** | N/A | 86400 (1 day) | 31536000 (1 year) |

---

## 14. Troubleshooting

### 14.1 Service Won't Start

```bash
# Check systemd logs
sudo journalctl -u consent-api -n 50

# Check if port 8008 is in use
sudo lsof -i :8008

# Kill conflicting process
sudo kill -9 PID

# Try starting again
sudo systemctl start consent-api
```

### 14.2 Database Connection Fails

```bash
# Test MySQL credentials
mysql -u consent_app -p -h 127.0.0.1 consent_db -e "SELECT 1;"

# Check if MySQL is running
sudo systemctl status mysql

# View MySQL error log
sudo tail -f /var/log/mysql/error.log
```

### 14.3 Rate Limiting Too Aggressive

```bash
# Edit Nginx config
sudo nano /etc/nginx/nginx.conf

# Adjust rate limit zones (e.g., increase from 10/min to 20/min for auth):
# limit_req_zone $binary_remote_addr zone=auth:10m rate=20r/m;

# Test syntax
sudo nginx -t

# Reload
sudo systemctl reload nginx
```

### 14.4 Certificate Renewal Fails

```bash
# Check renewal status
sudo certbot renew --dry-run -v

# Manually renew
sudo certbot renew --force-renewal

# Check certificate expiry
sudo certbot certificates

# View renewal log
sudo tail -f /var/log/letsencrypt/renewal.log
```

### 14.5 High CPU Usage

```bash
# Check process resource usage
top -p $(pgrep -f "python asgi.py")

# Check if app is in infinite loop (check logs)
sudo journalctl -u consent-api -f

# Reduce worker count temporarily
sudo nano /etc/systemd/system/consent-api.service
# Change workers in ExecStart (but leave blank for auto-detection)

# Restart
sudo systemctl daemon-reload
sudo systemctl restart consent-api
```

### 14.6 Nginx 502 Bad Gateway

```bash
# Verify backend is running
curl http://127.0.0.1:8008/health

# Check Nginx error log for details
sudo tail -f /var/log/nginx/error.log

# Increase proxy timeouts in nginx.conf if slow backend:
# proxy_connect_timeout 30s;
# proxy_read_timeout 60s;
# proxy_send_timeout 60s;

# Test and reload
sudo nginx -t && sudo systemctl reload nginx
```

---

## 15. Monitoring and Observability

### 15.1 System Metrics (CloudWatch / Datadog)

```bash
# Install CloudWatch agent (AWS)
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i -E ./amazon-cloudwatch-agent.deb

# Or install Datadog agent
DD_AGENT_MAJOR_VERSION=7 DD_API_KEY=YOUR_KEY \
    DD_SITE=datadoghq.com bash -c "$(curl -L https://s3.amazonaws.com/dd-agent/scripts/install_agent.sh)"
```

### 15.2 Application Logging (ELK Stack)

Configure Filebeat to ship logs to Elasticsearch:

```bash
# Install Filebeat
curl -L -O https://artifacts.elastic.co/downloads/beats/filebeat/filebeat-8.0.0-amd64.deb
sudo dpkg -i filebeat-8.0.0-amd64.deb

# Configure to read consent-api logs
sudo tee /etc/filebeat/filebeat.yml > /dev/null << 'EOF'
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/consent-api/*.log
    fields:
      service: consent-api

output.elasticsearch:
  hosts: ["elasticsearch.yourdomain.com:9200"]
EOF

# Start Filebeat
sudo systemctl enable filebeat
sudo systemctl start filebeat
```

### 15.3 APM Integration (Optional)

Use Elastic APM or Datadog APM for request tracing:

```bash
# Install Elastic APM Python agent
pip install elastic-apm

# In app/server.py, add:
from elasticapm.contrib.fastapi import make_apm_client

apm_client = make_apm_client({"SERVICE_NAME": "consent-api"})
app.add_middleware(ElasticAPM, client=apm_client)
```

---

## 16. Post-Deployment Verification

Complete this checklist after deployment:

- [ ] Application logs show no errors: `sudo journalctl -u consent-api -n 100 | grep -i error`
- [ ] Nginx error log is clean: `sudo tail -20 /var/log/nginx/error.log`
- [ ] All health checks passing: `curl https:/.consent.yourdomain.com/health`
- [ ] Database has correct schema: `mysql -u consent_app -p consent_db -e "SHOW TABLES;"`
- [ ] Rate limiting works: Submit 15 requests to `/v1/auth/` endpoint
- [ ] HTTPS certificate valid: `openssl s_client -connect api.consent.yourdomain.com:443`
- [ ] HSTS header present: `curl -I https:/.consent.yourdomain.com | grep HSTS`
- [ ] Backup runs successfully: Check S3 or backup directory for recent file
- [ ] Monitoring is collecting data: Verify logs in CloudWatch / Datadog dashboard

---

## 17. Support and Documentation

- **API Documentation:** `https:/.consent.yourdomain.com/docs`
- **Health Status:** `https:/.consent.yourdomain.com/health`
- **Application Logs:** `/var/log/consent-api/app.log`
- **Nginx Logs:** `/var/log/nginx/{access,error}.log`
- **System Logs:** `sudo journalctl -u consent-api -f`
- **Database:** `mysql -u consent_app -p -h 127.0.0.1 consent_db`

---

**Document Revision:** 1.0  
**Last Updated:** 2026-05-22  
**Maintained By:** DevOps / Platform Team
