@echo off
REM Production deployment script for Pulse Check (Windows)

echo Starting Pulse Check in production mode...

REM Check if admin.py exists
if not exist "admin.py" (
    echo ERROR: admin.py not found!
    echo Please copy admin.py.example to admin.py and set your credentials.
    exit /b 1
)

REM Install/update dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Initialize database
echo Initializing database...
python -c "from configuration import init_db; init_db()"

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

REM Run with Gunicorn (or waitress on Windows)
echo Starting production server...
waitress-serve --host=0.0.0.0 --port=5000 --threads=8 app:app
