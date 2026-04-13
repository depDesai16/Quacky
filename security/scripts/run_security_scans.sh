#!/bin/bash
# Run all security scans for Quacky

set -e

echo "🔒 Running Security Scans for Quacky"
echo "===================================="
echo ""

# Create results directory
mkdir -p security-scan-results
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 1. Bandit - Python Security Linter
echo "1️⃣  Running Bandit (Python Security Linter)..."
echo "-------------------------------------------"
bandit -r . -f txt | tee security-scan-results/bandit_${TIMESTAMP}.txt
bandit -r . -f json -o security-scan-results/bandit_${TIMESTAMP}.json || true
echo "✅ Bandit scan complete"
echo ""

# 2. Safety - Dependency Vulnerability Scanner
echo "2️⃣  Running Safety (Dependency Vulnerabilities)..."
echo "------------------------------------------------"
safety check | tee security-scan-results/safety_${TIMESTAMP}.txt
safety check --json --output security-scan-results/safety_${TIMESTAMP}.json || true
echo "✅ Safety check complete"
echo ""

# 3. pip-audit - PyPI Package Auditing
echo "3️⃣  Running pip-audit (PyPI Package Auditing)..."
echo "----------------------------------------------"
pip-audit | tee security-scan-results/pip-audit_${TIMESTAMP}.txt
pip-audit --format json --output security-scan-results/pip-audit_${TIMESTAMP}.json || true
echo "✅ pip-audit complete"
echo ""

# 4. detect-secrets - Secret Detection
echo "4️⃣  Running detect-secrets (Secret Detection)..."
echo "----------------------------------------------"
if [ -f ".secrets.baseline" ]; then
    detect-secrets scan --baseline .secrets.baseline | tee security-scan-results/secrets_${TIMESTAMP}.txt
else
    detect-secrets scan | tee security-scan-results/secrets_${TIMESTAMP}.txt
fi
echo "✅ Secret detection complete"
echo ""

# 5. Pre-commit hooks
echo "5️⃣  Running pre-commit hooks..."
echo "-----------------------------"
pre-commit run --all-files | tee security-scan-results/precommit_${TIMESTAMP}.txt || true
echo "✅ Pre-commit checks complete"
echo ""

# Summary
echo ""
echo "📊 Security Scan Summary"
echo "======================="
echo "Scan completed at: $(date)"
echo "Results saved in: security-scan-results/"
echo ""
echo "Review the following files:"
echo "  - bandit_${TIMESTAMP}.txt"
echo "  - safety_${TIMESTAMP}.txt"
echo "  - pip-audit_${TIMESTAMP}.txt"
echo "  - secrets_${TIMESTAMP}.txt"
echo "  - precommit_${TIMESTAMP}.txt"
echo ""
echo "Next steps:"
echo "1. Review scan results for any issues"
echo "2. Fix any critical or high severity issues"
echo "3. Update dependencies if vulnerabilities found"
echo "4. Commit fixes and re-run scans"
echo ""
