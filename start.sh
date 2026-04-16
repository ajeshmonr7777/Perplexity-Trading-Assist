#!/bin/bash
# Start the Perplexity Trading application on port 8001

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

uvicorn main:app --reload --port 8001
