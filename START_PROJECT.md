# InsightDesk & Vex-Hero Local Startup Guide

This document describes how to start the application components locally in development mode and troubleshoot connection issues (such as `ERR_CONNECTION_REFUSED`).

---

## ⚡ Quick Start (Windows)

We have provided a master launcher script that automatically cleans port conflicts and spins up the frontend and backend concurrently.

1. Navigate to the project root directory: `c:\Users\yadhu\.gemini\antigravity-ide\scratch`
2. Double-click or run the following file:
   ```cmd
   start_all.bat
   ```
This will:
- Check for and terminate any processes currently occupying ports `5000` (Flask) and `5173` (Vite).
- Open a dedicated command prompt window running the **Backend** server.
- Open a dedicated command prompt window running the **Frontend** server.
- Automatically launch the browser at `http://localhost:5173/`.

---

## 🛠️ Manual Startup Procedure

If you prefer to start the servers manually, run the following commands in separate terminal sessions:

### 1. Start the Flask Backend API
Open a terminal in `c:\Users\yadhu\.gemini\antigravity-ide\scratch\InsightDesk` and run:
```bash
python -m flask --app wsgi.py run --port 5000
```
- **Backend URL**: `http://localhost:5000`
- **Health Check Endpoint**: `http://localhost:5000/`

### 2. Start the React Frontend Dev Server
Open a terminal in `c:\Users\yadhu\.gemini\antigravity-ide\scratch\vex-hero` and run:
```bash
npm run dev
```
- **Frontend URL**: `http://localhost:5173/`

---

## 🔍 Health Status Check

You can run the automated health check script to verify both services are up and responding:

```bash
cd c:\Users\yadhu\.gemini\antigravity-ide\scratch\InsightDesk
python check_health.py
```

---

## 🛑 Common Troubleshooting Steps

### 1. ERR_CONNECTION_REFUSED on Localhost:5173
**Why this happens:** When the laptop restarts or sleeps deeply, the active terminal session running the Vite dev server is killed by the operating system.
**How to resolve:** Re-run `start_all.bat` or run the manual startup instructions above.

### 2. Port Collision / Port Already In Use
If either server fails to start because port 5000 or 5173 is occupied:
1. Open PowerShell as Administrator.
2. Find and terminate processes using:
   - For Flask (Port 5000):
     ```powershell
     Get-Process -Id (Get-NetTCPConnection -LocalPort 5000).OwningProcess | Stop-Process -Force
     ```
   - For Vite (Port 5173):
     ```powershell
     Get-Process -Id (Get-NetTCPConnection -LocalPort 5173).OwningProcess | Stop-Process -Force
     ```
*Note: The `start_all.bat` script executes this cleanup automatically every time it is run.*
