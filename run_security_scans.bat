@echo off
REM Run all security scans for Quacky (Windows)

echo 🔒 Running Security Scans for Quacky
echo ====================================
echo.

REM Create results directory
if not exist "security-scan-results" mkdir security-scan-results
set TIMESTAMP=%date:~-4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM 1. Bandit - Python Security Linter
echo 1️⃣  Running Bandit (Python Security Linter)...
echo -------------------------------------------
bandit -r . -f txt > security-scan-results\bandit_%TIMESTAMP%.txt
bandit -r . -f json -o security-scan-results\bandit_%TIMESTAMP%.json
type security-scan-results\bandit_%TIMESTAMP%.txt
echo ✅ Bandit scan complete
echo.

REM 2. Safety - Dependency Vulnerability Scanner
echo 2️⃣  Running Safety (Dependency Vulnerabilities)...
echo ------------------------------------------------
safety check > security-scan-results\safety_%TIMESTAMP%.txt
safety check --json --output security-scan-results\safety_%TIMESTAMP%.json
type security-scan-results\safety_%TIMESTAMP%.txt
echo ✅ Safety check complete
echo.

REM 3. pip-audit - PyPI Package Auditing
echo 3️⃣  Running pip-audit (PyPI Package Auditing)...
echo ----------------------------------------------
pip-audit > security-scan-results\pip-audit_%TIMESTAMP%.txt
pip-audit --format json --output security-scan-results\pip-audit_%TIMESTAMP%.json
type security-scan-results\pip-audit_%TIMESTAMP%.txt
echo ✅ pip-audit complete
echo.

REM 4. detect-secrets - Secret Detection
echo 4️⃣  Running detect-secrets (Secret Detection)...
echo ----------------------------------------------
if exist ".secrets.baseline" (
    detect-secrets scan --baseline .secrets.baseline > security-scan-results\secrets_%TIMESTAMP%.txt
) else (
    detect-secrets scan > security-scan-results\secrets_%TIMESTAMP%.txt
)
type security-scan-results\secrets_%TIMESTAMP%.txt
echo ✅ Secret detection complete
echo.

REM 5. Pre-commit hooks
echo 5️⃣  Running pre-commit hooks...
echo -----------------------------
pre-commit run --all-files > security-scan-results\precommit_%TIMESTAMP%.txt
type security-scan-results\precommit_%TIMESTAMP%.txt
echo ✅ Pre-commit checks complete
echo.

REM Summary
echo.
echo 📊 Security Scan Summary
echo =======================
echo Scan completed at: %date% %time%
echo Results saved in: security-scan-results\
echo.
echo Review the following files:
echo   - bandit_%TIMESTAMP%.txt
echo   - safety_%TIMESTAMP%.txt
echo   - pip-audit_%TIMESTAMP%.txt
echo   - secrets_%TIMESTAMP%.txt
echo   - precommit_%TIMESTAMP%.txt
echo.
echo Next steps:
echo 1. Review scan results for any issues
echo 2. Fix any critical or high severity issues
echo 3. Update dependencies if vulnerabilities found
echo 4. Commit fixes and re-run scans
echo.
pause
