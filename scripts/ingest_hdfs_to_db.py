import json
import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://sguard_user:sguard_password@localhost:5433/sguard_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class IncidentDB(Base):
    __tablename__ = "incidents"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(30), unique=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(20), default="NORMAL")
    status = Column(String(30), default="Open")
    incident_type = Column(String(20), default="AI")
    assigned_to = Column(String(100), nullable=True)
    source_sms_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

def ingest_anomalies(json_path):
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found.")
        return

    with open(json_path, 'r') as f:
        events = json.load(f)

    anomalies = [e for e in events if e['is_anomaly']]
    print(f"Found {len(anomalies)} anomalies in JSON.")

    db = SessionLocal()
    try:
        count = 0
        for a in anomalies:
            code = f"LOG-{a['line']}"
            existing = db.query(IncidentDB).filter(IncidentDB.code == code).first()
            
            if not existing:
                incident = IncidentDB(
                    code=code,
                    title=f"System Log Anomaly: {a['component']}",
                    description=a['message'],
                    severity=a['severity'],
                    status="Open",
                    incident_type="LOG",
                    created_at=datetime.strptime(a['timestamp'], "%Y-%m-%d %H:%M:%S")
                )
                db.add(incident)
                count += 1
        
        db.commit()
        print(f"Successfully ingested {count} new anomalies into the database.")
    except Exception as e:
        print(f"Error during ingestion: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    json_path = "/Users/choisu/workspace_new/s_guard_AI/scripts/parsed_hdfs_events.json"
    ingest_anomalies(json_path)
