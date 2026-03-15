from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Depends, File, UploadFile, Form, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import re
from datetime import datetime, timedelta
import random
import string
import logging
import json
import os
import hashlib
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio
import base64
import httpx
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, ForeignKey, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship, backref
import chromadb
from sentence_transformers import SentenceTransformer

# LangChain & RAG 관련 임포트
from langchain_community.llms import Ollama
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 데이터베이스 설정
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://sguard_user:sguard_password@localhost:5433/sguard_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# RAG 환경설정 (Ollama & ChromaDB 연결)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
CHROMA_BASE_URL = os.getenv("CHROMA_BASE_URL", "http://localhost:8001")

# 1. 임베딩 모델 (nomic-embed-text)
embeddings = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url=OLLAMA_BASE_URL
)

# 2. Vector DB (Chroma) 연결
import chromadb
# chromadb 컨테이너에 HttpClient로 접속. 포트가 URL 형태라면 분리 필요
chroma_host = CHROMA_BASE_URL.replace("http://", "").split(":")[0]
chroma_port = CHROMA_BASE_URL.split(":")[-1]

chroma_client = chromadb.HttpClient(host=chroma_host, port=chroma_port)

vector_store = Chroma(
    client=chroma_client,
    collection_name="s_guard_knowledge",
    embedding_function=embeddings
)

# 3. LLM 엔진 (Llama 3)
llm = Ollama(
    model="llama3",
    base_url=OLLAMA_BASE_URL,
    temperature=0.1 # 정확한 답변을 위해 낮은 temperature 설정
)

# 4. Retrieval QA Chain 셋업 
# 실제 RAG 연동시 이 chain을 통해 LLM에 질의를 던짐
qa_prompt_template = PromptTemplate(
    template="[S-Guard 시스템 컨텍스트]\n{context}\n\n질문: {question}\n\n위 컨텍스트를 기반으로 간결하고 정확하게 시스템 운영 관점에서 답변해줘.",
    input_variables=["context", "question"]
)

qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vector_store.as_retriever(search_kwargs={"k": 3}),
    chain_type_kwargs={"prompt": qa_prompt_template}
)

# DB 모델 정의
# RAG 설정 (ChromaDB + Ollama)
try:
    chroma_client = chromadb.HttpClient(host="sguard-chroma", port=8000)
    chroma_collection = chroma_client.get_collection(name="sguard_postmortems")
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    logger.info("ChromaDB & Embedding Model initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize ChromaDB or Embedding Model: {e}")
    chroma_collection = None
    embedding_model = None

OLLAMA_URL = "http://sguard-ollama:11434/api/generate"

class SMSMessageDB(Base):
    __tablename__ = "received_messages"
    id = Column(Integer, primary_key=True, index=True)
    sender = Column(String(20), index=True)
    message = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    keyword_detected = Column(Boolean, default=False)
    response_message = Column(Text, nullable=True)
    read = Column(Boolean, default=False)

class SMSHistoryDB(Base):
    __tablename__ = "sms_history"
    id = Column(Integer, primary_key=True, index=True)
    recipient = Column(String(20))
    message = Column(Text)
    sent_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20))

class KeywordDB(Base):
    __tablename__ = "alert_keywords"
    keyword = Column(String(50), primary_key=True)
    response = Column(Text)
    severity = Column(String(20), default="NORMAL")
    hit_count = Column(Integer, default=0)

class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    password_hash = Column(String(256), nullable=True)  # nullable for Google OAuth users
    role = Column(String(50), default="analyst")  # admin, analyst, viewer
    auth_provider = Column(String(30), default="local")  # local, google
    company = Column(String(100), nullable=True)   # 회사소속
    employee_id = Column(String(50), nullable=True)  # 사번
    phone = Column(String(20), nullable=True)        # 핸드폰번호
    honbu = Column(String(100), nullable=True)        # 본부
    team = Column(String(100), nullable=True)         # 팀
    part = Column(String(100), nullable=True)         # 파트
    token = Column(String(256), nullable=True)        # 세션 토큰
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class OrganizationDB(Base):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), unique=True, index=True, nullable=True)
    parent_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    depth = Column(Integer, default=1)  # 1: Company, 2: Honbu, 3: Team, 4: Part
    sort_order = Column(Integer, default=0)

    children = relationship("OrganizationDB", backref=backref('parent', remote_side=[id]), cascade="all, delete-orphan")

class IncidentDB(Base):
    __tablename__ = "incidents"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(30), unique=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(20), default="NORMAL")  # CRITICAL, MAJOR, NORMAL
    status = Column(String(30), default="Open")  # Open, In Progress, Completed
    incident_type = Column(String(20), default="AI")  # AI, SMS
    assigned_to = Column(String(100), nullable=True)
    source_sms_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ActivityLogDB(Base):
    __tablename__ = "activity_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    user_name = Column(String(100), default="System")
    incident_code = Column(String(30), nullable=True)
    incident_title = Column(String(255), nullable=True)
    action = Column(String(100), nullable=False)  # e.g. 'AI 리포트 보고 완료'
    detail = Column(Text, nullable=True)
    team = Column(String(100), nullable=True)
    report_type = Column(String(50), default="AI 리포트")
    created_at = Column(DateTime, default=datetime.utcnow)

class WarRoomChatDB(Base):
    __tablename__ = "warroom_chats"
    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(String(50), index=True)
    sender = Column(String(50))
    role = Column(String(50), nullable=True)
    type = Column(String(20), default='user') # 'user', 'ai', 'system'
    text = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

class WarRoomAttachmentDB(Base):
    __tablename__ = "warroom_attachments"
    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(String(50), index=True)
    filename = Column(String(255))          # stored filename
    original_name = Column(String(255))     # user-facing name
    file_type = Column(String(50))          # image/jpeg, application/pdf, etc.
    url = Column(String(500))               # /static/uploads/{filename}
    uploaded_by = Column(String(100), default="Unknown")
    timestamp = Column(DateTime, default=datetime.utcnow)

class ResetVerificationDB(Base):
    __tablename__ = "reset_verifications"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), index=True)
    code = Column(String(10))
    created_at = Column(DateTime, default=datetime.utcnow)
    is_verified = Column(Boolean, default=False)

# 테이블 생성 및 연결 대기
import time
def init_db_with_retry():
    retries = 5
    while retries > 0:
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database initialized successfully")
            break
        except Exception as e:
            logger.error(f"Database connection failed, retrying... ({retries} left): {e}")
            retries -= 1
            time.sleep(5)
    else:
        logger.error("Failed to connect to database after multiple attempts")

init_db_with_retry()

# DB 세션 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# WebSocket 연결 관리자
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket 연결됨. 총 연결: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket 연결 해제. 총 연결: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"메시지 전송 실패: {e}")

manager = ConnectionManager()

app = FastAPI(title="S-Guard AI SMS Service")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic 모델
class SMSMessage(BaseModel):
    sender: str
    message: str
    received_at: Optional[str] = None

class IncidentCreate(BaseModel):
    code: str
    title: str
    description: Optional[str] = None
    severity: str = "NORMAL"
    incident_type: str = "AI"
    source_sms_id: Optional[int] = None

def check_keywords(db: Session, message: str) -> Optional[str]:
    keywords = db.query(KeywordDB).all()
    for kw in keywords:
        if kw.keyword in message:
            logger.info(f"키워드 감지: {kw.keyword}")
            return kw.response
    return None

async def send_sms(db: Session, recipient: str, message: str):
    logger.info(f"SMS 전송: {recipient} - {message}")
    sms_data = SMSHistoryDB(
        recipient=recipient,
        message=message,
        sent_at=datetime.utcnow(),
        status="sent"
    )
    db.add(sms_data)
    db.commit()
    return sms_data

@app.get("/")
async def root():
    return {"service": "S-Guard AI SMS Service", "status": "running", "version": "1.1.0 (DB Linked)"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/sms/receive")
async def receive_sms(sms: SMSMessage, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    logger.info(f"SMS 수신: {sms.sender} - {sms.message}")
    response_message = check_keywords(db, sms.message)
    
    # Use internal timestamp if provided, else fallback to server time
    ts = datetime.utcnow()
    if sms.received_at:
        try:
            # Handle ISO format like "2024-03-21T15:30:00" or simple "2024-03-21 15:30:00"
            ts = datetime.fromisoformat(sms.received_at.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            logger.warning(f"Invalid timestamp format: {sms.received_at}. Falling back to server time.")
    
    msg_db = SMSMessageDB(
        sender=sms.sender,
        message=sms.message,
        timestamp=ts,
        keyword_detected=response_message is not None,
        response_message=response_message
    )
    db.add(msg_db)
    db.commit()
    db.refresh(msg_db)
    
    notification = {
        "type": "sms_received",
        "sender": sms.sender,
        "message": sms.message,
        "timestamp": msg_db.timestamp.isoformat(),
        "keyword_detected": msg_db.keyword_detected,
        "response_message": response_message
    }
    await manager.broadcast(notification)
    
    if response_message:
        # 백업 태스크에서도 새 세션을 사용하거나 세션 관리에 주의해야 합니다. 
        # 간단하게 구현하기 위해 동기 함수로 직접 호출하거나 별도 로직 권장
        await send_sms(db, sms.sender, response_message)
        
        return {
            "status": "keyword_detected",
            "sender": sms.sender,
            "response_sent": True,
            "response_message": response_message
        }
    
    return {"status": "received", "sender": sms.sender, "response_sent": False}

@app.get("/sms/recent")
async def get_recent_messages(limit: int = 10, db: Session = Depends(get_db)):
    messages = db.query(SMSMessageDB).order_by(SMSMessageDB.timestamp.desc()).limit(limit).all()
    return {"total": len(messages), "messages": messages}

@app.delete("/sms/{message_id}")
async def delete_sms(message_id: int, db: Session = Depends(get_db)):
    msg = db.query(SMSMessageDB).filter(SMSMessageDB.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    db.delete(msg)
    db.commit()
    return {"status": "success", "message": "Deleted successfully"}

@app.get("/sms/history")
async def get_sms_history(db: Session = Depends(get_db)):
    history = db.query(SMSHistoryDB).all()
    return {"total": len(history), "history": history}

@app.get("/sms/keywords")
async def get_keywords(db: Session = Depends(get_db)):
    keywords = db.query(KeywordDB).all()
    return {"keywords": keywords}

@app.post("/sms/keywords")
async def add_keyword(keyword: str, response: str, db: Session = Depends(get_db)):
    kw = KeywordDB(keyword=keyword, response=response)
    db.merge(kw) # 존재하면 업데이트, 없으면 추가
    db.commit()
    return {"status": "success", "keyword": keyword}

@app.on_event("startup")
def startup_populate_keywords():
    # 초기 키워드 데이터 시딩
    db = SessionLocal()
    default_keywords = {
        "장애": "장애 알림이 감지되었습니다. S-Guard AI 시스템에 자동 등록되었습니다.",
        "CRITICAL": "긴급 장애가 감지되었습니다. 즉시 War-Room을 통해 확인해주세요.",
        "오류": "시스템 오류가 감지되었습니다. AI 분석을 시작합니다.",
        "DOWN": "서비스 다운이 감지되었습니다. 긴급 대응팀에 알림을 전송했습니다.",
        "비정상": "비정상 상태가 감지되었습니다. 자동 분석 중입니다.",
    }
    for k, v in default_keywords.items():
        if not db.query(KeywordDB).filter_by(keyword=k).first():
            db.add(KeywordDB(keyword=k, response=v))
    db.commit()
    db.close()

# --- AI API Endpoints (Phase 2) ---

# 최적화를 위한 글로벌 캐시 (Autopilot 패널의 잦은 Polling으로 인한 LLM 부하 방지)
last_analyzed_sms_id = None
cached_insight_response = None

@app.get("/ai/insight")
async def get_ai_insight(db: Session = Depends(get_db)):
    """
    대시보드 상단 AI Insight (Autopilot) 패널용 데이터
    수신된 가장 최근 SMS 내용을 바탕으로 ChromaDB에서 과거 장애 패턴을 찾고, Ollama LLM을 통해 실시간 분석 및 대응 가이드 제공.
    """
    global last_analyzed_sms_id, cached_insight_response
    
    # 1. 최근 SMS 내역 조회
    recent_sms = db.query(SMSMessageDB).order_by(SMSMessageDB.timestamp.desc()).first()
    
    # 대시보드 UI 요약 지표용 데이터 (최근 100건)
    recent_messages = db.query(SMSMessageDB).order_by(SMSMessageDB.timestamp.desc()).limit(100).all()
    prediction_counts = {
        "critical": 0,
        "server": 0,
        "security": 0,
        "report": 0
    }
    
    for msg in recent_messages:
        msg_text_lower = msg.message.lower()
        if "db" in msg_text_lower or "데이터베이스" in msg_text_lower:
            prediction_counts["critical"] += 1
        elif "cpu" in msg_text_lower or "메모리" in msg_text_lower:
            prediction_counts["server"] += 1
        else:
            prediction_counts["report"] += 1

    # 수신된 메시지가 아예 없을 경우 예외 처리
    if not recent_sms:
        return {
            "status": "active",
            "learning_data_size": "15.2 TB (KMS)",
            "accuracy": "98.5%",
            "prediction_counts": prediction_counts,
            "current_log": {
                "id": "SYS-000",
                "type": "info",
                "category": "report",
                "severity": "info",
                "text": "실시간 데이터 대기 중... 새로운 장애 SMS를 기다리고 있습니다.",
                "detail": "신한DS KMS 연동 RAG 분석 대기 중"
            }
        }

    # 2. 성능 최적화: 이전에 캐싱된 SMS 결과인지 체크
    if last_analyzed_sms_id == recent_sms.id and cached_insight_response:
        # prediction_counts 값만 최신화해서 캐시 응답
        cached_insight_response["prediction_counts"] = prediction_counts
        return cached_insight_response

    # 3. 새로운 SMS가 수신되었다면 RAG 기반 AI 모델 구동
    text = recent_sms.message
    
    # 3-1. Retrieval (ChromaDB 참조 데이터 수집)
    rag_context = ""
    if chroma_collection and embedding_model:
        try:
            query_embedding = embedding_model.encode([text])
            results = chroma_collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=2 # 핵심 참조 문헌 2건만
            )
            if results['documents'] and len(results['documents'][0]) > 0:
                rag_context = "과거 발생한 유사 사후보고서 단서:\\n"
                for doc in results['documents'][0]:
                    rag_context += f"- {doc[:200]}...\\n"
        except Exception as e:
            logger.error(f"ChromaDB search failed in Autopilot: {e}")

    # 3-2. Generation (Ollama LLM)
    system_prompt = (
        "당신은 S-Guard 시스템 자동 분석 오토파일럿(S-Autopilot)입니다. "
        "사용자가 수신한 에러/장애 SMS 텍스트와, 이와 유사했던 과거 장애 사례 문헌을 분석하여 "
        "현재 발생한 장애의 추정 원인 및 즉각적인 조치 가이드라인을 '1~2문장'으로 매우 짧고 명확하게 한국어로 제시하세요. "
        "결과는 반드시 '💡 [Insight] ' 또는 '🚨 [Critical] ' 등의 아이콘 접두어로 시작해야 합니다. 불필요한 인사말은 생략하세요."
    )
    
    combined_prompt = f"수신된 SMS 에러: {text}\\n\\n과거 관련 사례 문헌:\\n{rag_context}\\n\\n위의 정보를 참고하여 원인과 결론을 요약해주세요."
    
    insight_text = "AI 엔진 분석 중..."
    severity = "info"
    type_str = "insight"
    category = "report"

    try:
        logger.info(f"Autopilot LLM 처리 중... SMS ID: {recent_sms.id}")
        payload = {
            "model": "llama3",
            "prompt": combined_prompt,
            "system": system_prompt,
            "stream": False
        }
        # 분석이 느려질 수 있으므로 timeout 여유있게 부여 (대시보드는 한 번만 기다리면 됨)
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(OLLAMA_URL, json=payload)
            response.raise_for_status()
            llm_result = response.json()
            insight_text = llm_result.get("response", "LLM 응답 불가")
            
            # 텍스트 결과에서 심각도 간단 추정
            if "Critical" in insight_text or "🚨" in insight_text:
                severity = "critical"
                type_str = "error"
                category = "database"
            elif "Warning" in insight_text or "⚠️" in insight_text:
                severity = "high"
                type_str = "warning"
                category = "server"
                
    except Exception as e:
        logger.error(f"Ollama failed in Autopilot insight: {e}")
        insight_text = f"💡 [Insight] RAG 모델 연동 중 LLM 추론 타임아웃 발생 (수신 SMS: {text[:20]}...). 서버 재기동을 고려하세요."

    current_log = {
        "id": f"RAG-AUTO-{recent_sms.id}",
        "type": type_str,
        "category": category,
        "severity": severity,
        "text": insight_text,
        "detail": f"수신 시간: {recent_sms.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
    }

    final_response = {
        "status": "active",
        "learning_data_size": "15.2 TB (KMS) + Local RAG",
        "accuracy": "99.1%",
        "prediction_counts": prediction_counts,
        "current_log": current_log
    }

    # 4. 분석 결과 메모리 캐싱 (중복 추론 방지)
    last_analyzed_sms_id = recent_sms.id
    cached_insight_response = final_response

    return final_response

@app.get("/ai/agent-discussion/{sms_id}")
async def get_agent_discussion(sms_id: int, db: Session = Depends(get_db)):
    """
    특정 SMS ID 기반 다중 에이전트 논의 대본 생성 API (Live Incident Stream 연동용)
    RAG(ChromaDB)를 통해 과거 사례를 찾고, Ollama LLM을 이용해 4명의 전문가 캐릭터들이 회의하는 JSON 대본을 생성.
    """
    sms = db.query(SMSMessageDB).filter(SMSMessageDB.id == sms_id).first()
    if not sms:
        raise HTTPException(status_code=404, detail="해당 SMS를 찾을 수 없습니다.")

    text = sms.message
    
    # 1. Retrieval (ChromaDB 참조 데이터 수집)
    rag_context = ""
    if chroma_collection and embedding_model:
        try:
            query_embedding = embedding_model.encode([text])
            results = chroma_collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=2 # 핵심 참조 문헌 2건만
            )
            if results['documents'] and len(results['documents'][0]) > 0:
                rag_context = "과거 발생한 유사 장애 및 해결 사례 (사후보고서):\\n"
                for doc in results['documents'][0]:
                    rag_context += f"- {doc[:200]}...\\n"
        except Exception as e:
            logger.error(f"ChromaDB search failed in Discussion API: {e}")

    # 2. 시스템 프롬프트 및 JSON 강제 생성 규칙 작성
    system_prompt = """
당신은 IT 장애 대응팀의 4명의 에이전트(Security, DB, DevOps, Leader)의 회의 대본을 작성하는 AI 봇입니다.
사용자가 제공하는 [현재 수신된 통신 장애 로그]와 [과거 유사 장애 및 해결 사례]를 바탕으로, 각자의 역할에 맞춘 짧은 대사(1~2문장)를 생성하세요.
반드시 아래 JSON Array 형식만 응답해야 하며, 다른 인삿말이나 부연 설명은 일절 포함하지 마세요.

역할(role) 정보:
- "Security": 침입이나 보안 위협 관점 점검
- "DB": 데이터베이스 상태 및 트랜잭션, 커넥션 풀 등의 관점 점검
- "DevOps": 서버 리소스, 인프라, 네트워크 지연 관점 제안
- "Leader": 상황을 종합하고 조치 방안(Actions) 결론 도출 (반드시 마지막에 발언)

응답 예시 포맷:
[
  {"role": "DevOps", "text": "현재 시스템의 ... 로그가 감지되었습니다. 이전 사례를 비추어볼 때 트래픽 폭주가 예상됩니다."},
  {"role": "DB", "text": "... 정보를 확인했습니다. DB 커넥션이 포화 상태입니다."},
  {"role": "Security", "text": "외부의 악성 접근은 발견되지 않았습니다."},
  {"role": "Leader", "text": "과거 사례를 참고하여 즉각적인 캐시 스케일 아웃 및 DB 재기동을 승인합니다."}
]
"""
    
    combined_prompt = f"현재 수신된 통신 장애 로그:\n{text}\n\n과거 유사 장애 및 해결 사례:\n{rag_context}\n\n역할별로 나누어 JSON 대본을 작성해주세요."
    
    try:
        logger.info(f"Agent-Discussion LLM 처리 중... SMS ID: {sms_id}")
        payload = {
            "model": "llama3",
            "prompt": combined_prompt,
            "system": system_prompt,
            "stream": False,
            "format": "json" # JSON 응답 강제 (지원되는 모델의 경우)
        }
        
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(OLLAMA_URL, json=payload)
            response.raise_for_status()
            llm_result = response.json()
            raw_text = llm_result.get("response", "[]")
            
            # JSON 파싱 시도
            import json
            try:
                # 가끔 모델이 markdown 블록으로 감싸는 경우 처리
                if raw_text.startswith("```json"):
                    raw_text = raw_text.split("```json")[1].split("```")[0].strip()
                elif raw_text.startswith("```"):
                    raw_text = raw_text.split("```")[1].split("```")[0].strip()
                    
                discussion_data = json.loads(raw_text)
                
                # 모델이 {"response": [...]} 또는 {"discussion": [...]} 형태로 응답하는 경우 처리
                if isinstance(discussion_data, dict):
                    if "response" in discussion_data and isinstance(discussion_data["response"], list):
                        discussion_data = discussion_data["response"]
                    elif "discussion" in discussion_data and isinstance(discussion_data["discussion"], list):
                        discussion_data = discussion_data["discussion"]
                        
                if not isinstance(discussion_data, list):
                    raise ValueError("Parsed JSON is not a list")
                    
                return {"status": "success", "discussion": discussion_data}
            except Exception as e:
                logger.warning(f"Failed to parse LLM JSON output: {e}. Raw text: {raw_text}")
                # 파싱 실패시 폴백 데이터 생성
                fallback_data = [
                    {"role": "DevOps", "text": f"수신된 로그 '{text[:20]}...' 분석 중입니다. 인프라 지표를 점검하겠습니다."},
                    {"role": "DB", "text": "데이터베이스 부하는 정상 범위로 보이나 과거 사례 기반으로 재확인 중입니다."},
                    {"role": "Security", "text": "관련 IP 대역에 대한 차단 룰을 임시로 활성화 하길 권장합니다."},
                    {"role": "Leader", "text": "우선 모니터링을 지속하며, 관련자 승인을 대기합니다."}
                ]
                return {"status": "fallback", "discussion": fallback_data}

    except Exception as e:
        logger.error(f"Ollama failed in Agent Discussion API: {e}")
        # LLM 자체 에러시 에러 메시 대사로 구성
        error_data = [
            {"role": "DevOps", "text": "LLM 추론 엔진과의 통신 시간 초과 (Timeout)가 발생했습니다."},
            {"role": "Leader", "text": "일단 과거 발생한 사례를 기반으로 기존 프로토콜 매뉴얼에 따라 수동 조치를 진행해 주시기 바랍니다."}
        ]
        return {"status": "error", "discussion": error_data}

@app.get("/ai/analysis/{incident_id}")
async def get_ai_analysis_detail(incident_id: str):
    """
    상세 페이지용 AI Root Cause Analysis 및 가이드
    RAG(Retrieval-Augmented Generation) 엔진 결과를 시뮬레이션
    """
    # 데모용: ID에 따라 다른 결과 반환 (홀/짝)
    # 실제로는 DB에서 해당 incident_id의 로그를 조회하고 LLM에 질의해야 함
    
    is_critical = "critical" in incident_id.lower() or "error" in incident_id.lower()
    
    if is_critical:
        return {
            "incident_id": incident_id,
            "similarity_score": 95,
            "similar_case": {
                "date": "3개월 전",
                "issue_id": "DB Lock Issue #402",
                "description": "대량 배치 작업으로 인한 세션 풀 고갈"
            },
            "root_cause": "Connection Pool Limit Exceeded (Max: 500)",
            "impact": "결제 API 응답 지연 (Avg 2.5s)",
            "recommendation": {
                "action": "KILL SESSION",
                "description": "Long Running Query 강제 종료",
                "type": "script"
            }
        }
    else:
        return {
            "incident_id": incident_id,
            "similarity_score": 88,
            "similar_case": {
                "date": "2주 전",
                "issue_id": "Memory Leak #105",
                "description": "이미지 처리 서비스 메모리 누수"
            },
            "root_cause": "Java Heap Space OutOfMemory",
            "impact": "이미지 업로드 실패",
            "recommendation": {
                "action": "RESTART SERVICE",
                "description": "이미지 처리 컨테이너 재기동",
                "type": "command"
            }
        }

class ChatRequest(BaseModel):
    query: str

@app.post("/ai/chat")
async def chat_with_ai(request: ChatRequest):
    """
    AI Agent Chatbot Endpoint (Fully Integrated with RAG)
    """
    query = request.query
    
    # 기본 더미 체크 (이전 Mock 호환 명목)
    if not query.strip():
        return {"response": "질문을 입력해주세요.", "related_logs": []}

    related_logs = []
    rag_context = ""

    # 1. Retrieval (ChromaDB 검색)
    if chroma_collection and embedding_model:
        try:
            logger.info(f"Querying ChromaDB for: {query}")
            query_embedding = embedding_model.encode([query])
            results = chroma_collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=3
            )
            
            if results['documents'] and len(results['documents'][0]) > 0:
                rag_context = "다음은 S-Guard에 등록된 과거 장애 처리 내역(Post-Mortem)입니다:\\n"
                for i, doc in enumerate(results['documents'][0]):
                    source = results['metadatas'][0][i].get('source', 'Unknown')
                    excerpt = doc[:400] + "..." if len(doc) > 400 else doc
                    rag_context += f"- [출처: {source}] {excerpt}\\n"
                    related_logs.append(f"[RAG] 매칭 출처: {source} (유사도: {results['distances'][0][i]:.4f})")
        except Exception as e:
            logger.error(f"ChromaDB search failed: {e}")
            related_logs.append(f"[System Error] Vector DB 연동 중 오류 발생: {e}")

    # 2. Generation (Ollama LLM 활용)
    # 프롬프트 구성
    system_prompt = (
        "당신은 S-Guard IT 시스템 장애 분석 전문가 및 챗봇입니다. "
        "사용자가 시스템 오류나 장애에 대해 질문하면, 가용한 정보와 과거 유사 장애 사례를 바탕으로 원인을 분석하고 해결책을 친절하게 제시하세요. "
        "응답은 반드시 한국어로 작성해야 합니다."
    )
    
    combined_prompt = f"질문: {query}\\n\\n"
    if rag_context:
        combined_prompt += f"과거 관련 장애 사례:\\n{rag_context}\\n\\n위의 과거 사례를 참고하여 질문에 상세히 답변해주세요."
    else:
        combined_prompt += "질문에 답변해주세요."

    payload = {
        "model": "llama3", # 사용 중인 모델명 (만약 phi3 사용시 변경)
        "prompt": combined_prompt,
        "system": system_prompt,
        "stream": False
    }

    try:
        logger.info("Sending prompt to Ollama LLM...")
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(OLLAMA_URL, json=payload)
            response.raise_for_status()
            llm_result = response.json()
            answer = llm_result.get("response", "LLM 응답을 해석할 수 없습니다.")
    except Exception as e:
        logger.error(f"OLLAMA HTTP Request Failed: {e}")
        answer = (
            "⚠️ LLM(Ollama) 서버와 통신할 수 없습니다. "
            "현재 모델(llama3)이 컨테이너에 탑재되어 실행 중인지, 메모리가 충분한지 확인해주세요.\\n"
            f"Error details: {e}"
        )
        if rag_context:
            answer += f"\\n\\n(참고로 AI 생성은 실패했으나, 다음 과거 유사 장애 문서를 찾았습니다.)\\n{rag_context[:500]}..."

    return {
        "response": answer,
        "related_logs": related_logs
    }

class ReportSaveRequest(BaseModel):
    title: str
    content: str
    sms_id: Optional[str] = None

class SmsAnalysisRequest(BaseModel):
    sender: str
    message: str

@app.post("/ai/analyze-sms")
async def analyze_sms(req: SmsAnalysisRequest):
    """Perform real-time RAG analysis on an incoming SMS"""
    query = f"다음 SMS 메시지를 분석하고 장애 유형과 대응 방안을 제시해줘: '{req.message}' (발신자: {req.sender})"
    try:
        # Use the existing RAG chain to find similar cases and analyze
        result = qa_chain.invoke(query)
        analysis_text = result.get('result', '')
        
        # If the result is too short or empty, provide a default but still structured response
        if not analysis_text or len(analysis_text) < 10:
            analysis_text = f"수신 메시지 '{req.message}'를 분석한 결과, 특이 장애 패턴이 발견되지 않았습니다. 지속적으로 모니터링이 필요합니다."
            
        return {"status": "success", "analysis": analysis_text}
    except Exception as e:
        logger.error(f"RAG 분석 중 오류 발생: {e}")
        # Fallback to a simpler prompt if the chain fails
        try:
            response = await httpx.AsyncClient(timeout=30.0).post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": "llama3",
                    "prompt": f"장애 관제 시스템 전문가로서 다음 SMS를 분석하고 대응 방안을 한국어로 한 문장으로 말해줘: {req.message}",
                    "stream": False
                }
            )
            if response.status_code == 200:
                data = response.json()
                return {"status": "success", "analysis": data.get('response', '')}
        except:
            pass
        return {"status": "error", "analysis": "AI 서비스를 일시적으로 사용할 수 없어 로컬 규칙으로 분석합니다."}

@app.post("/ai/report/save")
async def save_ai_report(req: ReportSaveRequest, db: Session = Depends(get_db)):
    logger.info(f"KMS 보고서 저장 요청: {req.title}")
    try:
        doc_id = f"report_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        document_text = f"Title: {req.title}\nContent: {req.content}"
        
        vector_store.add_texts(
            texts=[document_text],
            metadatas=[{
                "source": "auto_generated_report",
                "title": req.title,
                "timestamp": datetime.utcnow().isoformat(),
                "sms_id": req.sms_id or "unknown"
            }],
            ids=[doc_id]
        )
        
        # [활동로그] AI 리포트 저장 로그 추가
        log = ActivityLogDB(
            user_name="AI Autopilot",
            incident_code=req.sms_id, # Linking to SMS ID if provided
            incident_title=req.title,
            action="AI 리포트 보고 완료",
            detail=f"KMS 지식 베이스에 AI 분석 보고서({req.title})가 저장되었습니다.",
            report_type="AI 리포트"
        )
        db.add(log)
        db.commit()

        logger.info(f"ChromaDB [s_guard_knowledge] 컬렉션에 새 보고서 적재 성공. ID: {doc_id}")
        return {"status": "success", "message": "보고서가 성공적으로 KMS에 저장(임베딩)되었습니다.", "doc_id": doc_id}
    except Exception as e:
        logger.error(f"KMS 저장 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- War-Room Chat Endpoints ---

class WarRoomMessage(BaseModel):
    incident_id: str
    sender: str
    role: Optional[str] = "User"
    type: str = "user"
    text: str

@app.post("/warroom/chat")
async def save_warroom_chat(msg: WarRoomMessage, db: Session = Depends(get_db)):
    """Save a single message from the War-Room"""
    chat_db = WarRoomChatDB(
        incident_id=msg.incident_id,
        sender=msg.sender,
        role=msg.role,
        type=msg.type,
        text=msg.text,
        timestamp=datetime.utcnow()
    )
    db.add(chat_db)
    db.commit()
    db.refresh(chat_db)
    return {"status": "success", "id": chat_db.id}

@app.get("/warroom/chat/{incident_id}")
async def get_warroom_chat(incident_id: str, db: Session = Depends(get_db)):
    """Retrieve chat history for a specific incident with metadata"""
    chats = db.query(WarRoomChatDB).filter(WarRoomChatDB.incident_id == incident_id).order_by(WarRoomChatDB.timestamp.asc()).all()
    
    # Also fetch incident metadata for the title and description
    incident = db.query(IncidentDB).filter(IncidentDB.code == incident_id).first()
    title = incident.title if incident else f"Room {incident_id}"
    description = incident.description if incident else ""
    severity = incident.severity if incident else "NORMAL"
    
    return {
        "messages": chats,
        "title": title,
        "description": description,
        "severity": severity,
        "status": incident.status if incident else "Open"
    }

@app.post("/incidents")
async def create_incident(inc: IncidentCreate, db: Session = Depends(get_db)):
    """Create or update incident metadata"""
    # 1. Check if an incident for this specific SMS already exists
    if inc.source_sms_id:
        existing_sms_inc = db.query(IncidentDB).filter(IncidentDB.source_sms_id == inc.source_sms_id).first()
        if existing_sms_inc:
            return {
                "status": "exists", 
                "id": existing_sms_inc.id, 
                "code": existing_sms_inc.code,
                "title": existing_sms_inc.title
            }

    # 2. Check for exact code match (original behavior)
    existing = db.query(IncidentDB).filter(IncidentDB.code == inc.code).first()
    if existing:
        existing.title = inc.title
        existing.description = inc.description
        existing.severity = inc.severity
        db.commit()
        db.refresh(existing)
        return {"status": "updated", "id": existing.id, "code": existing.code}
    
    new_inc = IncidentDB(
        code=inc.code,
        title=inc.title,
        description=inc.description,
        severity=inc.severity,
        incident_type=inc.incident_type,
        source_sms_id=inc.source_sms_id
    )
    db.add(new_inc)
    
    # [활동로그] 새로운 워룸 개설 로그 추가
    log = ActivityLogDB(
        user_name="System",
        incident_code=new_inc.code,
        incident_title=new_inc.title,
        action="War-Room 개설",
        detail=f"새로운 War-Room ({new_inc.code})이 개설되었습니다.",
        report_type="시스템"
    )
    db.add(log)
    
    db.commit()
    db.refresh(new_inc)
    return {"status": "created", "id": new_inc.id, "code": new_inc.code}

# ─── War-Room Management Endpoints ──────────────────────────────────────────

UPLOAD_DIR = "/tmp/warroom_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/warroom/rooms")
async def list_warrooms(
    status: Optional[str] = None,
    q: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    assigned_to: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all War-Rooms with optional filters"""
    query = db.query(IncidentDB)
    
    if status:
        query = query.filter(IncidentDB.status == status)
    
    if q:
        query = query.filter(or_(
            IncidentDB.title.ilike(f"%{q}%"),
            IncidentDB.description.ilike(f"%{q}%"),
            IncidentDB.code.ilike(f"%{q}%")
        ))
        
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
            query = query.filter(IncidentDB.created_at >= start_dt)
        except: pass
        
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
            # To include the whole day if end_date doesn't have time
            if len(end_date) <= 10: 
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
            query = query.filter(IncidentDB.created_at <= end_dt)
        except: pass
        
    if assigned_to:
        query = query.filter(IncidentDB.assigned_to.ilike(f"%{assigned_to}%"))

    incidents = query.order_by(IncidentDB.created_at.desc()).all()
    
    result = []
    for inc in incidents:
        # Latest message
        latest = db.query(WarRoomChatDB)\
            .filter(WarRoomChatDB.incident_id == inc.code)\
            .order_by(WarRoomChatDB.timestamp.desc()).first()
        
        # Message count
        msg_count = db.query(WarRoomChatDB)\
            .filter(WarRoomChatDB.incident_id == inc.code)\
            .count()
        
        # Attachment count
        attach_count = db.query(WarRoomAttachmentDB)\
            .filter(WarRoomAttachmentDB.incident_id == inc.code)\
            .count()

        result.append({
            "code": inc.code,
            "title": inc.title,
            "description": inc.description,
            "severity": inc.severity,
            "status": inc.status,
            "incident_type": inc.incident_type,
            "assigned_to": inc.assigned_to,
            "created_at": inc.created_at.isoformat() if inc.created_at else None,
            "updated_at": inc.updated_at.isoformat() if inc.updated_at else None,
            "last_message": latest.text if latest else None,
            "last_message_time": latest.timestamp.isoformat() if latest else None,
            "last_message_sender": latest.sender if latest else None,
            "message_count": msg_count,
            "attachment_count": attach_count,
        })
    
    return {"total": len(result), "rooms": result}


@app.post("/warroom/reset")
async def reset_warroom_data(db: Session = Depends(get_db)):
    """Wipe all War-Room incidents, chats, and attachments for testing/cleanup"""
    try:
        # 1. Delete physical files
        if os.path.exists(UPLOAD_DIR):
            import shutil
            for filename in os.listdir(UPLOAD_DIR):
                file_path = os.path.join(UPLOAD_DIR, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    logger.error(f"Failed to delete {file_path}. Reason: {e}")

        # 2. Purge DB tables
        db.query(WarRoomChatDB).delete()
        db.query(WarRoomAttachmentDB).delete()
        db.query(IncidentDB).delete()
        
        # 3. Optional: Clear related Activity Logs if needed
        db.query(ActivityLogDB).filter(ActivityLogDB.incident_code != None).delete()
        
        db.commit()
        return {"status": "success", "message": "All War-Room data has been cleared."}
    except Exception as e:
        db.rollback()
        logger.error(f"Reset failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/warroom/rooms/search")
async def search_warrooms(
    q: str = Query(..., description="Search query"),
    db: Session = Depends(get_db)
):
    """Search War-Rooms by title or description"""
    incidents = db.query(IncidentDB).filter(
        or_(
            IncidentDB.title.ilike(f"%{q}%"),
            IncidentDB.description.ilike(f"%{q}%"),
            IncidentDB.code.ilike(f"%{q}%")
        )
    ).order_by(IncidentDB.created_at.desc()).all()
    
    result = []
    for inc in incidents:
        latest = db.query(WarRoomChatDB)\
            .filter(WarRoomChatDB.incident_id == inc.code)\
            .order_by(WarRoomChatDB.timestamp.desc()).first()
        msg_count = db.query(WarRoomChatDB).filter(WarRoomChatDB.incident_id == inc.code).count()
        result.append({
            "code": inc.code,
            "title": inc.title,
            "description": inc.description,
            "severity": inc.severity,
            "status": inc.status,
            "created_at": inc.created_at.isoformat() if inc.created_at else None,
            "last_message": latest.text if latest else None,
            "last_message_time": latest.timestamp.isoformat() if latest else None,
            "message_count": msg_count,
        })
    return {"total": len(result), "rooms": result}


@app.post("/warroom/rooms/{incident_id}/join")
async def join_warroom(
    incident_id: str,
    body: dict = {},
    db: Session = Depends(get_db)
):
    """Record joining a War-Room"""
    inc = db.query(IncidentDB).filter(IncidentDB.code == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="War-Room not found")
    
    user_name = body.get("user_name", "Unknown")
    
    # Log system message for join event
    join_msg = WarRoomChatDB(
        incident_id=incident_id,
        sender="시스템",
        role="System",
        type="system",
        text=f"👤 {user_name}님이 War-Room에 참여하였습니다.",
        timestamp=datetime.utcnow()
    )
    db.add(join_msg)
    
    # Log activity
    log = ActivityLogDB(
        user_name=user_name,
        incident_code=incident_id,
        incident_title=inc.title,
        action="War-Room 참여",
        detail=f"{user_name}이 {incident_id} War-Room에 참여"
    )
    db.add(log)
    db.commit()
    
    return {"status": "joined", "incident_id": incident_id, "title": inc.title}


@app.post("/warroom/upload")
async def upload_warroom_file(
    incident_id: str = Form(...),
    uploaded_by: str = Form(default="Unknown"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a file/image to a War-Room"""
    MAX_SIZE = 50 * 1024 * 1024  # 50MB
    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 50MB)")
    
    # Generate unique filename
    ext = os.path.splitext(file.filename)[1] if file.filename else ""
    unique_name = f"{secrets.token_hex(12)}{ext}"
    save_path = os.path.join(UPLOAD_DIR, unique_name)
    
    with open(save_path, "wb") as f:
        f.write(contents)
    
    file_url = f"/warroom/uploads/{unique_name}"
    
    attachment = WarRoomAttachmentDB(
        incident_id=incident_id,
        filename=unique_name,
        original_name=file.filename,
        file_type=file.content_type,
        url=file_url,
        uploaded_by=uploaded_by,
        timestamp=datetime.utcnow()
    )
    db.add(attachment)
    
    # Also save to chat log as a message
    chat_msg = WarRoomChatDB(
        incident_id=incident_id,
        sender=uploaded_by,
        role="User",
        type="file",
        text=f"[첨부파일] {file.filename}|{file_url}|{file.content_type}",
        timestamp=datetime.utcnow()
    )
    db.add(chat_msg)
    db.commit()
    db.refresh(attachment)
    
    return {
        "status": "success",
        "id": attachment.id,
        "url": file_url,
        "filename": file.filename,
        "file_type": file.content_type
    }


@app.get("/warroom/uploads/{filename}")
async def get_warroom_upload(filename: str):
    """Serve uploaded files"""
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)


@app.get("/warroom/rooms/{incident_id}/attachments")
async def get_warroom_attachments(incident_id: str, db: Session = Depends(get_db)):
    """Get all attachments for a War-Room"""
    attachments = db.query(WarRoomAttachmentDB)\
        .filter(WarRoomAttachmentDB.incident_id == incident_id)\
        .order_by(WarRoomAttachmentDB.timestamp.asc()).all()
    return {"attachments": [{
        "id": a.id,
        "filename": a.filename,
        "original_name": a.original_name,
        "file_type": a.file_type,
        "url": a.url,
        "uploaded_by": a.uploaded_by,
        "timestamp": a.timestamp.isoformat() if a.timestamp else None
    } for a in attachments]}

# ─── End War-Room Management Endpoints ──────────────────────────────────────

@app.post("/warroom/resolve/{incident_id}")
async def resolve_and_learn_incident(incident_id: str, db: Session = Depends(get_db)):
    """
    Gather all chat logs for the incident, compile them into a troubleshooting report,
    and ingest them into ChromaDB for future RAG learning.
    """
    try:
        # Retrieve all messages for this incident
        chats = db.query(WarRoomChatDB).filter(WarRoomChatDB.incident_id == incident_id).order_by(WarRoomChatDB.timestamp.asc()).all()
        
        if not chats:
            raise HTTPException(status_code=404, detail="No chat history found for this incident.")
            
        # Build the Troubleshooting Report text
        report_lines = [
            f"[Troubleshooting Report - War-Room Chat History]",
            f"Incident ID: {incident_id}",
            f"Resolved At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"\n--- Incident Log ---"
        ]
        
        for msg in chats:
            time_str = msg.timestamp.strftime('%H:%M:%S')
            prefix = f"[{time_str}] {msg.sender} ({msg.role}) [{msg.type}]:"
            report_lines.append(f"{prefix} {msg.text}")
            
        report_lines.append("\n--- Resolution ---")
        report_lines.append(f"Incident {incident_id} successfully resolved and added to knowledge base.")
        
        full_report_text = "\n".join(report_lines)
        
        metadata = {
            "source": "war_room_chat",
            "type": "incident_report",
            "category": "human_interaction",
            "incident_id": incident_id,
            "ingested_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Ingest into ChromaDB
        vector_store.add_texts(
            texts=[full_report_text],
            metadatas=[metadata],
            ids=[f"warroom_{incident_id}_{int(datetime.now().timestamp())}"]
        )
        
        # 1. Update Incident Status in DB
        inc = db.query(IncidentDB).filter(IncidentDB.code == incident_id).first()
        if inc:
            inc.status = "Completed"
            inc.updated_at = datetime.utcnow()
        
        # 2. Add Final System Message
        closure_msg = WarRoomChatDB(
            incident_id=incident_id,
            sender="시스템",
            role="System",
            type="system",
            text="✅ 대응이 완료되어 War-Room이 종료되었습니다. (읽기 전용 모드)",
            timestamp=datetime.utcnow()
        )
        db.add(closure_msg)
        db.commit()

        return {
            "status": "success", 
            "message": f"{incident_id} 장애 보고서가 학습되었으며 War-Room이 종료되었습니다.",
            "message_count_processed": len(chats)
        }
        
    except Exception as e:
        logger.error(f"Error resolving incident {incident_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/knowledge/list")
async def list_knowledge_entries(limit: int = 50):
    """
    Return documents from the s_guard_knowledge ChromaDB collection
    so users can review what has been learned by the AI.
    """
    try:
        # Get the raw ChromaDB client collection
        raw_collection = chroma_client.get_or_create_collection(
            name="s_guard_knowledge",
            metadata={"hnsw:space": "cosine"}
        )
        result = raw_collection.get(
            limit=limit,
            include=["documents", "metadatas"]
        )
        entries = []
        ids = result.get("ids", [])
        docs = result.get("documents", [])
        metas = result.get("metadatas", [])
        for i, doc_id in enumerate(ids):
            meta = metas[i] if i < len(metas) else {}
            doc = docs[i] if i < len(docs) else ""
            entries.append({
                "id": doc_id,
                "source": meta.get("source", "unknown"),
                "type": meta.get("type", "document"),
                "incident_id": meta.get("incident_id", ""),
                "title": meta.get("title", doc[:80] + "..." if len(doc) > 80 else doc),
                "ingested_at": meta.get("ingested_at", meta.get("timestamp", "")),
                "preview": doc[:300] + "..." if len(doc) > 300 else doc,
            })
        # Sort by ingested_at descending
        entries.sort(key=lambda x: x.get("ingested_at", ""), reverse=True)
        return {"total": len(entries), "entries": entries}
    except Exception as e:
        logger.error(f"Failed to list knowledge entries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================================
# AUTH Endpoints
# ===========================================================

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hashed}"

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, hashed = stored_hash.split(":")
        return hashlib.sha256((salt + password).encode()).hexdigest() == hashed
    except Exception:
        return False

def generate_token(user_id: int, email: str) -> str:
    raw = f"{user_id}:{email}:{secrets.token_hex(16)}"
    return hashlib.sha256(raw.encode()).hexdigest()

async def send_email_async(to_email: str, subject: str, body: str):
    """
    SMTP 서버(기본: Gmail)를 통해 이메일을 비동기로 발송합니다.
    """
    smtp_server = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    sender_email = os.getenv("SMTP_USER", "")
    sender_password = os.getenv("SMTP_PASSWORD", "")

    if not sender_email or not sender_password:
        logger.error("SMTP credentials (USER/PASSWORD) are missing in environment variables.")
        return

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        # SMTP 연결
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            # TLS 보안 연결 (Gmail 필수)
            if smtp_port == 587:
                server.starttls()
            
            # 인증 정보가 있는 경우 로그인
            server.login(sender_email, sender_password)
            
            server.send_message(msg)
        logger.info(f"Email sent successfully to {to_email} via {smtp_server}")
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")

class RequestResetCode(BaseModel):
    email: str
    employee_id: str

class VerifyResetCode(BaseModel):
    email: str
    employee_id: str
    code: str

@app.post("/auth/request-reset-code")
async def request_reset_code(req: RequestResetCode, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    이메일과 사번이 일치하는 사용자를 확인하고 인증 코드를 전송(로그 기록)합니다.
    """
    user = db.query(UserDB).filter(UserDB.email == req.email, UserDB.employee_id == req.employee_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자 정보를 찾을 수 없습니다.")
    
    # 6자리 인증 코드 생성
    code = "".join(random.choices(string.digits, k=6))
    
    # 기존 코드 삭제 후 새 코드 저장
    db.query(ResetVerificationDB).filter(ResetVerificationDB.email == req.email).delete()
    new_verif = ResetVerificationDB(email=req.email, code=code)
    db.add(new_verif)
    db.commit()
    
    # 이메일 발송 위임
    background_tasks.add_task(send_email_async, user.email, "S-Guard 비밀번호 초기화 인증 코드", f"인증 코드: {code}")
    
    logger.info(f"\n[EMAIL TRIGGERED] To: {user.email}, Verification Code: {code}\n")
    
    return {"status": "success", "message": "인증 코드가 이메일로 전송되었습니다."}

@app.post("/auth/verify-reset-code")
async def verify_reset_code(req: VerifyResetCode, db: Session = Depends(get_db)):
    """
    인증 코드를 검증하고 성공 시 임시 비밀번호를 발급합니다.
    """
    verif = db.query(ResetVerificationDB).filter(
        ResetVerificationDB.email == req.email, 
        ResetVerificationDB.code == req.code
    ).first()
    
    if not verif:
        raise HTTPException(status_code=400, detail="인증 코드가 올바르지 않습니다.")
    
    # 코드 유효 시간 체크 (예: 5분)
    if datetime.utcnow() - verif.created_at > timedelta(minutes=5):
        raise HTTPException(status_code=400, detail="인증 코드가 만료되었습니다.")
    
    user = db.query(UserDB).filter(UserDB.email == req.email, UserDB.employee_id == req.employee_id).first()
    if not user:
         raise HTTPException(status_code=404, detail="사용자 정보를 찾을 수 없습니다.")

    # 임시 비밀번호 생성 (기존 로직 사용)
    temp_password = "".join(random.choices(string.ascii_letters + string.digits + "!@#$%", k=10))
    user.password_hash = hash_password(temp_password)
    
    # 인증 완료 후 코드 삭제
    db.query(ResetVerificationDB).filter(ResetVerificationDB.email == req.email).delete()
    db.commit()
    
    return {
        "status": "success",
        "temp_password": temp_password,
        "name": user.name,
        "email": user.email
    }

class ProfileUpdateRequest(BaseModel):
    user_id: int
    name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    honbu: Optional[str] = None
    team: Optional[str] = None
    part: Optional[str] = None

class SignupRequest(BaseModel):
    email: str
    name: str
    password: str
    company: Optional[str] = None
    employee_id: Optional[str] = None
    phone: Optional[str] = None
    honbu: Optional[str] = None
    team: Optional[str] = None
    part: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

class UserResetPasswordRequest(BaseModel):
    new_password: str

class UserUpdateRoleRequest(BaseModel):
    role: str

class OrgNodeCreate(BaseModel):
    name: str
    code: Optional[str] = None
    parent_id: Optional[int] = None
    depth: int
    sort_order: Optional[int] = 0

class OrgNodeUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    sort_order: Optional[int] = None

@app.post("/auth/signup")
async def signup(req: SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(UserDB).filter(UserDB.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다.")
    user = UserDB(
        email=req.email,
        name=req.name,
        password_hash=hash_password(req.password),
        auth_provider="local",
        company=req.company,
        employee_id=req.employee_id,
        phone=req.phone,
        honbu=req.honbu,
        team=req.team,
        part=req.part,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = generate_token(user.id, user.email)
    user.token = token
    db.commit()
    db.refresh(user)
    return {"status": "success", "token": token, "user": {"id": user.id, "name": user.name, "email": user.email, "role": user.role, "company": user.company, "honbu": user.honbu, "team": user.team, "part": user.part, "phone": user.phone}}

@app.post("/auth/login")
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    # 이메일 또는 사번으로 사용자 조회
    user = db.query(UserDB).filter(
        or_(UserDB.email == req.email, UserDB.employee_id == req.email),
        UserDB.is_active == True
    ).first()
    
    if not user or not user.password_hash or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="이메일(또는 사번) 또는 비밀번호가 올바르지 않습니다.")
    
    token = generate_token(user.id, user.email)
    user.token = token
    db.commit()
    
    return {"status": "success", "token": token, "user": {
        "id": user.id, "name": user.name, "email": user.email, "role": user.role,
        "company": user.company, "honbu": user.honbu, "team": user.team, "part": user.part, "phone": user.phone
    }}

class ChangePasswordRequest(BaseModel):
    user_id: int
    new_password: str

@app.post("/auth/change-password")
async def change_password(req: ChangePasswordRequest, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    user.password_hash = hash_password(req.new_password)
    db.commit()
    return {"status": "success", "message": "비밀번호가 성공적으로 변경되었습니다."}

@app.patch("/auth/profile")
async def update_profile(req: ProfileUpdateRequest, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    if req.name is not None: user.name = req.name
    if req.phone is not None: user.phone = req.phone
    if req.company is not None: user.company = req.company
    if req.honbu is not None: user.honbu = req.honbu
    if req.team is not None: user.team = req.team
    if req.part is not None: user.part = req.part
    
    db.commit()
    db.refresh(user)
    return {"status": "success", "user": {
        "id": user.id, "name": user.name, "email": user.email, "role": user.role,
        "company": user.company, "honbu": user.honbu, "team": user.team, "part": user.part, "phone": user.phone
    }}

class PasswordResetRequest(BaseModel):
    email: str
    employee_id: str

@app.post("/auth/reset-password")
async def reset_password(req: PasswordResetRequest, db: Session = Depends(get_db)):
    """
    이메일과 사번이 모두 일치하는 사용자를 찾아 임시 비밀번호를 생성하고 반환합니다.
    내부 시스템이므로 임시 비밀번호를 응답에 포함해 화면에 표시합니다.
    """
    user = db.query(UserDB).filter(
        UserDB.email == req.email,
        UserDB.employee_id == req.employee_id,
        UserDB.is_active == True
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="입력하신 정보와 일치하는 사용자를 찾을 수 없습니다.")

    # 임시 비밀번호 생성: 영문대소/숫자/특수문자 조합 10자
    import random, string
    chars = string.ascii_letters + string.digits + "!@#$%"
    temp_pw = ''.join(random.choices(chars, k=10))

    user.password_hash = hash_password(temp_pw)
    db.commit()
    logger.info(f"Password reset for user {user.email}")

    return {
        "status": "success",
        "message": "임시 비밀번호가 발급되었습니다. 로그인 후 반드시 변경해 주세요.",
        "temp_password": temp_pw,
        "name": user.name,
        "email": user.email,
    }

@app.post("/auth/google")
async def google_login(payload: dict, db: Session = Depends(get_db)):
    email = payload.get("email")
    name = payload.get("name", "Google User")
    if not email:
        raise HTTPException(status_code=400, detail="이메일 정보가 없습니다.")
    user = db.query(UserDB).filter(UserDB.email == email).first()
    if not user:
        user = UserDB(email=email, name=name, auth_provider="google")
        db.add(user)
        db.commit()
        db.refresh(user)
    token = generate_token(user.id, user.email)
    return {"status": "success", "token": token, "user": {"id": user.id, "name": user.name, "email": user.email, "role": user.role}}

# ── User Management ────────────────────────────────
@app.get("/users")
async def list_users(db: Session = Depends(get_db)):
    users = db.query(UserDB).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "role": u.role,
            "company": u.company,
            "employee_id": u.employee_id,
            "phone": u.phone,
            "honbu": u.honbu,
            "team": u.team,
            "part": u.part,
            "is_active": u.is_active,
            "created_at": u.created_at
        } for u in users
    ]

@app.post("/users/{user_id}/reset-password")
async def reset_user_password(user_id: int, req: UserResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    user.password_hash = hash_password(req.new_password)
    db.commit()
    return {"status": "success", "message": "비밀번호가 초기화되었습니다."}

@app.patch("/users/{user_id}/status")
async def toggle_user_status(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    user.is_active = not user.is_active
    db.commit()
    return {"status": "success", "is_active": user.is_active}

@app.patch("/users/{user_id}/role")
async def update_user_role(user_id: int, req: UserUpdateRoleRequest, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    user.role = req.role
    db.commit()
    return {"status": "success", "role": user.role}

# ── Organization Management ────────────────────────
@app.get("/org/tree")
async def get_org_tree(db: Session = Depends(get_db)):
    # Simple recursive builder for a small tree
    def build_tree(parent_id=None):
        nodes = db.query(OrganizationDB).filter(OrganizationDB.parent_id == parent_id).order_by(OrganizationDB.sort_order).all()
        tree = []
        for node in nodes:
            tree.append({
                "id": node.id,
                "name": node.name,
                "code": node.code,
                "parent_id": node.parent_id,
                "depth": node.depth,
                "sort_order": node.sort_order,
                "children": build_tree(node.id)
            })
        return tree
    
    return build_tree()

@app.post("/org/nodes")
async def create_org_node(req: OrgNodeCreate, db: Session = Depends(get_db)):
    node = OrganizationDB(
        name=req.name,
        code=req.code,
        parent_id=req.parent_id,
        depth=req.depth,
        sort_order=req.sort_order
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return node

@app.patch("/org/nodes/{node_id}")
async def update_org_node(node_id: int, req: OrgNodeUpdate, db: Session = Depends(get_db)):
    node = db.query(OrganizationDB).filter(OrganizationDB.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if req.name is not None: node.name = req.name
    if req.code is not None: node.code = req.code
    if req.sort_order is not None: node.sort_order = req.sort_order
    db.commit()
    return node

@app.delete("/org/nodes/{node_id}")
async def delete_org_node(node_id: int, db: Session = Depends(get_db)):
    node = db.query(OrganizationDB).filter(OrganizationDB.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    db.delete(node)
    db.commit()
    return {"status": "success"}

# ===========================================================
# INCIDENTS Endpoints
# ===========================================================

class IncidentCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    severity: str = "NORMAL"
    status: str = "Open"
    incident_type: str = "AI"
    assigned_to: Optional[str] = None
    source_sms_id: Optional[int] = None

class IncidentUpdateRequest(BaseModel):
    status: Optional[str] = None
    severity: Optional[str] = None
    assigned_to: Optional[str] = None
    description: Optional[str] = None

def generate_incident_code(db: Session) -> str:
    count = db.query(IncidentDB).count()
    return f"INC-{20240000 + count + 1}"

@app.get("/incidents")
async def get_incidents(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    incident_type: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    q = db.query(IncidentDB)
    if status:
        q = q.filter(IncidentDB.status == status)
    if severity:
        q = q.filter(IncidentDB.severity == severity)
    if incident_type:
        q = q.filter(IncidentDB.incident_type == incident_type)
    incidents = q.order_by(IncidentDB.created_at.desc()).limit(limit).all()
    result = []
    for inc in incidents:
        result.append({
            "id": inc.id,
            "code": inc.code,
            "title": inc.title,
            "description": inc.description,
            "severity": inc.severity,
            "status": inc.status,
            "incident_type": inc.incident_type,
            "assigned_to": inc.assigned_to,
            "created_at": inc.created_at.isoformat() if inc.created_at else None,
            "updated_at": inc.updated_at.isoformat() if inc.updated_at else None,
        })
    return {"total": len(result), "incidents": result}

@app.post("/incidents")
async def create_incident(req: IncidentCreateRequest, db: Session = Depends(get_db)):
    code = generate_incident_code(db)
    inc = IncidentDB(
        code=code,
        title=req.title,
        description=req.description,
        severity=req.severity,
        status=req.status,
        incident_type=req.incident_type,
        assigned_to=req.assigned_to,
        source_sms_id=req.source_sms_id,
    )
    db.add(inc)
    db.commit()
    db.refresh(inc)
    return {"status": "success", "code": inc.code, "id": inc.id}

@app.patch("/incidents/{incident_id}")
async def update_incident(incident_id: int, req: IncidentUpdateRequest, db: Session = Depends(get_db)):
    inc = db.query(IncidentDB).filter(IncidentDB.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="인시던트를 찾을 수 없습니다.")
    if req.status is not None:
        inc.status = req.status
    if req.severity is not None:
        inc.severity = req.severity
    if req.assigned_to is not None:
        inc.assigned_to = req.assigned_to
    if req.description is not None:
        inc.description = req.description
    inc.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(inc)
    return {"status": "success", "id": inc.id, "code": inc.code}

# ===========================================================
# ACTIVITY LOGS Endpoints
# ===========================================================

class ActivityLogCreateRequest(BaseModel):
    user_name: Optional[str] = "System"
    incident_code: Optional[str] = None
    incident_title: Optional[str] = None
    action: str
    detail: Optional[str] = None
    team: Optional[str] = None
    report_type: Optional[str] = "AI 리포트"

@app.get("/activity-logs")
async def get_activity_logs(limit: int = 50, db: Session = Depends(get_db)):
    logs = db.query(ActivityLogDB).order_by(ActivityLogDB.created_at.desc()).limit(limit).all()
    result = []
    for log in logs:
        result.append({
            "id": log.id,
            "user_name": log.user_name,
            "incident_code": log.incident_code,
            "incident_title": log.incident_title,
            "action": log.action,
            "detail": log.detail,
            "team": log.team,
            "report_type": log.report_type,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })
    return {"total": len(result), "logs": result}

@app.post("/activity-logs")
async def create_activity_log(req: ActivityLogCreateRequest, db: Session = Depends(get_db)):
    log = ActivityLogDB(
        user_name=req.user_name,
        incident_code=req.incident_code,
        incident_title=req.incident_title,
        action=req.action,
        detail=req.detail,
        team=req.team,
        report_type=req.report_type,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return {"status": "success", "id": log.id}

# ===========================================================
# KEYWORD DELETE Endpoint
# ===========================================================

@app.delete("/sms/keywords/{keyword}")
async def delete_keyword(keyword: str, db: Session = Depends(get_db)):
    kw = db.query(KeywordDB).filter(KeywordDB.keyword == keyword).first()
    if not kw:
        raise HTTPException(status_code=404, detail="키워드를 찾을 수 없습니다.")
    db.delete(kw)
    db.commit()
    return {"status": "success", "deleted": keyword}

# SMS 수신 시 자동으로 Incident 생성하는 hook
@app.on_event("startup")
async def startup_create_incident_on_sms():
    """기존 수신 SMS 중 인시던트가 없는 항목들을 자동으로 인시던트 생성"""
    pass  # 이후 SMS 수신 시 receive_sms endpoint에서 자동 생성

@app.post("/sms/convert-multimodal")
async def convert_multimodal(file: UploadFile = File(...)):
    """
    이미지 또는 음성 파일을 텍스트로 변환하는 실제 AI 멀티모달 처리 엔드포인트
    """
    content_type = file.content_type
    filename = file.filename.lower()
    
    # 파일 내용 읽기
    content = await file.read()
    
    if "image" in content_type:
        # 1. Base64 인코딩
        base64_image = base64.b64encode(content).decode('utf-8')
        
        # 2. Ollama LLAVA 모델 호출
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": "llava",
                        "prompt": "이 이미지에 포함된 모든 텍스트를 있는 그대로 추출해서 보여줘. 설명이나 요약은 하지 말고 텍스트 내용만 한국어로 출력해줘.",
                        "images": [base64_image],
                        "stream": False
                    }
                )
                
                if response.status_code == 200:
                    result_data = response.json()
                    raw_response = result_data.get('response', '')
                    print(f"DEBUG: Ollama raw response: {raw_response[:100]}...")
                    result_text = raw_response if raw_response else "텍스트를 추출하지 못했습니다."
                else:
                    print(f"DEBUG: Ollama error: {response.status_code} - {response.text}")
                    result_text = f"[AI 분석 오류] Ollama 서버 응답 실패 (Code: {response.status_code})"
        except Exception as e:
            result_text = f"[AI 분석 오류] 서버 연동 중 문제 발생: {str(e)}"
            
    elif any(ext in filename for ext in ["mp3", "wav", "m4a", "ogg"]):
        # Audio 처리 (현재는 텍스트 변환 시뮬레이션 - Whisper 등 연동 가능)
        result_text = "[음성 분석 시뮬레이션] '현재 서초 데이터센터 2층 L2 스위치 모듈에서 과열 경고음이 감지되고 있습니다. 즉시 점검이 필요합니다.' (실제 STT 연동 준비 중)"
    else:
        result_text = "[멀티모달 분석] 지원하지 않는 파일 형식입니다. (이미지/음성 파일만 지원)"

    return {
        "status": "success",
        "converted_text": result_text,
        "filename": file.filename,
        "content_type": content_type
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
