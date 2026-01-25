from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Enum
from sqlalchemy.sql import func
from ..database import Base
import enum

class IncidentLevel(enum.Enum):
    LEVEL_1 = "Level 1 (주의)"
    LEVEL_2 = "Level 2 (경고)"
    LEVEL_3 = "Level 3 (심각)"

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    
    # SMS 원문에서 파싱된 정보
    if_id = Column(String, index=True)
    if_name = Column(String)
    biz_code = Column(String)
    service_code = Column(String)
    
    transaction_date = Column(String)
    transaction_time = Column(String)
    collected_at = Column(DateTime) # 거래집계일시
    
    # 통계 정보
    avg_error_count = Column(Integer)
    avg_error_rate = Column(Float)
    error_threshold = Column(Float)
    
    current_tx_count = Column(Integer)
    current_error_count = Column(Integer)
    current_error_rate = Column(Float)
    
    # 관리 정보
    recipients = Column(String) # 수신자 목록
    msg_received_at = Column(DateTime) # 메시지 발생일시
    raw_message = Column(Text) # 원문
    
    # 시스템 부여 정보
    severity = Column(Enum(IncidentLevel), default=IncidentLevel.LEVEL_1)
    status = Column(String, default="OPEN") # OPEN, IN_PROGRESS, RESOLVED
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
class ChatLog(Base):
    __tablename__ = "chat_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, index=True)
    sender = Column(String)
    message = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    is_ai = Column(Integer, default=0) # 0: Human, 1: AI
