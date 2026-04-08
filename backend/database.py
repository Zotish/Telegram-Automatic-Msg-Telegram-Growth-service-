from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True)
    phone = Column(String, unique=True)
    proxy_ip = Column(String)
    proxy_port = Column(Integer)
    proxy_user = Column(String)
    proxy_pass = Column(String)
    status = Column(String, default="Active")  # Active, Banned
    assignments = relationship("AccountGroupAssignment", back_populates="account", cascade="all, delete")

class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True)
    name = Column(String)           # Display name (e.g. "Alpha Network")
    username = Column(String, unique=True)  # Telegram group username (e.g. "alphanetwork")
    content = Column(Text, default="")     # AI context/information for this group
    
    # Advanced Controls
    max_messages_per_day = Column(Integer, default=50)
    messages_sent_today = Column(Integer, default=0)
    last_reset_date = Column(String, default="") # Format: YYYY-MM-DD
    start_hour = Column(Integer, default=9)  # 0-23
    end_hour = Column(Integer, default=21)   # 0-23
    cooldown_minutes = Column(Integer, default=30)
    batch_size = Column(Integer, default=5)
    min_delay = Column(Integer, default=40)
    max_delay = Column(Integer, default=80)
    is_active = Column(Boolean, default=True)  # Per-group on/off toggle

    assignments = relationship("AccountGroupAssignment", back_populates="group", cascade="all, delete")

class AccountGroupAssignment(Base):
    __tablename__ = "assignments"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    group_id = Column(Integer, ForeignKey("groups.id"))
    account = relationship("Account", back_populates="assignments")
    group = relationship("Group", back_populates="assignments")

class Config(Base):
    __tablename__ = "config"
    id = Column(Integer, primary_key=True)
    active_provider = Column(String, default="gemini") # gemini, openai
    gemini_api_key = Column(String)
    openai_api_key = Column(String)
    # Global delays
    min_delay = Column(Integer, default=40)
    max_delay = Column(Integer, default=80)

engine = create_engine("sqlite:///./automation.db")
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)