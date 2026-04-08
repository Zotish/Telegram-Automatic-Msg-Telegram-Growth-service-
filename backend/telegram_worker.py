import asyncio
import os
import random
import traceback
import google.generativeai as genai
from telethon import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from sqlalchemy.orm import Session
import socks

from database import SessionLocal, Account, Group, AccountGroupAssignment, Config

# Temporary storage for clients needing OTP

from dotenv import load_dotenv

from openai import OpenAI
pending_logins = {}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")

load_dotenv()

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')
else:
    model = None

openai_client = None
if os.getenv("OPENAI_API_KEY"):
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Varied fallbacks to avoid repetitive "Hmm interesting!"
FALLBACK_MESSAGES = [
    "That's a good point, actually.",
    "I was just thinking about that too!",
    "Interesting! Tell me more.",
    "Yeah, I definitely agree with you there.",
    "Haha, true! I never thought of it that way.",
    "Nice! How long has it been like that?",
    "Sounds cool! Any other thoughts?",
]

# Global flags and states
automation_running = False
active_clients = {}  # phone -> TelegramClient
gemini_cooldown_until = 0  # Timestamp until Gemini is usable again
group_last_senders = {} # group_id -> list of last account_ids [last, second_last]
group_topic_index = {}  # group_id -> current topic index for rotation

# Different perspectives for natural variety
PERSPECTIVES = [
    "Share a short bullish take on",
    "Ask a quick question about",
    "Express genuine curiosity about",
    "Give a brief skeptical thought on",
    "React naturally to the discussion about",
    "Share a quick personal opinion on",
    "Drop a short insight about",
    "React with mild surprise about",
]

def get_current_topic(content: str, group_id: int) -> str:
    """Parse topics separated by '---' and return the current one."""
    if not content or not content.strip():
        return ""
    topics = [t.strip() for t in content.split('---') if t.strip()]
    if not topics:
        return content.strip()
    if len(topics) == 1:
        return topics[0]
    idx = group_topic_index.get(group_id, 0) % len(topics)
    return topics[idx]

def advance_topic(group_id: int, content: str):
    """Move to next topic after a batch is done."""
    if not content:
        return
    topics = [t.strip() for t in content.split('---') if t.strip()]
    if len(topics) <= 1:
        return
    current = group_topic_index.get(group_id, 0)
    group_topic_index[group_id] = (current + 1) % len(topics)
    print(f"🔄 Group {group_id} topic advanced to index {group_topic_index[group_id]} / {len(topics)}")

async def initiate_login(phone, api_id, api_hash, proxy=None):
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    session_path = os.path.join(SESSIONS_DIR, phone)

    # Remove old client from cache if exists
    if phone in active_clients:
        try:
            await active_clients[phone].disconnect()
        except: pass
        del active_clients[phone]

    async def _try_login(fresh=False):
        if fresh:
            # Delete corrupted session file and retry
            for ext in ['', '.session', '.session-journal']:
                path = session_path + ext if ext else session_path + '.session'
                if os.path.exists(path):
                    os.remove(path)
                    print(f"🗑 Deleted corrupt session: {path}")

        client = TelegramClient(session_path, api_id, api_hash, proxy=proxy)
        await client.connect()

        if not await client.is_user_authorized():
            sent_code = await client.send_code_request(phone)
            pending_logins[phone] = {
                "client": client,
                "phone_code_hash": sent_code.phone_code_hash
            }
            return "OTP_SENT"
        else:
            active_clients[phone] = client
            return "AUTHORIZED"

    try:
        return await _try_login(fresh=False)
    except Exception as e:
        err = str(e)
        print(f"⚠️ Login attempt 1 failed for {phone}: {err}")
        if "AuthKey" in err or "two different IP" in err or "auth_key" in err.lower():
            try:
                print(f"🔄 Retrying with fresh session for {phone}...")
                return await _try_login(fresh=True)
            except Exception as e2:
                return f"ERROR: {str(e2)}"
        return f"ERROR: {err}"

async def complete_login(phone, otp_code):
    if phone in pending_logins:
        data = pending_logins[phone]
        client = data["client"]
        try:
            await client.sign_in(phone, otp_code, phone_code_hash=data["phone_code_hash"])
            del pending_logins[phone]
            active_clients[phone] = client  # ✅ cache immediately so automation can use it
            return {"status": "SUCCESS"}
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
    return {"status": "NOT_FOUND"}

# ─────────────────────────────────────────────
# 🤖 AUTOMATION LOGIC
# ─────────────────────────────────────────────

async def get_ai_reply(db: Session, context, prompt_type="chat", user_msg="", history="", sent_today=0):
    global gemini_cooldown_until
    
    # Fetch configuration from database
    config = db.query(Config).first()
    provider = "gemini"
    g_key = GEMINI_KEY
    o_key = os.getenv("OPENAI_API_KEY")
    
    if config:
        provider = config.active_provider
        if config.gemini_api_key: g_key = config.gemini_api_key
        if config.openai_api_key: o_key = config.openai_api_key

    # Decide between Social (Greeting) or Technical (Context) prompt
    is_warmup = sent_today < 3  # First 3 messages of the day are casual
    
    if is_warmup:
        system_rules = (
            "You are a friendly community member. TONE: Very casual, short, human-like. "
            "PURPOSE: Start the day with simple greetings like 'Hi', 'Hello', 'How's everyone?', 'Gm everyone'. "
            "Keep it short (max 5 words). Minimal emojis. No '!' mark."
        )
    else:
        perspective = random.choice(PERSPECTIVES)
        # Extract recent messages from history to avoid repetition
        recent_lines = history.strip().split('\n')[-6:] if history else []
        recent_text = "\n".join(recent_lines)
        system_rules = (
            f"You are a real crypto community member. Current topic: {context}.\n"
            f"Your task: {perspective} the topic above.\n"
            f"STRICT RULES:\n"
            f"- Max 12 words\n"
            f"- Sound human and natural, NOT like a bot\n"
            f"- NEVER start with the token/project name directly\n"
            f"- NEVER repeat or rephrase what was already said recently\n"
            f"- Vary your sentence structure every time\n"
            f"- Rare emojis only (2 out of 10 messages)\n"
            f"- No '!' mark. Use '?' only when genuinely asking\n"
            f"RECENT MESSAGES (DO NOT REPEAT THESE):\n{recent_text}"
        )

    # Handle Gemini Provider
    if provider == "gemini":
        if not g_key or time.time() < gemini_cooldown_until:
            if gemini_cooldown_until > 0 and time.time() < gemini_cooldown_until:
                print(f"⏳ Gemini is on cooldown for {int(gemini_cooldown_until - time.time())}s. Using fallback.")
            return random.choice(FALLBACK_MESSAGES)
        
        genai.configure(api_key=g_key)
        curr_model = genai.GenerativeModel('gemini-2.0-flash')
        
        history_part = f"\nRecent Group History:\n{history}" if history else ""
        prompt = (
            f"{system_rules}\n"
            f"Task: {'Initiate conversation' if prompt_type=='start' else f'Reply to: {user_msg}'}\n"
            f"{history_part}"
        )
        try:
            response = curr_model.generate_content(prompt)
            return response.text.strip() or random.choice(FALLBACK_MESSAGES)
        except Exception as e:
            err_msg = str(e)
            print(f"Gemini Error: {err_msg}")
            if "429" in err_msg or "ResourceExhausted" in err_msg:
                gemini_cooldown_until = time.time() + 900
            return random.choice(FALLBACK_MESSAGES)

    # Handle OpenAI Provider
    elif provider == "openai":
        if not o_key:
            return random.choice(FALLBACK_MESSAGES)
        
        local_openai = OpenAI(api_key=o_key)
        history_part = f"\nRecent Group History:\n{history}" if history else ""
        messages = [
            {"role": "system", "content": system_rules},
            {"role": "user", "content": f"History: {history_part}\nTask: {'Quick thought' if prompt_type=='start' else f'Quick reply to: {user_msg}'}"}
        ]
        try:
            response = local_openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=50
            )
            return response.choices[0].message.content.strip() or random.choice(FALLBACK_MESSAGES)
        except Exception as e:
            print(f"OpenAI Error: {e}")
            return random.choice(FALLBACK_MESSAGES)

    return random.choice(FALLBACK_MESSAGES)

async def load_client(account: Account, api_id, api_hash):
    """Loads and starts a TelegramClient for a given account from DB."""
    if account.phone in active_clients:
        return active_clients[account.phone]
        
    session_path = os.path.join(SESSIONS_DIR, account.phone)
    proxy = None
    if account.proxy_ip:
        proxy = (socks.SOCKS5, account.proxy_ip, account.proxy_port, True, account.proxy_user, account.proxy_pass)
        
    client = TelegramClient(session_path, api_id, api_hash, proxy=proxy)
    try:
        await client.connect()
        if await client.is_user_authorized():
            active_clients[account.phone] = client
            print(f"✅ Loaded client for {account.phone}")
            return client
        else:
            print(f"❌ Client {account.phone} is not authorized.")
            return None
    except Exception as e:
        print(f"❌ Failed to load client {account.phone}: {e}")
        return None

import datetime
import time

async def automation_job(api_id, api_hash):
    global automation_running
    # Note: automation_running set to True by caller
    print("🚀 Automation Engine Task Started...")
    
    # Track group-specific cooldowns: group_id -> timestamp until next allow
    group_cooldowns = {} 

    while automation_running:
        print("🕒 Starting Task Loop...")
        db: Session = SessionLocal()
        try:
            # Get latest config
            config = db.query(Config).first()
            if not config:
                config = Config()
                db.add(config)
                db.commit()
                db.refresh(config)
            
            # Get all groups with active assignments (Distinct to avoid duplicate processing)
            active_groups = db.query(Group).join(AccountGroupAssignment).distinct().all()
            if not active_groups:
                print("⚠️ No active group assignments found. Halting for 60 seconds.")
                await asyncio.sleep(60)
                continue
                
            for group in active_groups:
                if not automation_running: break

                # 0. Check if group is active (per-group toggle)
                if not group.is_active:
                    print(f"⏸️ Group {group.name} is paused.")
                    continue

                # 1. Check Operating Hours
                now = datetime.datetime.now()
                if not (group.start_hour <= now.hour < group.end_hour):
                    print(f"💤 Group {group.name} is outside operating hours ({group.start_hour}-{group.end_hour}). Current hour: {now.hour}")
                    continue

                # 2. Check Daily Message Limits & Reset Logic
                today_str = now.strftime("%Y-%m-%d")
                if group.last_reset_date != today_str:
                    group.messages_sent_today = 0
                    group.last_reset_date = today_str
                    db.commit()
                
                if group.messages_sent_today >= group.max_messages_per_day:
                    print(f"🛑 Group {group.name} reached daily limit ({group.max_messages_per_day}).")
                    continue

                # 3. Check Group Cooldown
                if group.id in group_cooldowns and time.time() < group_cooldowns[group.id]:
                    remaining = int(group_cooldowns[group.id] - time.time())
                    # Only print once every minute or if remaining is small to avoid spam
                    if remaining % 60 == 0 or remaining < 30:
                        print(f"⏳ Group {group.name} is on cooldown. Remaining: {remaining}s.")
                    continue

                # 4. Get Assignments for this group
                assignments = db.query(AccountGroupAssignment).filter_by(group_id=group.id).all()
                if not assignments: continue

                # 5. Process Batch
                batch_to_send = group.batch_size
                # Also don't exceed daily limit in this batch
                batch_to_send = min(batch_to_send, group.max_messages_per_day - group.messages_sent_today)
                
                print(f"📦 Processing Group: {group.name} | Batch Size: {batch_to_send}")

                sent_in_batch = 0
                max_attempts = batch_to_send * 4  # prevent infinite loop
                attempts = 0

                while sent_in_batch < batch_to_send and attempts < max_attempts:
                    attempts += 1
                    if not automation_running: break

                    # Pick account — prefer ones not in last_senders
                    last_sent = group_last_senders.get(group.id, [])
                    available = [a for a in assignments if a.account.id not in last_sent and a.account.status == "Active"]
                    if not available:
                        available = [a for a in assignments if a.account.status == "Active"]
                    if not available:
                        break

                    assignment = random.choice(available)
                    account = assignment.account

                    # Load client
                    client = await load_client(account, api_id, api_hash)
                    if not client: continue

                    target_group = group.username if group.username else group.name
                    if not target_group.startswith('@') and not target_group.startswith('https') and not target_group.lstrip('-').isdigit():
                        entry_target = f"@{target_group}"
                    else:
                        entry_target = target_group
                    
                    # ── Fetch History & Decide Reply Logic ──
                    history_text = ""
                    reply_to_id = None
                    last_msg_text = ""
                    
                    try:
                        msgs = await client.get_messages(entry_target, limit=10)
                        if msgs:
                            history_lines = []
                            for m in reversed(msgs):
                                sender_name = "Member"
                                if m.sender:
                                    if getattr(m.sender, 'username', None):
                                        sender_name = f"@{m.sender.username}"
                                    else:
                                        sender_name = getattr(m.sender, 'first_name', 'Member') or 'Member'
                                history_lines.append(f"{sender_name}: {m.text}")
                            history_text = "\n".join(history_lines)
                            
                            last_m = msgs[0]
                            me = await client.get_me()
                            if last_m.sender_id != me.id and random.random() < 0.7:
                                reply_to_id = last_m.id
                                last_msg_text = last_m.text
                    except Exception as e:
                        print(f"⚠️ History fetch error for {target_group}: {e}")

                    # Generate Message — use current rotating topic
                    current_topic = get_current_topic(group.content, group.id)
                    print(f"🤖 Generating message for {target_group} via {config.active_provider} | Topic: {current_topic[:60]}...")
                    ptype = "chat" if reply_to_id else "start"
                    full_msg = await get_ai_reply(db, current_topic, ptype, user_msg=last_msg_text, history=history_text, sent_today=group.messages_sent_today)
                    
                    messages_to_send = [m.strip() for m in full_msg.split("|||") if m.strip()]
                    
                    try:
                        async with client.action(entry_target, 'typing'):
                            for i, msg_part in enumerate(messages_to_send):
                                await asyncio.sleep(random.randint(2, 4)) 
                                current_reply_id = reply_to_id if i == 0 else None
                                await client.send_message(entry_target, msg_part, reply_to=current_reply_id)
                                
                                if i < len(messages_to_send) - 1:
                                    await asyncio.sleep(random.uniform(1.5, 3.0))

                        # Success! Increment counters
                        group.messages_sent_today += 1
                        sent_in_batch += 1
                        db.commit()
                        print(f"📩 Sent by {account.phone} -> {target_group} ({group.messages_sent_today}/{group.max_messages_per_day})")

                    except Exception as e:
                        print(f"❌ Error sending message by {account.phone}: {e}")

                    # Individual message delay
                    group_last_senders[group.id] = [account.id]
                    delay_sec = random.randint(group.min_delay, group.max_delay)
                    print(f"💤 Sleeping for {delay_sec}s before next batch item in {target_group}...")
                    await asyncio.sleep(delay_sec)
                
                # 6. Advance to next topic after batch
                advance_topic(group.id, group.content)

                # 7. Set Cooldown for this group after batch
                cooldown_sec = group.cooldown_minutes * 60
                group_cooldowns[group.id] = time.time() + cooldown_sec
                print(f"🛌 Group {group.name} batch finished. Cooldown started for {group.cooldown_minutes}m.")

        except Exception as e:
            print(f"❌ Automation crash loop: {e}")
            traceback.print_exc()
        finally:
            db.close()
            
        if automation_running:
            # Small break before next group/loop check
            await asyncio.sleep(30)
            
    print("🛑 Automation Engine Stopped.")
            
    print("🛑 Automation Engine Stopped.")

async def start_automation_engine(api_id, api_hash):
    global automation_running
    if not automation_running:
        automation_running = True
        asyncio.create_task(automation_job(api_id, api_hash))
        return True
    return False

def stop_automation_engine():
    global automation_running
    automation_running = False
    return True

async def join_group(account: Account, group: Group, api_id, api_hash):
    """Makes a specific Telegram client join a target group."""
    client = await load_client(account, api_id, api_hash)
    if not client:
        return {"status": "ERROR", "message": "Client not authorized or unreachable"}
        
    raw_target = (group.username if group.username else group.name).strip()
    print(f"🔗 Attempting to join: {raw_target} using {account.phone}")
    
    try:
        # Standardize target (remove https://, t.me/, etc.)
        target = raw_target
        if target.startswith("https://"):
            target = target.replace("https://", "")
        if target.startswith("http://"):
            target = target.replace("http://", "")
        if target.startswith("t.me/"):
            target = target.replace("t.me/", "")
            
        # Handle cases like @username or username
        is_invite = "/joinchat/" in raw_target or "+" in raw_target
        
        if is_invite:
            # Extract hash from link (handle both +XXXX and /joinchat/XXXX)
            hash_str = raw_target.split('/')[-1].replace('+', '').replace('joinchat', '')
            await client(ImportChatInviteRequest(hash_str))
        else:
            # Standard public username join
            # Clean it to be just the username if it was t.me/username
            if "/" in target:
                target = target.split("/")[0]
            
            # Ensure it has @ if it's not a numeric ID
            if not target.startswith('@') and not target.lstrip('-').isdigit():
                target = f"@{target}"
            
            # Use JoinChannelRequest with the cleaned target
            await client(JoinChannelRequest(target))
            
        print(f"✅ {account.phone} successfully joined {raw_target}")
        return {"status": "SUCCESS", "message": f"Successfully joined {raw_target}"}
    except Exception as e:
        err_msg = str(e)
        print(f"❌ {account.phone} failed to join {raw_target}: {err_msg}")
        return {"status": "ERROR", "message": f"Join failed: {err_msg}"}