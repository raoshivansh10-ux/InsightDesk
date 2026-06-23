# InsightDesk & Vex-Hero Production Deployment Guide

This guide describes how to deploy the containerized InsightDesk backend (Flask) and Vex-Hero frontend (React) services to a production environment.

## 📋 System Architecture

The deployment orchestrates three primary layers:
1. **Frontend Layer (Nginx)**: Serves static built React assets on port 80 and reverse proxies `/datasets/api` and `/dashboard/api` routes to the backend.
2. **Backend Layer (Gunicorn/Flask)**: Listens internally on port 5000 and connects to PostgreSQL and external APIs (Supabase, Gemini).
3. **Database Layer (PostgreSQL)**: Persists operational relational schema and user datasets.

---

## ⚙️ Environment Variables Checklist

Create a production `.env` file in the root directory before running containers. Ensure these credentials are secure and not checked into source control.

| Variable Name | Description | Example / Recommendation |
| :--- | :--- | :--- |
| `FLASK_CONFIG` | Specifies backend config class | `production` |
| `SECRET_KEY` | Flask session and signing secret | *Generate a secure 64-character random string* |
| `POSTGRES_USER` | PostgreSQL admin username | `postgres` |
| `POSTGRES_PASSWORD`| PostgreSQL admin password | *Generate a secure password* |
| `POSTGRES_DB` | Relational database name | `insightdesk` |
| `GEMINI_API_KEY` | API Key for natural language features | Get key from Google AI Studio |
| `SUPABASE_URL` | Supabase endpoint URL for user auth | `https://your-project.supabase.co` |
| `SUPABASE_ANON_KEY`| Client anon key for token verification | Obtained from Supabase API dashboard |
| `SUPABASE_SERVICE_ROLE_KEY` | Admin role key (for database sync/admin bypass) | Obtained from Supabase settings |
| `MAIL_SERVER` | SMTP Mail Server address | `smtp.sendgrid.net` |
| `MAIL_PORT` | SMTP connection port | `587` (TLS) or `465` (SSL) |
| `MAIL_USERNAME` | SMTP auth user identifier | `apikey` |
| `MAIL_PASSWORD` | SMTP API key/password | *SMTP credentials* |
| `MAIL_DEFAULT_SENDER` | Default email sender address | `reports@insightdesk.app` |

---

## 🚀 Running the Containers

Ensure you have Docker and Docker Compose installed on your host system.

### 1. Build and Start Services
To build and run all services in detached (background) mode:
```bash
docker compose up -d --build
```
This command builds the frontend static package using Node and sets up the Flask and PostgreSQL services.

### 2. Verify Server Status
Verify that all containers are healthy:
```bash
docker compose ps
```
Or check the server logs:
```bash
docker compose logs -f web
```

---

## 💾 Database Schema Initialization & Migrations

Flask automatically calls `db.create_all()` on application factory startup if tables do not exist. However, for structured production migrations (Alembic):

### 1. Generate a New Migration
Run inside the running backend container:
```bash
docker compose exec web flask db migrate -m "Production schema init"
```

### 2. Apply Migrations to Production
To run database upgrades on start or manually:
```bash
docker compose exec web flask db upgrade
```

---

## 🔒 Production HTTPS / Nginx SSL Setup

To configure secure SSL (HTTPS) termination in Nginx, you should use Let's Encrypt and Certbot on your host machine.

### Option A: Certbot on Host Machine
1. Install certbot on the host:
   ```bash
   sudo apt-get install certbot
   ```
2. Generate SSL certificates for your domain:
   ```bash
   sudo certbot certonly --standalone -d yourdomain.com
   ```
3. Mount the certificates into Nginx container. Update `docker-compose.yml` to bind certificate directories:
   ```yaml
   frontend:
     ports:
       - "80:80"
       - "443:443"
     volumes:
       - /etc/letsencrypt:/etc/letsencrypt:ro
   ```
4. Adjust `nginx.conf` in the frontend code to configure server blocks on port 443 with SSL paths.

---

## 🩺 Production Monitoring & Diagnostics

- **Health Checks**: PostgreSQL containers have a pre-configured `pg_isready` check.
- **Log Files**: Application logs are stored inside the container at `/app/instance/insightdesk.log`.
- **Database Backup**:
  To export a dump of the active PostgreSQL database:
  ```bash
  docker compose exec db pg_dump -U postgres insightdesk > backup.sql
  ```
