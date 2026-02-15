#!/bin/bash
echo "════════════════════════════════════════════════"
echo "  Structure Validation"
echo "════════════════════════════════════════════════"

ERRORS=0

check_file() {
    if [ -f "$1" ]; then
        echo "✅ $1"
    else
        echo "❌ MISSING: $1"
        ((ERRORS++))
    fi
}

# Check all 20 files
check_file "README.md"
check_file ".env.example"
check_file ".gitignore"
check_file "requirements.txt"
check_file "app/__init__.py"
check_file "app/main.py"
check_file "app/config.py"
check_file "app/models/__init__.py"
check_file "app/models/schemas.py"
check_file "app/services/__init__.py"
check_file "app/services/vertex_ai_service.py"
check_file "app/services/storage_service.py"
check_file "app/services/datadog_service.py"
check_file "app/api/__init__.py"
check_file "app/api/routes.py"
check_file "app/api/dependencies.py"
check_file "app/api/middleware.py"
check_file "deployment/systemd/aws-cost-agent.service"
check_file "deployment/scripts/install.sh"

echo ""
if [ $ERRORS -eq 0 ]; then
    echo "🎉 All 20 files present! Ready to install."
    exit 0
else
    echo "❌ $ERRORS files missing"
    exit 1
fi
