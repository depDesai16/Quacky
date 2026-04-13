@echo off
REM Security setup script for Quacky (Windows)
REM Run this after cloning the repository

echo 🔒 Setting up security for Quacky...
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Install security tools
echo 🛠️  Installing security tools...
python -m pip install --upgrade pip
pip install -r requirements-security.txt

REM Setup pre-commit hooks
echo 🪝 Setting up pre-commit hooks...
pre-commit install

REM Initialize secrets baseline
echo 🔍 Initializing secrets detection...
detect-secrets scan > .secrets.baseline

REM Check .env file
if exist ".env" (
    echo ✅ Found .env file
) else (
    echo ⚠️  .env file not found. Copy .env.example to .env and configure it.
)

REM Run initial security scans
echo.
echo 🔍 Running initial security scans...
echo.

echo Running Bandit...
bandit -r . -ll
echo.

echo Running Safety check...
safety check
echo.

echo Running pip-audit...
pip-audit
echo.

REM Create security scan results directory
if not exist "security-scan-results" mkdir security-scan-results

echo.
echo ✅ Security setup complete!
echo.
echo Next steps:
echo 1. Copy .env.example to .env and configure your API keys
echo 2. Review SECURITY.md for security policies
echo 3. Review docs\SECURITY_GUIDE.md for detailed security guidelines
echo 4. Run 'pre-commit run --all-files' to check all files
echo 5. Enable GitHub security features (Dependabot, CodeQL, etc.)
echo.
echo Security tools installed:
echo   - bandit: Python security linter
echo   - safety: Dependency vulnerability scanner
echo   - pip-audit: PyPI package auditing
echo   - pre-commit: Git hook framework
echo   - detect-secrets: Secret detection
echo.
echo Run security scans anytime with:
echo   bandit -r .
echo   safety check
echo   pip-audit
echo   pre-commit run --all-files
echo.
pause
