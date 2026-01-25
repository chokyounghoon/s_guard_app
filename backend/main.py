from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .database import engine, Base, get_db, SessionLocal
from .core.models import Incident, IncidentLevel
from .collector.parser import parse_sms
from .collector.grade import determine_severity
from pydantic import BaseModel

# Initialize Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="S-Guard AI Platform",
    description="AI Agent 기반 지능형 장애 예방 및 통합 관리 플랫폼",
    version="1.0.0"
)

# CORS Config
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SMSInput(BaseModel):
    text: str

from .brain.agent import agent
from .brain.rag import rag_engine
from .core.models import ChatLog

@app.post("/api/sms/receive")
async def receive_sms(input: SMSInput, db: Session = Depends(get_db)):
    try:
        # 1. Parse SMS
        parsed_data = parse_sms(input.text)
        
        # 2. Determine Severity
        severity = determine_severity(parsed_data.current_error_rate, parsed_data.error_threshold)
        
        # 3. Create Incident Record
        incident = Incident(
            if_id=parsed_data.if_id,
            if_name=parsed_data.if_name,
            biz_code=parsed_data.biz_code,
            service_code=parsed_data.service_code,
            transaction_date=parsed_data.transaction_date,
            transaction_time=parsed_data.transaction_time,
            collected_at=parsed_data.collected_at,
            avg_error_count=parsed_data.avg_error_count,
            avg_error_rate=parsed_data.avg_error_rate,
            error_threshold=parsed_data.error_threshold,
            current_tx_count=parsed_data.current_tx_count,
            current_error_count=parsed_data.current_error_count,
            current_error_rate=parsed_data.current_error_rate,
            recipients=",".join(parsed_data.recipients) if parsed_data.recipients else "",
            msg_received_at=parsed_data.msg_received_at,
            raw_message=parsed_data.raw_message,
            severity=severity,
            status="OPEN"
        )
        
        db.add(incident)
        db.commit()
        db.refresh(incident)
        
        # 4. AI Analysis & Guide (S-Guard Brain)
        # Background task ideally, but sync for demo
        similar_cases = rag_engine.search(parsed_data.raw_message)
        ai_guide = await agent.analyze_incident(parsed_data.raw_message, similar_cases)
        
        # Save AI Guide to Chat
        chat_log = ChatLog(
            incident_id=incident.id,
            sender="S-Guard AI",
            message=ai_guide,
            is_ai=1
        )
        db.add(chat_log)
        db.commit()
        
        return {
            "status": "success",
            "incident_id": incident.id,
            "severity": incident.severity.value,
            "message": "장애가 접수되었으며, AI 가이드를 생성했습니다."
        }
        
    except Exception as e:
        # Log error
        print(f"Error processing SMS: {e}")
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import WebSocket, WebSocketDisconnect
from .warroom.socket import manager
from .core.models import ChatLog
import json
from datetime import datetime

@app.websocket("/ws/chat/{incident_id}")
async def websocket_endpoint(websocket: WebSocket, incident_id: str):
    await manager.connect(websocket, incident_id)
    # Create a new DB session for this connection lifecycle or per message
    # For simplicity in async, we might use run_in_executor or a separate async db session.
    # But here, standard sync session with careful usage. 
    # Actually, for high perf, we shouldn't block loop. 
    # Let's keep it simple: create session per message handling or use simple wrapper.
    
    db = SessionLocal() 
    
    try:
        while True:
            data = await websocket.receive_text()
            # Expecting JSON: {"sender": "Kim", "message": "Hello"}
            try:
                msg_data = json.loads(data)
                sender = msg_data.get("sender", "Anonymous")
                message = msg_data.get("message", "")
                
                if message:
                    # Save to DB
                    chat_log = ChatLog(
                        incident_id=int(incident_id),
                        sender=sender,
                        message=message,
                        is_ai=0
                    )
                    db.add(chat_log)
                    db.commit()
                    
                    # Broadcast
                    response = {
                        "sender": sender,
                        "message": message,
                        "timestamp": str(datetime.now())
                    }
                    await manager.broadcast(json.dumps(response), incident_id)
                    
            except json.JSONDecodeError:
                # Fallback for plain text tests
                await manager.broadcast(json.dumps({"sender": "System", "message": f"Invalid format: {data}"}), incident_id)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, incident_id)
        # await manager.broadcast(json.dumps({"sender": "System", "message": "User left"}), incident_id)
    finally:
        db.close()
