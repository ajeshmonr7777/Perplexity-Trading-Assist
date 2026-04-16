#!/bin/bash

# setup_mac.sh - Script to automate setup for the client

echo "=========================================="
echo "   Perplexity Trading System Setup        "
echo "=========================================="

# 0. Fix folder permissions (common issue when extracted from zip)
chmod -R u+rwX . 2>/dev/null

# 1. Check Python Installation
if command -v python3 &>/dev/null; then
    echo "✅ Python 3 found."
else
    echo "❌ Error: Python 3 is not installed. Please install Python 3.9+ from https://www.python.org/downloads/"
    exit 1
fi

# 2. Create Virtual Environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment (venv)..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment."
        exit 1
    fi
else
    echo "✅ Virtual environment already exists."
fi

# 3. Activate Virtual Environment & Install Dependencies
echo "⬇️  Installing dependencies..."
source venv/bin/activate

if [ -f "requirements.txt" ]; then
    pip install --upgrade pip
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies."
        exit 1
    fi
    echo "✅ Dependencies installed successfully."
else
    echo "❌ requirements.txt not found!"
    exit 1
fi

# 4. Environment Configuration
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "⚙️  Creating .env configuration file..."
        cp .env.example .env
        
        echo ""
        echo "👉 Please enter your PERPLEXITY API KEY (Leave blank to edit manually later):"
        read -r API_KEY
        
        if [ ! -z "$API_KEY" ]; then
            # Using sed for cross-platform compatibility (mac requires empty string for -i)
            sed -i '' "s/PERPLEXITY_API_KEY=.*/PERPLEXITY_API_KEY=$API_KEY/" .env
            echo "✅ API Key saved to .env file."
        else
            echo "⚠️  No API Key entered. Please edit .env file manually."
        fi
    else
        echo "⚠️  .env.example file missing. Skipping configuration."
    fi
else
    echo "✅ Configuration file (.env) already exists."
fi

# 5. Make start script executable
if [ -f "start.sh" ]; then
    chmod +x start.sh
    echo "✅ permission set for start.sh"
fi

echo ""
echo "=========================================="
echo "🎉 Setup Complete!"
echo "To start the application, run:"
echo "   ./start.sh"
echo "=========================================="
