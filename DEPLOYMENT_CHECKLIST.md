# Production Deployment Checklist

## Pre-Deployment

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up Admin Credentials
```bash
# Copy the example file
cp admin.py.example admin.py

# Edit admin.py and change:
# - ADMIN_USERNAME (default: "admin")
# - ADMIN_PASSWORD (default: "changeme")
# - SECRET_KEY (generate with: python -c "import secrets; print(secrets.token_hex(32))")
```

### 3. Initialize Database
```bash
python -c "from configuration import init_db; init_db()"
```

### 4. Test Locally First
```bash
# Development server (testing only)
python app.py

# Visit http://localhost:5000
# Test with 2-3 browser tabs as different students
```

---

## Production Deployment

### Windows
```bash
run_production.bat
```

### Linux/Mac
```bash
chmod +x run_production.sh
./run_production.sh
```

This will:
- ✅ Check for admin.py
- ✅ Install dependencies
- ✅ Initialize database
- ✅ Start production server (Waitress/Gunicorn)
- ✅ Run with 4 workers (adjust based on class size)

---

## Configuration by Class Size

### Small Class (5-10 students)
```bash
# Windows
waitress-serve --host=0.0.0.0 --port=5000 --threads=4 app:app

# Linux/Mac
gunicorn -w 2 -b 0.0.0.0:5000 app:app
```

### Medium Class (10-20 students)
```bash
# Windows
waitress-serve --host=0.0.0.0 --port=5000 --threads=8 app:app

# Linux/Mac
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Large Class (20-30 students)
```bash
# Windows
waitress-serve --host=0.0.0.0 --port=5000 --threads=12 app:app

# Linux/Mac
gunicorn -w 6 -b 0.0.0.0:5000 --timeout 120 app:app
```

---

## Verification Checklist

### Before Class Starts

- [ ] Server is running on production server (not `python app.py`)
- [ ] Admin dashboard accessible at `/admin/login`
- [ ] Admin credentials work
- [ ] Test room created with at least 1 question
- [ ] Test submission works from student view
- [ ] Teacher dashboard shows real-time updates
- [ ] Network accessible to all student devices

### During Class

- [ ] Monitor server logs for errors
- [ ] Check response times (should be <200ms)
- [ ] Watch for "Database locked" errors (should be none)
- [ ] Verify all student submissions appear in real-time
- [ ] Test "Lock Submissions" button works
- [ ] Test "Show Responses" toggle works

### After Class

- [ ] Download backup from admin dashboard
- [ ] Archive responses.csv for records
- [ ] Clear disconnected students if needed
- [ ] Check database file size (WAL files)

---

## Performance Expectations

### With Optimizations Applied

| Metric | Expected Value |
|--------|---------------|
| Response time | 50-150ms |
| Concurrent students | 20-30+ |
| Polling interval | 2 seconds |
| Database queries/request | ~3 |
| Error rate | <1% |

### Warning Signs

🚨 **Response time >500ms**: Check server load, consider more workers  
🚨 **"Database locked" errors**: Increase timeout or reduce workers  
🚨 **Stale data**: Check cache invalidation, restart server  
🚨 **CSV corruption**: Restore from backup, check for crashes  

---

## Troubleshooting

### Students Can't Connect
```bash
# Check server is running
curl http://localhost:5000

# Check firewall allows port 5000
# Windows: netsh advfirewall firewall add rule name="Pulse Check" dir=in action=allow protocol=TCP localport=5000
# Linux: sudo ufw allow 5000
```

### Slow Performance
```bash
# Check worker count
ps aux | grep -E "waitress|gunicorn"

# Increase workers (Linux/Mac)
gunicorn -w 8 -b 0.0.0.0:5000 app:app

# Increase threads (Windows)
waitress-serve --threads=16 app:app
```

### Database Locked Errors
```python
# Check configuration.py has:
timeout=30.0
PRAGMA busy_timeout=30000
PRAGMA journal_mode=WAL
```

### Cache Issues
```bash
# Restart server to clear cache
# Or check responses.csv modification time matches cache
```

---

## Backup & Recovery

### Manual Backup
```bash
# From admin dashboard: Click "Download Backup"
# Or manually copy:
cp database/classroom_pulse.db backup/
cp database/responses.csv backup/
cp database/questions.csv backup/
```

### Restore from Backup
```bash
# Stop server first
cp backup/classroom_pulse.db database/
cp backup/responses.csv database/
cp backup/questions.csv database/
# Restart server
```

### Automated Backup (Optional)
```bash
# Linux/Mac cron job (daily at 2am)
0 2 * * * cd /path/to/pulse_check && tar -czf backups/backup_$(date +\%Y\%m\%d).tar.gz database/

# Windows Task Scheduler
# Create task to run: tar -czf backups\backup_%date%.tar.gz database\
```

---

## Security Checklist

- [ ] `admin.py` has strong password (not "changeme")
- [ ] `SECRET_KEY` is random and unique
- [ ] `admin.py` is in `.gitignore` (never committed)
- [ ] Server only accessible on local network (not internet)
- [ ] HTTPS enabled if accessible over internet
- [ ] Regular backups of student data
- [ ] `responses.csv` handled per data privacy policy

---

## Scaling Beyond 30 Students

If you need to support 50+ concurrent students:

### Option 1: PostgreSQL Migration
```bash
# Install PostgreSQL
pip install psycopg2-binary

# Migrate data
python migrate_to_postgres.py

# Update configuration.py to use PostgreSQL
```

### Option 2: Redis Caching
```bash
# Install Redis
pip install redis

# Add distributed cache
# Update app.py to use Redis instead of in-memory cache
```

### Option 3: Load Balancer
```bash
# Run multiple app instances
# Use nginx or HAProxy to distribute load
```

---

## Support & Documentation

- **Performance**: See `docs/PERFORMANCE.md`
- **Race Conditions**: See `docs/RACE_CONDITIONS.md`
- **Application Docs**: See `docs/APP_DOCS.md`
- **Technical Spec**: See `docs/SPEC.md`

---

## Quick Reference

### Start Server
```bash
# Windows
run_production.bat

# Linux/Mac
./run_production.sh
```

### Stop Server
```bash
# Windows: Ctrl+C in terminal

# Linux/Mac: Ctrl+C or
pkill -f "gunicorn.*app:app"
```

### View Logs
```bash
# If using production scripts
tail -f logs/access.log
tail -f logs/error.log
```

### Test Race Conditions
```bash
python test_race_conditions.py
```

---

## Emergency Procedures

### Server Crash During Class
1. Restart server immediately: `run_production.bat` or `./run_production.sh`
2. Students will auto-reconnect within 2 seconds
3. Check logs for error cause
4. If database corrupted, restore from last backup

### Data Corruption
1. Stop server
2. Check `responses.csv` for corruption (open in text editor)
3. If corrupted, restore from backup
4. If no backup, manually fix CSV (it's human-readable)
5. Restart server

### Network Issues
1. Check server is running: `curl http://localhost:5000`
2. Check firewall allows port 5000
3. Check students on same network
4. Test with teacher device first

---

**Last Updated**: After performance and race condition fixes  
**Safe For**: 20-30 concurrent students  
**Tested With**: 10 students live deployment
