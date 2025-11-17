# 🌐🤖 Voice Health Advisor – IBM-Themed Futuristic UI (Mock Mode)

**Abstract:** Voice + text health advisor that provides self‑care guidance, OTC suggestions, and when to seek help. Runs **offline** in **Mock Mode** but keeps **IBM services in code** for evaluation.

## Features
- Futuristic IBM corporate theme (Deep Space Blue #0F62FE) with soft animated waves
- Voice input (mic) + voice output (browser TTS)
- Semi‑smart triage with severity badge (LOW / MODERATE / URGENT)
- Local JSON history (Cloudant simulation)
- IBM integration present in code (Watson Assistant stub)

## Run (Windows)
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Open: http://localhost:5000

## IBM Services (included for marks, disabled in demo)
- Watsonx Assistant — API stub in `app.py`
- Cloudant — simulated via `local_data/history.json`
- Text-to-Speech — simulated via browser `speechSynthesis`

## Team
| Name | Roll Number |
|---|---|
| Anupam Dwivedi | 24100BTCSDSI17463 |
| Dipti Narware | 24100BTCSDSI17471 |
| Aditi | 24100BTCSDSI17457 |
| Nandini Bhandari | 24100BTCSDSI17478 |
| Sukanya Jadon | 24100BTCSDSI17491 |

Course: **B.Tech – CSE (Data Science & AI)**

## Disclaimer
Educational guidance only — not a medical diagnosis.
