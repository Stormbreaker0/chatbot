#!/bin/bash

# Navigate to the directory containing your Python application
#cd /path/to/your/python/app

# Create and activate the virtual environment (if it doesn't exist)
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# Check and install packages from requirements.txt if they are not already installed
pip check || pip install -r requirements.txt 

echo "starting bot..."
# Run the Python application
python chatbot.py

# Deactivate the virtual environment
deactivate

