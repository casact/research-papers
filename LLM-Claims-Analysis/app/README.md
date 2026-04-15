# Web Application

React + Flask interface for the LLM Claims Analysis Pipeline.

## Tech Stack

- Backend: Flask, Python 3.8+
- Frontend: React, Vite

## Quick Start

### Backend
```bash
cd backend
pip install -r requirements.txt
python app.py
```
API runs at `http://localhost:5001`

### Frontend
```bash
cd frontend
npm install
npm run dev
```
App runs at `http://localhost:3000`

## Structure

```
app/
├── backend/          # Flask API
│   ├── app.py
│   └── requirements.txt
└── frontend/         # React UI
    ├── src/
    └── package.json
```

---

*This software was developed and implemented by MDSight, LLC with project management by Lieberthal & Associates, LLC and funding from the Casualty Actuarial Society. Licensed under MPL-2.0.*
