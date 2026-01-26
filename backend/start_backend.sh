#!/bin/bash
# ThetaMind Backend Startup Script

set -e

echo "🚀 Starting ThetaMind Backend..."
echo ""

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "   Python: $python_version"

# Check if .env exists
if [ ! -f "../.env" ]; then
    echo "⚠️  WARNING: .env file not found!"
    echo "   Please copy .env.example to .env and configure it."
    echo "   cp ../.env.example ../.env"
    exit 1
fi

# Check if dependencies are installed
echo ""
echo "📦 Checking dependencies..."
if ! python -c "import fastapi" 2>/dev/null; then
    echo "   ❌ Dependencies not installed!"
    echo ""
    echo "   Installing dependencies..."
    echo "   This may take a few minutes..."
    
    # Try pip install with trusted hosts to bypass SSL issues
    pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt || {
        echo ""
        echo "   ⚠️  Installation failed. Trying alternative method..."
        echo "   Please install dependencies manually:"
        echo "   pip install -r requirements.txt"
        echo ""
        echo "   Or use a virtual environment:"
        echo "   python -m venv venv"
        echo "   source venv/bin/activate  # On macOS/Linux"
        echo "   pip install -r requirements.txt"
        exit 1
    }
else
    echo "   ✅ Dependencies installed"
fi

# Check database connection (optional)
echo ""
echo "🔍 Checking configuration..."
if python -c "from app.core.config import settings; print('Database URL:', settings.database_url[:30] + '...')" 2>/dev/null; then
    echo "   ✅ Configuration loaded"
else
    echo "   ⚠️  Configuration check failed (may be normal if .env is incomplete)"
fi

# Start the server
echo ""
echo "🌟 Starting FastAPI server..."
echo "   API will be available at: http://localhost:8000"
echo "   Docs will be available at: http://localhost:8000/docs"
echo ""
echo "   Press Ctrl+C to stop"
echo ""

# Start uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
