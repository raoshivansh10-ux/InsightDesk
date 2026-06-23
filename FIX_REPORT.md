# Diagnostic and Resolution Report: Connection Issues

This report details why `localhost:5173` became unavailable after laptop sleep or system restarts, and how we resolved the startup process reliability.

---

## 🔍 1. Root Cause Analysis

When a developer starts Vite (`npm run dev`) or Flask (`python wsgi.py`) inside an active shell session, these processes run as background child tasks of the terminal shell session. 
- **System Restarts / Shutdowns**: The OS terminates all shell processes.
- **Laptop Deep Sleep / Hibernate**: The OS can suspend the processes or dump volatile memory, leading to socket timeout/failures and process crashes.
- **Port Collisions**: Sometimes when terminal apps close unexpectedly, the process running Node/Flask is not cleanly shutdown, leaving them listening on the port. When trying to run the app again, it fails with `EADDRINUSE`.

Since there was no daemon or automatic recovery script running to re-spin the servers after reboot, the ports refused connection.

---

## 🛠️ 2. Solution Applied

We introduced an automated and persistent Windows Command setup to make starting the system easy and collision-free:

1. **Port Collision Killer**: In the launcher, we check if ports `5000` (Flask) and `5173` (Vite) are being held by orphan processes. If so, they are terminated immediately using `taskkill /f /pid`.
2. **Modular Batch Scripts**:
   - `start_backend.bat`: Verifies Python is set up and starts the Flask API.
   - `start_frontend.bat`: Verifies npm, installs any missing packages (`npm install`), and starts the Vite Dev server.
   - `start_all.bat`: The master launcher that clears ports, spins up both processes concurrently in separate window titles, and opens the browser.
3. **Automated Health Check**: Added `check_health.py` to allow the user or backend worker to verify server state on localhost.

---

## 📂 3. Files Created or Changed

| File Path | Action | Description |
| :--- | :--- | :--- |
| [start_all.bat](file:///c:/Users/yadhu/.gemini/antigravity-ide/scratch/start_all.bat) | **[NEW]** | Master launcher that cleans ports, starts backend & frontend, and opens Chrome/Edge. |
| [start_backend.bat](file:///c:/Users/yadhu/.gemini/antigravity-ide/scratch/start_backend.bat) | **[NEW]** | Launches Python Flask. |
| [start_frontend.bat](file:///c:/Users/yadhu/.gemini/antigravity-ide/scratch/start_frontend.bat) | **[NEW]** | Installs node modules and runs `npm run dev`. |
| [check_health.py](file:///c:/Users/yadhu/.gemini/antigravity-ide/scratch/InsightDesk/check_health.py) | **[NEW]** | Test script validating local HTTP responses. |
| [START_PROJECT.md](file:///c:/Users/yadhu/.gemini/antigravity-ide/scratch/InsightDesk/START_PROJECT.md) | **[NEW]** | Operational instructions for running the project. |

---

## 🚀 4. Correct Startup Procedure

To start the application at any point (including immediately after rebooting your machine):

1. Double-click the file [start_all.bat](file:///c:/Users/yadhu/.gemini/antigravity-ide/scratch/start_all.bat).
2. The browser will open automatically. Bookmark and load the following URL:
   - **Frontend App URL**: `http://localhost:5173/`
