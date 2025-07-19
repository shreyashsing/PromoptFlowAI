#!/bin/bash
# Unix/Linux/macOS setup script for PromptFlow AI Backend

echo "🚀 Setting up PromptFlow AI Backend Environment (Unix/Linux/macOS)"
echo "=================================================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed or not in PATH"
    echo "Please install Python 3.8+ from your package manager or https://python.org"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment"
        exit 1
    fi
    echo "✅ Virtual environment created successfully!"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "❌ Failed to activate virtual environment"
    exit 1
fi

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
if [ -f "requirements.txt" ]; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies"
        exit 1
    fi
    echo "✅ Dependencies installed successfully!"
else
    echo "⚠️  requirements.txt not found"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Copy .env.example to .env and configure your settings"
echo "2. Run database initialization: python scripts/init_db.py"
echo "3. Start the server: uvicorn app.main:app --reload"
echo ""
echo "To activate the virtual environment in the future, run:"
echo "   source venv/bin/activate"
echo ""