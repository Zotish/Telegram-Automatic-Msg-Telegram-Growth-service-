import os
from dotenv import load_dotenv
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import SessionLocal, Account, Group, AccountGroupAssignment, Config
from telegram_worker import initiate_login, complete_login, start_automation_engine, stop_automation_engine, automation_running, join_group
from context_processor import extract_text_from_pdf, extract_text_from_docx, extract_text_from_url

app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
async def startup_event():
    """Auto-start automation engine when server starts."""
    await start_automation_engine(API_ID, API_HASH)
    print("✅ Automation engine auto-started on server startup.")

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()


# ─────────────────────────────────────────────
# ACCOUNT ENDPOINTS
# ─────────────────────────────────────────────

@app.get("/accounts")
def get_accounts(db: Session = Depends(get_db)):
    return db.query(Account).all()

@app.post("/accounts")
def add_account(data: dict, db: Session = Depends(get_db)):
    existing = db.query(Account).filter(Account.phone == data.get("phone")).first()
    if existing:
        raise HTTPException(status_code=400, detail="Account already exists")
    new_acc = Account(**data)
    db.add(new_acc)
    db.commit()
    db.refresh(new_acc)
    return new_acc

@app.delete("/accounts/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    acc = db.query(Account).filter(Account.id == account_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    db.delete(acc)
    db.commit()
    return {"message": "Deleted"}

@app.patch("/accounts/{account_id}/status")
def update_account_status(account_id: int, data: dict, db: Session = Depends(get_db)):
    acc = db.query(Account).filter(Account.id == account_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    acc.status = data.get("status", acc.status)
    db.commit()
    return {"message": "Status updated", "status": acc.status}


# ─────────────────────────────────────────────
# GROUP ENDPOINTS
# ─────────────────────────────────────────────

@app.get("/groups")
def get_groups(db: Session = Depends(get_db)):
    return db.query(Group).all()

@app.post("/groups")
def add_group(data: dict, db: Session = Depends(get_db)):
    existing = db.query(Group).filter(Group.username == data.get("username")).first()
    if existing:
        raise HTTPException(status_code=400, detail="Group already exists")
    new_group = Group(**data)
    db.add(new_group)
    db.commit()
    db.refresh(new_group)
    return new_group

@app.patch("/groups/{group_id}")
def update_group(group_id: int, data: dict, db: Session = Depends(get_db)):
    grp = db.query(Group).filter(Group.id == group_id).first()
    if not grp:
        raise HTTPException(status_code=404, detail="Group not found")
    for key, value in data.items():
        setattr(grp, key, value)
    db.commit()
    return {"message": "Group updated"}

@app.patch("/groups/{group_id}/toggle-active")
def toggle_group_active(group_id: int, db: Session = Depends(get_db)):
    grp = db.query(Group).filter(Group.id == group_id).first()
    if not grp:
        raise HTTPException(status_code=404, detail="Group not found")
    grp.is_active = not grp.is_active
    db.commit()
    return {"is_active": grp.is_active}

@app.delete("/groups/{group_id}")
def delete_group(group_id: int, db: Session = Depends(get_db)):
    grp = db.query(Group).filter(Group.id == group_id).first()
    if not grp:
        raise HTTPException(status_code=404, detail="Group not found")
    db.delete(grp)
    db.commit()
    return {"message": "Deleted"}

@app.post("/groups/{group_id}/process-content")
async def process_group_content(
    group_id: int,
    url: str = Form(None),
    file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    grp = db.query(Group).filter(Group.id == group_id).first()
    if not grp:
        raise HTTPException(status_code=404, detail="Group not found")
        
    extracted_text = ""
    
    if file:
        content = await file.read()
        if file.filename.endswith(".pdf"):
            extracted_text = await extract_text_from_pdf(content)
            if extracted_text == "IMAGE_PDF":
                raise HTTPException(status_code=422, detail="IMAGE_PDF: এই PDF থেকে text extract করা যাচ্ছে না কারণ এটি image-based। Content টি manually AI Context field এ লিখুন।")
        elif file.filename.endswith(".docx"):
            extracted_text = await extract_text_from_docx(content)
        elif file.filename.endswith(".txt"):
            extracted_text = content.decode("utf-8")
        else:
            raise HTTPException(status_code=400, detail="শুধুমাত্র .pdf, .docx, .txt file সমর্থিত")
            
    if url:
        try:
            # Disable SSL verify for local dev environments if needed
            url_text = await extract_text_from_url(url, verify_ssl=False)
            if extracted_text:
                extracted_text += "\n\n" + url_text
            else:
                extracted_text = url_text
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"URL extraction failed: {str(e)}")
            
    if not extracted_text:
        raise HTTPException(status_code=400, detail="No content provided")
        
    # Replace existing content with new content
    grp.content = extracted_text

    db.commit()
    return {"status": "SUCCESS", "message": "Content updated successfully", "length": len(extracted_text)}


# ─────────────────────────────────────────────
# ASSIGNMENT ENDPOINTS (Account ↔ Group)
# ─────────────────────────────────────────────

@app.get("/assignments")
def get_assignments(db: Session = Depends(get_db)):
    rows = db.query(AccountGroupAssignment).all()
    result = []
    for r in rows:
        result.append({
            "id": r.id,
            "account_id": r.account_id,
            "group_id": r.group_id,
            "account_phone": r.account.phone if r.account else None,
            "group_name": r.group.name if r.group else None,
            "group_username": r.group.username if r.group else None,
        })
    return result

@app.post("/assignments")
def assign_account_to_group(data: dict, db: Session = Depends(get_db)):
    existing = db.query(AccountGroupAssignment).filter(
        AccountGroupAssignment.account_id == data["account_id"],
        AccountGroupAssignment.group_id == data["group_id"]
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Assignment already exists")
    new_assign = AccountGroupAssignment(**data)
    db.add(new_assign)
    db.commit()
    return {"message": "Assigned"}

@app.delete("/assignments/{assignment_id}")
def remove_assignment(assignment_id: int, db: Session = Depends(get_db)):
    row = db.query(AccountGroupAssignment).filter(AccountGroupAssignment.id == assignment_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Assignment not found")
    db.delete(row)
    db.commit()
    return {"message": "Removed"}

@app.post("/assignments/{assignment_id}/join")
async def trigger_join_group(assignment_id: int, db: Session = Depends(get_db)):
    assignment = db.query(AccountGroupAssignment).filter(AccountGroupAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
        
    result = await join_group(assignment.account, assignment.group, API_ID, API_HASH)
    if result["status"] == "SUCCESS":
        return result
    raise HTTPException(status_code=400, detail=result["message"])


# ─────────────────────────────────────────────
# AUTH ENDPOINTS (OTP Login & Admin Login)
# ─────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str

class ConfigUpdate(BaseModel):
    id: int | None = None
    active_provider: str
    gemini_api_key: str | None = None
    openai_api_key: str | None = None
    min_delay: int = 40
    max_delay: int = 80

@app.post("/auth/admin-login")
def admin_login(data: LoginRequest):
    correct_email = os.getenv("ADMIN_EMAIL", "chandrazotish@gmail.com")
    correct_password = os.getenv("ADMIN_PASSWORD", "iLIKEYOU@2")
    
    if data.email == correct_email and data.password == correct_password:
        return {"status": "SUCCESS", "message": "Login successful"}
    raise HTTPException(status_code=401, detail="Invalid email or password")

@app.post("/auth/send-otp")
async def send_otp(data: dict, db: Session = Depends(get_db)):
    phone = data["phone"]
    acc = db.query(Account).filter(Account.phone == phone).first()
    proxy = None
    if acc and acc.proxy_ip:
        import socks
        proxy = (socks.SOCKS5, acc.proxy_ip, acc.proxy_port, True, acc.proxy_user, acc.proxy_pass)
    status = await initiate_login(phone, API_ID, API_HASH, proxy=proxy)
    return {"status": status}

@app.post("/auth/verify-otp")
async def verify_otp(data: dict):
    phone = data["phone"]
    otp = data["otp"]
    result = await complete_login(phone, otp)
    return result

# ─────────────────────────────────────────────
# ENGINE ENDPOINTS (Start/Stop Automation)
# ─────────────────────────────────────────────

@app.get("/automation/status")
def get_automation_status():
    from telegram_worker import automation_running
    return {"running": automation_running}

@app.post("/automation/start")
async def start_automation():
    if await start_automation_engine(API_ID, API_HASH):
        return {"message": "Automation Started", "running": True}
    return {"message": "Automation already running", "running": True}

@app.post("/automation/stop")
def stop_automation():
    stop_automation_engine()
    return {"message": "Automation Stopped", "running": False}

# --- CONFIG ENDPOINTS ---

@app.get("/config")
def get_config(db: Session = Depends(get_db)):
    config = db.query(Config).first()
    if not config:
        config = Config(active_provider="gemini")
        db.add(config)
        db.commit()
        db.refresh(config)
    return config

@app.post("/config")
def update_config(data: ConfigUpdate, db: Session = Depends(get_db)):
    config = db.query(Config).first()
    if not config:
        config = Config()
        db.add(config)
    
    config.active_provider = data.active_provider
    if data.gemini_api_key is not None:
        config.gemini_api_key = data.gemini_api_key
    if data.openai_api_key is not None:
        config.openai_api_key = data.openai_api_key
    config.min_delay = data.min_delay
    config.max_delay = data.max_delay
    
    db.commit()
    return {"status": "SUCCESS", "message": "Configuration updated"}