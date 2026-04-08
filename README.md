# TG Automation Dashboard

This is a complete Telegram Account Manager and AI-powered Automation Engine. The project consists of a React frontend and a FastAPI (Python) backend using Telethon and Google Gemini AI.

## Requirements

- **Python 3.8+**
- **Node.js (npm)**

---

## Environment Setup

Inside the `backend/` folder, make sure you have your `.env` file configured.
Create `.env` if it doesn't exist and add the following format:

```ini
API_ID=your_api_id
API_HASH=your_api_hash
GEMINI_API_KEY=your_gemini_key
```

---

## 🚀 How to Run the Project

You need to run both the Backend Server and the Frontend UI simultaneously in two separate terminal windows.

### 1. Start the Backend Server
Open your first terminal and run the following commands:

```bash
cd backend
pip install -r requirements.txt  # If requirements.txt is not present: pip install fastapi uvicorn sqlalchemy python-dotenv telethon pysocks
source .venv/bin/activate  # ভাচুয়াল এনভায়রনমেন্ট অ্যাক্টিভেট করতে
uvicorn main:app --reload --port 8000

```
*The backend API will run on http://127.0.0.1:8000*

### 2. Start the Frontend Dashboard
Open your second terminal and run the following commands:

```bash
cd frontend
npm install
npm start
```
*The dashboard UI will automatically open in your browser at http://localhost:3000*

---

## 🛠 Features & Flow Instructions

1. **Add Accounts:** Go to the `Accounts` tab to add numbers and proxies.
2. **OTP Login:** Click the `📱 OTP Login` button beside an account. This will trigger Telegram to send an OTP to your phone/Telegram app. Enter the OTP in the popup to successfully login.
3. **Add Target Groups:** Go to the `Groups` tab and add the groups you want to message, along with the "AI Context" (e.g., details about what the bot should say in this group).
4. **Assign Accounts:** Go to the `Assignments` tab and link the verified accounts to specific groups.
5. **Start Automation:** Click the `🚀 Start Automation` button in the top right corner of the dashboard to begin sending context-aware, human-like AI messages automatically.
