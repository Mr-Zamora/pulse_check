#!/bin/bash
# Start Pulse Check with optimized uWSGI configuration

echo "Starting Pulse Check with uWSGI..."

# Check if uwsgi.ini exists
if [ ! -f "uwsgi.ini" ]; then
    echo "ERROR: uwsgi.ini not found!"
    exit 1
fi

# Check if admin.py exists
if [ ! -f "admin.py" ]; then
    echo "ERROR: admin.py not found!"
    echo "Please copy admin.py.example to admin.py and set your credentials."
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
pip install uwsgi

# Initialize database
echo "Initializing database..."
python -c "from configuration import init_db; init_db()"

# Create logs directory
mkdir -p logs

# Start uWSGI
echo "Starting uWSGI with optimized configuration..."
uwsgi --ini uwsgi.ini --http :5000
