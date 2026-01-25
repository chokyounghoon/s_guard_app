import re
from datetime import datetime
from .schemas import ParsedSMS

def parse_sms(text: str) -> ParsedSMS:
    lines = text.split('\n')
    data = {}
    
    def extract_value(line, key_pattern):
        # Find pattern like "▶ IF아이디 : [SHB02681]"
        # Regex to capture content inside last [] pair strictly or loosely?
        # Strategy: Look for "▶ Key :" then take everything after `[` until the last `]`.
        if key_pattern in line:
            parts = line.split(':', 1)
            if len(parts) > 1:
                val_part = parts[1].strip()
                # Remove leading '[' and trailing ']' and any suffix like (1시간) or %
                # Logic: find first '[' and last ']'
                start = val_part.find('[')
                end = val_part.rfind(']')
                if start != -1 and end != -1:
                    return val_part[start+1:end].strip()
        return None

    # Mapping keys to fields
    # Note: Using simple string search for robustness
    for line in lines:
        if "IF아이디" in line: data['if_id'] = extract_value(line, "IF아이디")
        if "IF명" in line: data['if_name'] = extract_value(line, "IF명")
        if "업무코드" in line: data['biz_code'] = extract_value(line, "업무코드")
        if "서비스코드" in line: data['service_code'] = extract_value(line, "서비스코드")
        if "대외기관" in line: data['external_institution'] = extract_value(line, "대외기관")
        
        if "거래일자" in line: data['transaction_date'] = extract_value(line, "거래일자")
        if "거래시간" in line: data['transaction_time'] = extract_value(line, "거래시간")
        if "거래집계일시" in line: 
            val = extract_value(line, "거래집계일시")
            if val: data['collected_at'] = datetime.strptime(val, "%Y-%m-%d %H:%M:%S")

        if "비교기간평균거래건수" in line: data['avg_error_count'] = 0 # Placeholder if not found
        # (Typo in header mapping? Check raw text)
        # ▶ 비교기간평균오류건수 : [12]
        if "비교기간평균오류건수" in line: data['avg_error_count'] = int(extract_value(line, "비교기간평균오류건수"))
        if "비교기간평균오류율" in line: data['avg_error_rate'] = float(extract_value(line, "비교기간평균오류율"))
        if "오류율임계치" in line: data['error_threshold'] = float(extract_value(line, "오류율임계치"))

        if "현재거래건수" in line: data['current_tx_count'] = int(extract_value(line, "현재거래건수"))
        if "현재오류건수" in line: data['current_error_count'] = int(extract_value(line, "현재오류건수"))
        if "현재오류율" in line: data['current_error_rate'] = float(extract_value(line, "현재오류율"))
        
        if "메시지 수신자" in line: 
            val = extract_value(line, "메시지 수신자")
            if val: data['recipients'] = [x.strip() for x in val.split(',')]
            
        if "메시지 발생일시" in line:
            val = extract_value(line, "메시지 발생일시")
            # The raw text has invisible char or needs clean up
            if val: data['msg_received_at'] = datetime.strptime(val.strip(), "%Y-%m-%d %H:%M:%S")

    data['raw_message'] = text
    
    # Fill missing optional defaults if necessary
    return ParsedSMS(**data)
