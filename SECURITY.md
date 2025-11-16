# Security Guide

## 🔒 Important Security Information

### Secrets Management

**NEVER commit the following files to version control:**
- `config.py` - Contains AWS credentials and other secrets
- `firebase_config.json` - Contains Firebase server keys
- `.env` - Contains all environment variables
- `*-permanent-config.yml` - Contains Cloudflare tunnel credentials
- `firebase-service-account.json` - Contains Firebase service account keys

### Migrating from config.py to .env

If you're currently using `config.py`, migrate to `.env`:

1. **Copy the example file:**
   ```bash
   cp .env.example .env
   ```

2. **Update .env with your values:**
   ```bash
   # Edit .env with your actual credentials
   nano .env
   ```

3. **Remove config.py:**
   ```bash
   rm config.py
   ```

4. **Load environment variables:**
   ```bash
   # On Linux/Mac
   export $(cat .env | xargs)
   
   # Or use python-dotenv (recommended)
   pip install python-dotenv
   ```

### Rotating Exposed Credentials

**CRITICAL**: If you've accidentally committed secrets, rotate them immediately!

1. **Rotate all exposed credentials immediately:**
   - AWS: Generate new access keys in IAM console and revoke old ones
   - Firebase: Regenerate server key in Firebase console (Project Settings > Cloud Messaging)
   - Cloudflare: Regenerate tunnel credentials
   - Any other services: Rotate all exposed keys/tokens

2. **Remove from git index (already done):**
   ```bash
   git rm --cached firebase_config.json
   git rm --cached config.py
   echo "firebase_config.json" >> .gitignore
   echo "config.py" >> .gitignore
   git commit -m "Remove secrets from repository"
   ```

3. **Purge from git history (recommended for public repos):**
   
   **Option A: Using git-filter-repo (recommended)**
   ```bash
   pip install git-filter-repo
   git filter-repo --path firebase_config.json --path config.py --invert-paths
   git push origin --force --all
   ```
   
   **Option B: Using BFG Repo-Cleaner**
   ```bash
   # Install BFG: brew install bfg (Mac) or download from https://rtyley.github.io/bfg-repo-cleaner/
   bfg --delete-files firebase_config.json
   bfg --delete-files config.py
   git reflog expire --expire=now --all
   git gc --prune=now --aggressive
   git push origin --force --all
   ```
   
   **Option C: Using git filter-branch (legacy)**
   ```bash
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch config.py firebase_config.json" \
     --prune-empty --tag-name-filter cat -- --all
   git push origin --force --all
   ```

4. **Verify removal:**
   ```bash
   git log --all --full-history -- firebase_config.json
   # Should return no results
   ```

**Warning**: Force pushing rewrites history. Coordinate with team members and ensure everyone pulls the updated history.

### Environment Variables

All sensitive configuration should use environment variables:

```bash
# Required
export FALCONEYE_SECRET="your-secret-key"
export CAM1_URL="http://your-camera-ip/jpg"

# Optional (AWS)
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
export AWS_REGION="us-east-1"
export S3_BUCKET_NAME="your-bucket"

# Optional (Firebase)
export FCM_SERVER_KEY="your-server-key"
export FIREBASE_PROJECT_ID="your-project-id"
```

### Production Deployment

1. **Use a production WSGI server:**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:3001 backend:app
   ```

2. **Enable HTTPS:**
   - Use a reverse proxy (nginx, Caddy) with SSL certificates
   - Or use Cloudflare tunnel (already configured)

3. **Set secure environment variables:**
   ```bash
   export FLASK_ENV=production
   export FALCONEYE_SECRET=$(openssl rand -hex 32)
   ```

4. **Use secrets management:**
   - AWS Secrets Manager
   - HashiCorp Vault
   - Kubernetes Secrets
   - Docker Secrets

### Rate Limiting

The backend includes basic rate limiting considerations. For production, consider:

```python
# Install flask-limiter
pip install flask-limiter

# Add to backend.py
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route("/auth/login", methods=["POST"])
@limiter.limit("5 per minute")
def login():
    # ...
```

### Input Validation

All user inputs are validated. For additional security:

1. **Sanitize file uploads:**
   - Validate file types
   - Limit file sizes
   - Scan for malware

2. **Validate API inputs:**
   - Use JSON schema validation
   - Sanitize strings
   - Validate ranges

3. **SQL Injection Prevention:**
   - Use parameterized queries (if using database)
   - Escape user inputs

### Security Headers

The backend automatically sets security headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Strict-Transport-Security` (production only)

### Session Security

- Sessions use HTTPOnly cookies (prevents XSS)
- Secure cookies in production (HTTPS only)
- SameSite=Lax (CSRF protection)
- Configurable session timeout

### Authentication

- Passwords are hashed using bcrypt
- Timing attack prevention
- Input validation
- Session-based authentication

## 🚨 Reporting Security Issues

If you discover a security vulnerability, please email security@falconeye.website (or create a private security advisory on GitHub).

**Do NOT** create a public issue for security vulnerabilities.

