#!/bin/bash
# Security setup script for Quacky
# Run this after cloning the repository

set -e  # Exit on error

echo "🔒 Setting up security for Quacky..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install security tools
echo "🛠️  Installing security tools..."
pip install --upgrade pip
pip install -r requirements-security.txt

# Setup pre-commit hooks
echo "🪝 Setting up pre-commit hooks..."
pre-commit install

# Initialize secrets baseline
echo "🔍 Initializing secrets detection..."
detect-secrets scan > .secrets.baseline || true

# Set secure file permissions
echo "🔐 Setting secure file permissions..."
chmod 700 venv/ 2>/dev/null || true
chmod 700 frontend/camera/face_data/ 2>/dev/null || true

if [ -f ".env" ]; then
    chmod 600 .env
    echo "✅ Secured .env file"
else
    echo "⚠️  .env file not found. Copy .env.example to .env and configure it."
fi

# Run initial security scans
echo ""
echo "🔍 Running initial security scans..."
echo ""

echo "Running Bandit..."
bandit -r . -ll || true
echo ""

echo "Running Safety check..."
safety check || true
echo ""

echo "Running pip-audit..."
pip-audit || true
echo ""

# Create security scan results directory
mkdir -p security-scan-results

echo ""
echo "✅ Security setup complete!"
echo ""
echo "Next steps:"
echo "1. Copy .env.example to .env and configure your API keys"
echo "2. Review SECURITY.md for security policies"
echo "3. Review docs/SECURITY_GUIDE.md for detailed security guidelines"
echo "4. Run 'pre-commit run --all-files' to check all files"
echo "5. Enable GitHub security features (Dependabot, CodeQL, etc.)"
echo ""
echo "Security tools installed:"
echo "  - bandit: Python security linter"
echo "  - safety: Dependency vulnerability scanner"
echo "  - pip-audit: PyPI package auditing"
echo "  - pre-commit: Git hook framework"
echo "  - detect-secrets: Secret detection"
echo ""
echo "Run security scans anytime with:"
echo "  bandit -r ."
echo "  safety check"
echo "  pip-audit"
echo "  pre-commit run --all-files"
echo ""
