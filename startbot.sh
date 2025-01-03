#!/bin/bash

# Navigate to the directory containing your Python application
cd /home/virgil/Desktop/chatbot || { echo "Failed to navigate to /home/virgil/Desktop/chatbot"; exit 1; }

# Create and activate the virtual environment (if it doesn't exist)
if [ ! -d "venv" ]; then
    python3 -m venv venv || { echo "Failed to create virtual environment"; exit 1; }
fi

# Activate the virtual environment
source venv/bin/activate || { echo "Failed to activate virtual environment"; exit 1; }

pip install -r requirements.txt

echo "starting the bot..."
# Run the Python application
python chatbot.py || { echo "Failed to start chatbot"; exit 1; }

# Deactivate the virtual environment
deactivate || { echo "Failed to deactivate virtual environment"; exit 1; }

echo "Script completed successfully"
