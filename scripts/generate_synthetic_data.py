import requests
import json
import random
import time
from datetime import datetime, timedelta

# 백엔드 API 주소 (Docker 환경 외부에서 호스트 머신으로 실행하므로 localhost:8000 사용)
API_URL = "http://localhost:8000/ai/ingest"

# 합성 데이터 생성용 템플릿 및 키워드 풀
SYSTEMS = ["Core Banking DB", "Payment Gateway", "User Auth Service", "Image Processing Worker", "Notification Service", "L4 Switch", "Redis Cache Cluster"]
SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
PROBLEM_TYPES = [
    "Connection Pool Exhaustion",
    "High CPU Usage",
    "Memory Leak",
    "Disk Space Full",
    "Network Timeout",
    "Deadlock Detected",
    "Certificate Expired"
]
ROOT_CAUSES = [
    "Unoptimized heavy read query scanning large tables without indexes.",
    "A recent deployment introduced a regression blocking the main thread.",
    "Third-party API throttling caused a cascading failure in the connection pool.",
    "Log rotation failed, causing the disk to reach 100% capacity.",
    "Hardware failure on the primary switch module.",
    "Unexpected traffic spike from a marketing campaign overwhelmed the service.",
]
RESOLUTIONS = [
    "Killed the long-running queries and added a composite index on the target table.",
    "Rolled back the deployment to the previous stable version.",
    "Scaled up the connection pool size and implemented a circuit breaker for the 3rd party API.",
    "Manually cleared old logs and restarted the logrotate service.",
    "Failed over to the secondary switch and initiated an RMA for the faulty hardware.",
    "Auto-scaled the application cluster and enabled aggressive caching."
]

def generate_synthetic_documents(count=50):
    docs = []
    base_time = datetime.utcnow()
    
    for i in range(count):
        system = random.choice(SYSTEMS)
        severity = random.choice(SEVERITIES)
        prob_type = random.choice(PROBLEM_TYPES)
        root_cause = random.choice(ROOT_CAUSES)
        resolution = random.choice(RESOLUTIONS)
        
        # 사건 발생 시간 (최근 1년 이내의 랜덤한 시간)
        incident_time = base_time - timedelta(days=random.randint(1, 365), hours=random.randint(0, 23))
        
        # Knowledge Base 형태의 본문 생성
        content = f"""
[Troubleshooting Report]
System: {system}
Issue ID: INC-{random.randint(10000, 99999)}
Date: {incident_time.strftime('%Y-%m-%d %H:%M:%S UTC')}
Severity: {severity}
Problem Type: {prob_type}

Description:
Alerts were triggered for {system} indicating {prob_type}. Monitoring dashboards showed a sudden spike in errors and degraded response times.

Root Cause Analysis:
{root_cause}

Resolution & Action Taken:
{resolution}

Lessons Learned:
System administrators should monitor the specific metrics related to {prob_type} and ensure automated alerts trigger sooner before full service degradation.
"""
        
        metadata = {
            "source": "synthetic_knowledge_base",
            "system": system,
            "severity": severity,
            "problem_type": prob_type,
            "incident_date": incident_time.strftime('%Y-%m-%d')
        }
        
        docs.append({"content": content.strip(), "metadata": metadata})
        
    return docs

def ingest_to_chroma():
    print("Generating synthetic data...")
    documents = generate_synthetic_documents(500) # 500건 생성
    print(f"Generated {len(documents)} documents. Starting ingestion to ChromaDB via API...")
    
    success_count = 0
    fail_count = 0
    
    for i, doc in enumerate(documents):
        try:
            response = requests.post(API_URL, json=doc)
            if response.status_code == 200:
                success_count += 1
                if (i + 1) % 10 == 0:
                    print(f"Ingested {success_count}/{len(documents)}...")
            else:
                fail_count += 1
                print(f"Failed to ingest Doc {i}: {response.text}")
        except Exception as e:
            fail_count += 1
            print(f"Error on Doc {i}: {e}")
            
        # 백엔드 및 Ollama 임베딩 모델에 너무 큰 부하가 가지 않도록 약간의 지연
        time.sleep(0.5)
        
    print(f"\nIngestion Complete! Success: {success_count}, Failed: {fail_count}")

if __name__ == "__main__":
    ingest_to_chroma()
