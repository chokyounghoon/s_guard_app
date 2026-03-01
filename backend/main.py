from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import re
from datetime import datetime
import logging
import json
import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

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
    
    msg_db = SMSMessageDB(
        sender=sms.sender,
        message=sms.message,
        timestamp=datetime.utcnow(),
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

@app.get("/ai/insight")
async def get_ai_insight(db: Session = Depends(get_db)):
    """
    대시보드 상단 AI Insight 패널용 데이터
    수신된 SMS 내용을 보고 신한DS내 축적된 KMS를 연동 LLM을 활용하여 장애를 예측 (구현 예정/시뮬레이션)
    """
    # 가장 최근 SMS 1건 조회
    recent_sms = db.query(SMSMessageDB).order_by(SMSMessageDB.timestamp.desc()).first()
    
    # 전체 최근 메시지 목록 (최대 100건)을 조회하여 예측 카운트를 집계
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

    if recent_sms:
        text = recent_sms.message
        category = "report"
        severity = "info"
        type_str = "insight"
        
        # 키워드 기반 KMS 연동 LLM 분석 시뮬레이션
        if "cpu" in text.lower() or "메모리" in text:
            severity = "high"
            type_str = "warning"
            category = "server"
            insight_text = f"💡 [Insight] 수신된 SMS ('{text[:15]}...') 기반 분석: 신한DS KMS 연동 LLM 분석 결과, 과거 배치 작업 중 발생한 서버 과부하 패턴과 98% 일치하며 시스템 강제종료가 예측됩니다."
        elif "db" in text.lower() or "데이터베이스" in text:
            severity = "critical"
            type_str = "error"
            category = "database"
            insight_text = f"🚨 [Critical] 수신된 SMS ('{text[:15]}...') 기반 분석: 신한DS KMS 연동 LLM 분석 결과, DB Connection Pool 고갈 패턴과 94% 일치. 결제 모듈 응답 지연 예측됨."
        elif "네트워크" in text or "network" in text.lower():
            severity = "medium"
            type_str = "insight"
            category = "network"
            insight_text = f"⚠️ [Insight] 수신된 SMS ('{text[:15]}...') 기반 분석: 신한DS KMS 연동 LLM 분석 결과, L4 스위치 트래픽 포화 상태 예측됨."
        else:
            insight_text = f"🔍 [Insight] 수신된 SMS ('{text[:15]}...') 기반 분석: 신한DS KMS 연동 LLM이 유사 사례를 분석 중입니다. 분석결과 일시적 발생 오류로 판단됩니다."

        current_log = {
            "id": f"KMS-{recent_sms.id}",
            "type": type_str,
            "category": category,
            "severity": severity,
            "text": insight_text,
            "detail": f"수신 시간: {recent_sms.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        }
    else:
        current_log = {
            "id": "SYS-000",
            "type": "info",
            "category": "report",
            "severity": "info",
            "text": "실시간 데이터 대기 중... 새로운 SMS를 기다리고 있습니다.",
            "detail": "신한DS KMS 연동 LLM 분석 대기 중"
        }

    return {
        "status": "active",
        "learning_data_size": "15.2 TB (KMS)",
        "accuracy": "98.5%",
        "prediction_counts": prediction_counts,
        "current_log": current_log
    }

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
    AI Agent Chatbot Endpoint
    Uses Langchain RetrievalQA to answer questions based on ingested ChromaDB data.
    """
    query = request.query
    
    try:
        # 1. RAG 체인을 통한 답변 생성
        response = qa_chain.run(query)
        
        # 2. 참고한 유사 문서(로그) 가져오기 (부가 정보 제공용)
        docs = vector_store.similarity_search(query, k=2)
        related_logs = [doc.page_content for doc in docs]

        return {
            "response": response,
            "related_logs": related_logs
        }
    except Exception as e:
        logger.error(f"AI Chat Error: {str(e)}")
        # 실패시 Fallback Mock Logic
        return {
            "response": "현재 AI 에이전트 서비스 응답이 지연되고 있습니다.",
            "related_logs": []
        }

class DocumentIngestRequest(BaseModel):
    content: str
    metadata: Optional[dict] = {}

@app.post("/ai/ingest")
async def ingest_document(request: DocumentIngestRequest):
    """
    System Admin Endpoint to inject knowledge base (text/logs) into ChromaDB
    """
    try:
        vector_store.add_texts(
            texts=[request.content],
            metadatas=[request.metadata]
        )
        return {"status": "success", "message": "도큐먼트가 성공적으로 ChromaDB에 임베딩되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

