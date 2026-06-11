# AI Viva Examiner

An AI-powered project viva examination system. Students upload their project files (PDF report, PPTX, source code ZIP), and the AI conducts a dynamic oral examination with follow-up questions, weak-answer detection, and detailed performance analytics.

---

## Project Structure

```
viva-ai/
├── backend/          # FastAPI Python backend
│   ├── app/
│   │   ├── api/routes/   # auth, submissions, viva, analytics, users
│   │   ├── core/         # config, database, security
│   │   ├── models/       # SQLAlchemy models
│   │   ├── services/     # document_parser, ai_service, viva_engine
│   │   └── utils/
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
└── frontend/         # React + Vite + TypeScript frontend
    ├── src/
    │   ├── pages/        # Login, Register, Dashboard, Upload, Viva, Results, Analytics, Faculty
    │   ├── components/   # Layout, UI components
    │   ├── services/     # Axios API client
    │   └── store/        # Zustand auth store
    └── package.json
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL
- Redis

### Backend Setup

```bash
cd backend

# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env
# Edit .env — add your OPENAI_API_KEY, DATABASE_URL, SECRET_KEY

# 4. Run server
uvicorn app.main:app --reload --port 8000
```

API docs available at: http://localhost:8000/api/docs

### Frontend Setup

```bash
cd frontend

# 1. Install dependencies
npm install

# 2. Start dev server
npm run dev
```

App available at: http://localhost:5173

---

## API Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/register | Register student/faculty |
| POST | /api/auth/login | Login |
| POST | /api/submissions/ | Upload project files |
| GET  | /api/submissions/ | List my submissions |
| POST | /api/viva/start | Start a viva session |
| POST | /api/viva/answer | Submit an answer |
| GET  | /api/viva/{id} | Get session transcript |
| GET  | /api/analytics/me | Personal analytics |
| GET  | /api/analytics/session/{id} | Session analytics |
| GET  | /api/analytics/faculty/overview | Faculty dashboard |

---

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy (async), PostgreSQL, Redis
- **AI**: OpenAI GPT-4o
- **Document Parsing**: PyMuPDF, python-pptx
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Recharts, Zustand
