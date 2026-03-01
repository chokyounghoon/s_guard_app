from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import re
from datetime import datetime
import logging
import json
import os
import httpx
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
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
    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
