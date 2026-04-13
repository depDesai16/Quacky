# Security Policy

## Supported Versions

We take security seriously and provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We appreciate your efforts to responsibly disclose your findings and will make every effort to acknowledge your contributions.

### How to Report a Security Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via one of the following methods:

1. **Email**: Send details to **some email, idk yet**
2. **GitHub Security Advisory**: Use the [Security Advisory](https://github.com/YOUR_USERNAME/Quacky/security/advisories/new) feature

### What to Include in Your Report

Please include the following information:

- Type of vulnerability (e.g., SQL injection, XSS, authentication bypass)
- Full paths of source file(s) related to the vulnerability
- Location of the affected source code (tag/branch/commit or direct URL)
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Depends on severity
  - Critical: 1-7 days
  - High: 7-30 days
  - Medium: 30-90 days
  - Low: Best effort

## Security Best Practices for Users

### Installation Security

1. **Always use virtual environments**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Verify package integrity**:
   ```bash
   pip install --require-hashes -r requirements.txt
   ```

3. **Keep dependencies updated**:
   ```bash
   pip install --upgrade -r requirements.txt
   ```

### API Key Security

1. **Never commit API keys** to version control
2. **Use environment variables** for sensitive data
3. **Rotate API keys regularly**
4. **Use `.env` files** (already in `.gitignore`)

### Runtime Security

1. **Run with least privileges** - Don't run as administrator/root
2. **Review permissions** - Check what the application can access
3. **Monitor network activity** - Quacky only connects to:
   - Google Gemini API (if configured)
   - Local server (localhost:8000)

### Data Privacy

- **Local Data**: All chat history and user data is stored locally
- **No Telemetry**: We don't collect usage statistics
- **Face Recognition**: Face data is stored locally in `frontend/camera/face_data/`
- **Email Access**: Only used if you configure email features

## Known Security Considerations

### Face Recognition
- Face encodings are stored locally in pickle files
- Ensure proper file permissions on `face_data/` directory
- Consider encrypting face data for sensitive environments

### Email Integration
- Email credentials are stored in `.env` file
- Use app-specific passwords, not your main password
- Enable 2FA on your email account

### Speech-to-Text
- Microphone access is required for voice features
- Audio is processed locally, not sent to external services (except if using cloud STT)

### API Keys
- Gemini API key required for AI features
- Store in `.env` file, never in code
- Monitor API usage for unexpected activity

## Security Features

### Implemented Security Measures

1. **Environment Variable Protection**
   - Sensitive data in `.env` files
   - `.env` excluded from version control

2. **Input Validation**
   - User inputs are sanitized
   - File paths are validated

3. **Dependency Management**
   - Regular dependency updates
   - Vulnerability scanning with `pip-audit`

4. **Code Security**
   - No eval() or exec() usage
   - Secure file handling
   - Proper error handling

### Planned Security Enhancements

- [ ] Add code signing for releases
- [ ] Implement automatic dependency updates
- [ ] Add security scanning in CI/CD
- [ ] Encrypt sensitive local data
- [ ] Add rate limiting for API calls
- [ ] Implement audit logging

## Compliance

This project aims to comply with:

- **OWASP Top 10** security risks mitigation
- **CWE/SANS Top 25** most dangerous software errors
- **GDPR** for user data privacy (local storage only)

## Security Scanning

We use the following tools to maintain security:

- **Bandit**: Python security linter (config: `security/config/.bandit`)
- **Safety**: Dependency vulnerability scanner
- **pip-audit**: PyPI package auditing
- **GitHub Dependabot**: Automated dependency updates
- **CodeQL**: Semantic code analysis

## Setup

To set up security tools, run:

**Linux/Mac:**
```bash
chmod +x security/scripts/setup_security.sh
./security/scripts/setup_security.sh
```

**Windows:**
```cmd
security\scripts\setup_security.bat
```

## Running Security Scans

**Linux/Mac:**
```bash
./security/scripts/run_security_scans.sh
```

**Windows:**
```cmd
security\scripts\run_security_scans.bat
```

## Contact

For security concerns, please contact:
- Security Team: [We have a security team??]
- Project Maintainer: [I guess someone maintains us]

---

**Last Updated**: April 2026
