# Start/Stop Guide for LoL AI Coaching Overlay

## Starting the Application

### Method 1: Start Both Services (Recommended)

**Step 1: Start Backend**
```bash
cd backend
python main.py
```
The backend will run on http://127.0.0.1:8001

**Step 2: Start Frontend (in a new terminal)**
```bash
cd frontend
npm run electron:dev
```
The frontend will run on http://localhost:5173 and launch the Electron overlay

### Method 2: Background Processes

**Start backend in background:**
```bash
cd backend && python main.py &
```

**Start frontend in background:**
```bash
cd frontend && npm run electron:dev &
```

## Stopping the Application

### Windows

**Option 1: Stop via Process Kill (Recommended)**

1. **Stop Backend (Port 8001)**
```bash
# Find the process using port 8001
netstat -ano | findstr :8001

# Kill the process (replace PID with the actual process ID)
taskkill //F //PID <PID>
```

2. **Stop Frontend (Port 5173 + Electron)**
```bash
# Find processes using port 5173
netstat -ano | findstr :5173

# Kill the Vite server
taskkill //F //PID <PID>

# Kill all Electron processes
taskkill //F //IM electron.exe
```

**Option 2: Stop via Terminal**
- If running in foreground, press `Ctrl+C` in each terminal window
- Close the Electron window to stop the frontend

### Linux/macOS

**Option 1: Stop via Process Kill**

1. **Stop Backend (Port 8001)**
```bash
# Find the process using port 8001
lsof -ti:8001

# Kill the process
kill -9 $(lsof -ti:8001)
```

2. **Stop Frontend (Port 5173)**
```bash
# Find and kill process on port 5173
kill -9 $(lsof -ti:5173)

# Kill Electron processes
pkill -f electron
```

**Option 2: Stop via Terminal**
- Press `Ctrl+C` in each terminal window
- Close the Electron window

## Handling Duplicate Port Issues

### Problem: "Port already in use" Error

This occurs when a previous instance is still running on the required port.

### Windows Solution

**For Backend (Port 8001):**
```bash
# Step 1: Find what's using port 8001
netstat -ano | findstr :8001

# Step 2: Kill the process
taskkill //F //PID <PID_NUMBER>

# Step 3: Verify port is free
netstat -ano | findstr :8001

# Step 4: Restart backend
cd backend && python main.py
```

**For Frontend (Port 5173):**
```bash
# Step 1: Find what's using port 5173
netstat -ano | findstr :5173

# Step 2: Kill the process
taskkill //F //PID <PID_NUMBER>

# Step 3: Restart frontend
cd frontend && npm run electron:dev
```

**Kill All Related Processes (Nuclear Option):**
```bash
# Kill all Python processes (BE CAREFUL - this kills ALL Python)
taskkill //F //IM python.exe

# Kill all Node processes (BE CAREFUL - this kills ALL Node)
taskkill //F //IM node.exe

# Kill all Electron processes
taskkill //F //IM electron.exe
```

### Linux/macOS Solution

**For Backend (Port 8001):**
```bash
# Step 1: Find and kill process on port 8001
kill -9 $(lsof -ti:8001)

# Step 2: Verify port is free
lsof -ti:8001

# Step 3: Restart backend
cd backend && python main.py
```

**For Frontend (Port 5173):**
```bash
# Step 1: Find and kill process on port 5173
kill -9 $(lsof -ti:5173)

# Step 2: Restart frontend
cd frontend && npm run electron:dev
```

**Kill All Related Processes (Nuclear Option):**
```bash
# Kill all Python main.py processes
pkill -f "python main.py"

# Kill all npm processes
pkill -f "npm run electron:dev"

# Kill all Electron processes
pkill -f electron
```

## Quick Reference Commands

### Windows Quick Commands

```bash
# Check if ports are in use
netstat -ano | findstr :8001
netstat -ano | findstr :5173

# Kill specific process
taskkill //F //PID <PID>

# Kill all instances
taskkill //F //IM python.exe
taskkill //F //IM node.exe
taskkill //F //IM electron.exe
```

### Linux/macOS Quick Commands

```bash
# Check if ports are in use
lsof -ti:8001
lsof -ti:5173

# Kill processes on specific ports
kill -9 $(lsof -ti:8001)
kill -9 $(lsof -ti:5173)

# Kill all instances
pkill -f "python main.py"
pkill -f "npm run electron:dev"
pkill -f electron
```

## Troubleshooting

### Issue: Backend won't start
**Error:** `error while attempting to bind on address ('127.0.0.1', 8001)`

**Solution:**
1. Kill any process using port 8001 (see above)
2. Wait 5 seconds
3. Try starting again

### Issue: Frontend won't connect to backend
**Symptoms:** Overlay shows "Connecting..." or no data

**Solution:**
1. Verify backend is running: Visit http://127.0.0.1:8001/health
2. Check backend terminal for errors
3. Restart both services in order (backend first, then frontend)

### Issue: Multiple Electron windows
**Problem:** Multiple overlay windows appear

**Solution:**
```bash
# Windows
taskkill //F //IM electron.exe

# Linux/macOS
pkill -f electron

# Then restart frontend
cd frontend && npm run electron:dev
```

### Issue: "Module not found" errors
**Solution:**
```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

## Development Workflow

### Recommended Development Setup

1. **Open two terminal windows side by side**

2. **Terminal 1 - Backend:**
```bash
cd backend
python main.py
```
Keep this running and watch for errors

3. **Terminal 2 - Frontend:**
```bash
cd frontend
npm run electron:dev
```
The Electron overlay will auto-reload on code changes

4. **When done developing:**
   - Press `Ctrl+C` in both terminals
   - Or close the Electron window and then stop backend with `Ctrl+C`

### Clean Restart

If things get weird, do a clean restart:

**Windows:**
```bash
# Kill everything
taskkill //F //IM python.exe
taskkill //F //IM node.exe
taskkill //F //IM electron.exe

# Wait 5 seconds

# Start fresh
cd backend && python main.py
# In new terminal:
cd frontend && npm run electron:dev
```

**Linux/macOS:**
```bash
# Kill everything
pkill -f "python main.py"
pkill -f "npm run electron:dev"
pkill -f electron

# Wait 5 seconds

# Start fresh
cd backend && python main.py
# In new terminal:
cd frontend && npm run electron:dev
```

## Port Configuration

If you need to change ports (to avoid conflicts):

**Backend Port (default: 8001)**
- Edit `backend/main.py` line with `uvicorn.run(..., port=8001)`
- Update `frontend/src/services/websocket.ts` WebSocket URL

**Frontend Port (default: 5173)**
- Edit `frontend/vite.config.ts` server configuration
- Or set environment variable: `PORT=5174 npm run electron:dev`

## Environment Variables

Make sure these are set in `backend/.env`:
```env
RIOT_API_KEY=your_riot_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

Without these, the backend will start but won't function fully.
