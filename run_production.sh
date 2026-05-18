#!/bin/bash
# Production deployment script for Pulse Check

echo "Starting Pulse Check in production mode..."

# Check if admin.py exists
if [ ! -f "admin.py" ]; then
    echo "ERROR: admin.py not found!"
    echo "Please copy admin.py.example to admin.py and set your credentials."
    exit 1
fi

# Install/update dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Initialize database
echo "Initializing database..."
python -c "from configuration import init_db; init_db()"

# Run with Gunicorn
echo "Starting Gunicorn with 4 workers..."
gunicorn -w 4 \
    -b 0.0.0.0:5000 \
    --timeout 120 \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    --log-level info \
    app:app
