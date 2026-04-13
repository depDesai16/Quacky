# Quacky Security Guide

## Table of Contents
1. [Overview](#overview)
2. [Secure Installation](#secure-installation)
3. [Configuration Security](#configuration-security)
4. [Runtime Security](#runtime-security)
5. [Data Protection](#data-protection)
6. [Network Security](#network-security)
7. [Monitoring & Auditing](#monitoring--auditing)
8. [Incident Response](#incident-response)

## Overview

This guide provides comprehensive security guidelines for installing, configuring, and running Quacky securely.

## Secure Installation

### 1. Verify Source Code

```bash
# Clone from official repository
git clone https://github.com/YOUR_USERNAME/Quacky.git
cd Quacky

# Verify commit signatures (if enabled)
git log --show-signature

# Check for tampering
git fsck
```

### 2. Use Virtual Environment

```bash
# Create isolated environment
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

### 3. Verify Dependencies

```bash
# Install with hash verification
pip install --require-hashes -r requirements.txt

# Or audit dependencies first
pip-audit -r requirements.txt

# Check for known vulnerabilities
safety check -r requirements.txt
```

### 4. Secure File Permissions

```bash
# Linux/Mac: Restrict permissions
chmod 700 venv/
chmod 600 .env
chmod 700 frontend/camera/face_data/

# Windows: Use File Properties > Security tab
# Set permissions to allow only your user account
```

## Configuration Security

### Environment Variables

**Never commit sensitive data to Git!**

1. **Create .env file**:
```bash
# Copy example
cp .env.example .env

# Edit with secure values
nano .env  # or your preferred editor
```

2. **Secure API Keys**:
```env
# Use strong, unique API keys
GEMINI_API_KEY=your_secure_api_key_here

# Email credentials - use app-specific passwords
EMAIL_ADDRESS=your_email@example.com
EMAIL_PASSWORD=app_specific_password_not_real_password
```

3. **Rotate Keys Regularly**:
- Change API keys every 90 days
- Use different keys for dev/prod
- Revoke unused keys immediately

### Face Recognition Security

1. **Encrypt Face Data** (optional but recommended):
```python
# Add encryption to face_recognition.py
from cryptography.fernet import Fernet

# Generate key (store securely!)
key = Fernet.generate_key()
cipher = Fernet(key)

# Encrypt before saving
encrypted_data = cipher.encrypt(pickle.dumps(face_encodings))
```

2. **Secure Storage**:
```bash
# Restrict access to face data
chmod 600 frontend/camera/face_data/*.pkl
```

3. **Data Retention**:
- Delete old face data regularly
- Implement data retention policy
- Provide user data deletion option

## Runtime Security

### 1. Run with Least Privileges

```bash
# Don't run as root/administrator
# Create dedicated user (Linux)
sudo useradd -m -s /bin/bash quacky
sudo -u quacky python app.py
```

### 2. Firewall Configuration

```bash
# Linux (ufw)
sudo ufw allow 8000/tcp  # Only if needed externally
sudo ufw enable

# Windows Firewall
# Allow Python through firewall only for private networks
```

### 3. Monitor Resource Usage

```bash
# Check for unusual activity
top  # Linux/Mac
taskmgr  # Windows

# Monitor network connections
netstat -an | grep 8000
```

### 4. Secure Local Server

The app runs a local server on `localhost:8000`. Ensure:
- Server only binds to localhost (127.0.0.1)
- No external access unless explicitly needed
- Use HTTPS if exposing externally (not recommended)

## Data Protection

### Local Data Storage

Quacky stores data locally in:
- `frontend/camera/face_data/` - Face recognition data
- `.env` - Configuration and credentials
- Chat history (if implemented)

**Protection Measures**:

1. **Backup Securely**:
```bash
# Encrypted backup
tar -czf backup.tar.gz frontend/camera/face_data/
gpg -c backup.tar.gz  # Encrypt with password
rm backup.tar.gz  # Remove unencrypted
```

2. **Secure Deletion**:
```bash
# Linux/Mac - secure delete
shred -vfz -n 10 sensitive_file

# Windows - use SDelete
sdelete -p 10 sensitive_file
```

3. **Data Minimization**:
- Only collect necessary data
- Delete data when no longer needed
- Implement data retention policies

### Privacy Considerations

1. **Microphone Access**:
   - Only active when speech features used
   - Audio not stored or transmitted
   - Review microphone permissions regularly

2. **Camera Access**:
   - Only for face recognition feature
   - Images not stored permanently
   - Can be disabled in settings

3. **Email Access**:
   - Only if email features configured
   - Uses app-specific passwords
   - No email content stored

## Network Security

### API Connections

Quacky connects to:
1. **Google Gemini API** (if configured)
   - HTTPS only
   - Certificate validation enabled
   - Rate limiting recommended

2. **Local Server** (localhost:8000)
   - Internal communication only
   - No external exposure by default

### Monitoring Network Activity

```bash
# Monitor connections (Linux/Mac)
lsof -i :8000

# Monitor connections (Windows)
netstat -ano | findstr :8000

# Use Wireshark for detailed analysis
# Filter: tcp.port == 8000
```

### Proxy Configuration (if needed)

```python
# In backend/client.py, add proxy support
import os
proxies = {
    'http': os.getenv('HTTP_PROXY'),
    'https': os.getenv('HTTPS_PROXY'),
}
```

## Monitoring & Auditing

### Enable Logging

```python
# Add to app.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('quacky.log'),
        logging.StreamHandler()
    ]
)

# Log security events
logger = logging.getLogger(__name__)
logger.info("Application started")
logger.warning("Failed authentication attempt")
```

### Security Monitoring

1. **Check Logs Regularly**:
```bash
# Review logs for anomalies
tail -f quacky.log

# Search for errors
grep ERROR quacky.log

# Search for security events
grep -i "security\|auth\|fail" quacky.log
```

2. **Monitor File Changes**:
```bash
# Linux - use inotify
inotifywait -m -r -e modify,create,delete .

# Windows - use File System Watcher
# Or third-party tools like FileAudit
```

3. **API Usage Monitoring**:
- Track API call frequency
- Monitor for unusual patterns
- Set up alerts for quota limits

### Audit Checklist

Weekly:
- [ ] Review application logs
- [ ] Check for failed authentication attempts
- [ ] Monitor API usage
- [ ] Review file system changes

Monthly:
- [ ] Update dependencies
- [ ] Rotate API keys
- [ ] Review access permissions
- [ ] Run security scans

## Incident Response

### If You Suspect a Security Breach

1. **Immediate Actions**:
   ```bash
   # Stop the application
   pkill -f "python app.py"
   
   # Disconnect from network (if needed)
   # Linux: sudo ifconfig eth0 down
   # Windows: Disable network adapter
   
   # Preserve evidence
   cp quacky.log incident-$(date +%Y%m%d).log
   ```

2. **Investigation**:
   - Review logs for suspicious activity
   - Check file modifications
   - Review network connections
   - Identify compromised data

3. **Containment**:
   - Change all API keys
   - Change email passwords
   - Update all credentials
   - Patch vulnerabilities

4. **Recovery**:
   - Restore from clean backup
   - Verify system integrity
   - Update security measures
   - Document incident

5. **Post-Incident**:
   - Conduct post-mortem
   - Update security policies
   - Improve detection mechanisms
   - Train on lessons learned

### Reporting Security Issues

See [SECURITY.md](../SECURITY.md) for reporting procedures.

## Security Best Practices Summary

✅ **DO**:
- Use virtual environments
- Keep dependencies updated
- Use strong, unique API keys
- Enable 2FA on connected accounts
- Run with least privileges
- Monitor logs regularly
- Backup data securely
- Use HTTPS for external connections
- Validate all inputs
- Handle errors securely

❌ **DON'T**:
- Commit API keys to Git
- Run as root/administrator
- Use default passwords
- Expose local server externally
- Store sensitive data unencrypted
- Ignore security warnings
- Use outdated dependencies
- Share API keys
- Log sensitive information
- Disable security features

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

---

**Questions or Concerns?**
Contact: security@example.com

**Last Updated**: March 2026
