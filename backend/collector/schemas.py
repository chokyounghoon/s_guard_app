from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class ParsedSMS(BaseModel):
    if_id: str
    if_name: str
    biz_code: str
    service_code: str
    external_institution: str
    
    transaction_date: str
    transaction_time: str
    collected_at: datetime
    
    avg_error_count: int
    avg_error_rate: float
    error_threshold: float
    
    current_tx_count: int
    current_error_count: int
    current_error_rate: float
    
    recipients: List[str]
    msg_received_at: datetime
    raw_message: str
