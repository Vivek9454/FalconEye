# Production Deployment Guide

## 🚀 Production Checklist

### Pre-Deployment

- [ ] All secrets moved to environment variables (no `config.py` in repo)
- [ ] `.env` file created and secured (not in version control)
- [ ] Strong `FALCONEYE_SECRET` generated
- [ ] HTTPS/SSL configured (via Cloudflare or reverse proxy)
- [ ] Firewall rules configured
- [ ] Database backups configured (if using database)
- [ ] Monitoring and logging set up
- [ ] Rate limiting configured
- [ ] Production WSGI server (Gunicorn) installed

## 🔧 Production Server Setup

### Option 1: Gunicorn (Recommended)

```bash
# Install Gunicorn
pip install gunicorn

# Run with 4 workers
gunicorn -w 4 -b 0.0.0.0:3001 --timeout 120 --access-logfile - --error-logfile - backend:app

# With more configuration
gunicorn \
  --workers 4 \
  --worker-class sync \
  --timeout 120 \
  --bind 0.0.0.0:3001 \
  --access-logfile /var/log/falconeye/access.log \
  --error-logfile /var/log/falconeye/error.log \
  --log-level info \
  --preload \
  backend:app
```

### Option 2: uWSGI

```bash
pip install uwsgi

# Create uwsgi.ini
[uwsgi]
module = backend:app
master = true
processes = 4
socket = 0.0.0.0:3001
protocol = http
vacuum = true
die-on-term = true
```

### Option 3: Docker with Gunicorn

```bash
docker build --target production -t falconeye:prod .
docker run -d \
  --name falconeye \
  -p 3001:3001 \
  --env-file .env \
  -v $(pwd)/clips:/app/clips \
  falconeye:prod
```

## 🔒 Security Hardening

### 1. Environment Variables

```bash
# Generate secure secret
export FALCONEYE_SECRET=$(openssl rand -hex 32)

# Set production environment
export FLASK_ENV=production

# Disable debug mode
export FLASK_DEBUG=0
```

### 2. Firewall Configuration

```bash
# Allow only necessary ports
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (if not using Cloudflare)
sudo ufw allow 443/tcp   # HTTPS (if not using Cloudflare)
sudo ufw enable
```

### 3. Rate Limiting

Install and configure Flask-Limiter:

```bash
pip install flask-limiter
```

Add to `backend.py`:

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"  # Use Redis in production: "redis://localhost:6379"
)

@app.route("/auth/login", methods=["POST"])
@limiter.limit("5 per minute")
def login():
    # ...
```

### 4. Input Validation

All endpoints should validate inputs:

```python
from flask import request
import re

def validate_camera_id(cam_id):
    """Validate camera ID format"""
    if not re.match(r'^cam[12]$', cam_id):
        raise ValueError("Invalid camera ID")
    return cam_id
```

### 5. CORS Configuration

Restrict CORS in production:

```python
from flask_cors import CORS

if os.environ.get('FLASK_ENV') == 'production':
    CORS(app, origins=["https://your-domain.com"])
else:
    CORS(app)  # Allow all in development
```

## 📊 Monitoring

### Application Logs

```bash
# Systemd service logs
sudo journalctl -u falconeye -f

# Gunicorn logs
tail -f /var/log/falconeye/access.log
tail -f /var/log/falconeye/error.log
```

### Health Checks

The application includes a health check endpoint:

```bash
curl http://localhost:3001/mobile/status
```

### Monitoring Tools

- **Prometheus + Grafana**: For metrics
- **Sentry**: For error tracking
- **Uptime Robot**: For availability monitoring

## 🔄 Backup Strategy

### Automated Backups

```bash
#!/bin/bash
# backup.sh - Run via cron

BACKUP_DIR="/backups/falconeye"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup clips
tar -czf "$BACKUP_DIR/clips_$DATE.tar.gz" /path/to/FalconEye/clips

# Backup configuration
cp /path/to/FalconEye/.env "$BACKUP_DIR/env_$DATE"

# Upload to S3 (if configured)
aws s3 cp "$BACKUP_DIR/clips_$DATE.tar.gz" s3://your-backup-bucket/
```

### Cron Job

```bash
# Add to crontab: crontab -e
0 2 * * * /path/to/backup.sh
```

## 🚨 Incident Response

### Application Crashes

1. Check logs: `sudo journalctl -u falconeye -n 100`
2. Restart service: `sudo systemctl restart falconeye`
3. Check system resources: `htop`, `df -h`

### Security Incidents

1. Rotate all credentials immediately
2. Review access logs
3. Check for unauthorized access
4. Update security patches
5. Document incident

## 📈 Performance Optimization

### Worker Configuration

```python
# Calculate workers: (2 x CPU cores) + 1
workers = (2 * os.cpu_count()) + 1
```

### Database Connection Pooling

If using a database:

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20
)
```

### Caching

Use Redis for caching:

```python
from flask_caching import Cache

cache = Cache(app, config={
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': 'redis://localhost:6379/0'
})
```

## 🔐 Secrets Management

### Option 1: Environment Variables

```bash
# .env file (not in git)
export FALCONEYE_SECRET="..."
```

### Option 2: AWS Secrets Manager

```python
import boto3

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])
```

### Option 3: HashiCorp Vault

```python
import hvac

client = hvac.Client(url='https://vault.example.com')
secret = client.secrets.kv.v2.read_secret_version(path='falconeye')
```

## 📝 Deployment Checklist

- [ ] Code tested and reviewed
- [ ] Dependencies updated and pinned
- [ ] Environment variables configured
- [ ] Database migrations run (if applicable)
- [ ] SSL certificates valid
- [ ] Firewall configured
- [ ] Monitoring set up
- [ ] Backups configured
- [ ] Documentation updated
- [ ] Team notified of deployment

## 🆘 Troubleshooting

### High Memory Usage

- Reduce model size (use yolov8n instead of yolov8x)
- Reduce number of workers
- Enable model caching
- Use GPU if available

### Slow Performance

- Check GPU availability
- Optimize model selection
- Increase worker count
- Add caching layer
- Use CDN for static assets

### Connection Issues

- Check firewall rules
- Verify port bindings
- Check reverse proxy configuration
- Review network logs

