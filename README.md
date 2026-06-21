# InsightDesk: An AI-Powered Business Intelligence and Decision Support Platform

InsightDesk is a business intelligence platform that goes beyond reporting numbers. It uploads sales data, cleans it, calculates KPIs, monitors health scores, and actively explains *why* changes happen (Automated Root Cause Analysis) before providing grounded, AI-powered recommendations.

## Core Promise
Upload sales data → cleaned data, KPIs, a Health Score, anomaly alerts, automated root-cause breakdowns, NLQ + grounded AI Q&A, forecasts, grounded recommendations, on-demand and scheduled reports.

## Final Tech Stack
- **Frontend**: HTML/CSS/JS + Jinja2, Chart.js
- **Backend**: Flask (Python 3.11+), Blueprints per module
- **Data Analytics**: Pandas, NumPy
- **Database**: PostgreSQL (prod) / SQLite (dev) + SQLAlchemy + Alembic
- **Anomaly Detection**: Z-score, IQR + IsolationForest
- **Root Cause Analysis**: Pandas groupby-based contribution decomposition
- **Forecasting**: Prophet + RandomForest/XGBoost
- **AI/NLQ/Recs**: Gemini API with function calling
- **Reporting**: WeasyPrint (PDF), Celery Beat (Scheduled Emails)
- **Background Jobs**: Celery + Redis

---

## ✅ Implemented Features (Phases 1-4 & 6 Partial)

### Phase 1: Auth & Multi-user Skeleton
- Database models, configuration, and Docker-ready setup.
- Secure registration, login, logout, and cross-account data isolation.
- React-inspired Tailwind Landing Page with animated typography.

### Phase 2: Industry Templates + Ingestion
- Robust CSV and Excel (`.xlsx`) upload and parsing capabilities.

### Phase 3: Analytics Engine + Executive Health Score
- Computation of key performance indicators (KPIs).
- Computes a Health Score based on revenue growth.

### Phase 4: Anomaly Detection & Business Alerts
- Outlier detection heuristics using Z-Score and IQR.

### Phase 6 (Partial): Dashboard
- Dynamic data visualization using Chart.js.
- Integration between the uploaded dataset and the dashboard views.
- Dedicated Charts API (`/dashboard/api/<id>/charts`).

---

## 🚀 Upcoming Roadmap (To Do)

### Phase 5: Automated Root Cause Analysis (RCA)
- **Database Persistence**: `anomalies` and `root_cause_reports` tables to store historical data.
- **RCA Engine**: Waterfall decomposition method to determine causality across `Category`, `Region`, and `Product`.
- **Candidate Signals**: Inferred stockouts and churn risks heuristics.

### Phase 7: Forecasting Module
- **Forecasting Engine**: Prophet + RandomForest/XGBoost predictive model with backtesting.
- **Dashboard Visuals**: "Future Projection" line chart with confidence intervals.

### Phase 8: AI Module (NLQ & Recommendations)
- **8a. Explanatory Q&A**: Natural language questions grounded in the stored `root_cause_reports`.
- **8b. Natural Language Queries**: Function-calling via Gemini using an allowlist schema (no model-generated SQL).
- **8c. Recommendation Engine**: Recommendations grounded in RCA data, mapping contributor types to specific action templates.

### Phase 9: Reporting (On-Demand PDF & Scheduled Email Digests)
- **PDF Report Generator**: WeasyPrint compilation of dashboard KPIs, charts, and RCA summaries into PDFs.
- **Scheduled Email Digests**: Celery Beat for weekly digests with `report_subscriptions` (opt-in toggles).

### Phase 10: Testing & Hardening
- Input validation, strict DB isolation checks, and rate limiting for AI features.
- Failure handling for scheduled email dispatch.

### Phase 11: Production Deployment
- Dockerized deploy (app + worker + beat), secrets management, HTTPS, managed Postgres.
- Transactional email provider configured with SPF/DKIM.

### Phase 12: Documentation & Demo Prep
- Final Polish: test datasets, architecture diagrams, demo script.
