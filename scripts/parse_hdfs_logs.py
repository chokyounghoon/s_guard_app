import re
import os
import json
from datetime import datetime

# Regex for HDFS log format: Date Time PID Level Component: Message
# Example: 081109 203615 148 INFO dfs.DataNode$PacketResponder: Message...
HDFS_LOG_PATTERN = re.compile(r'^(\d{6})\s+(\d{6})\s+(\d+)\s+([A-Z]+)\s+([^:]+):\s+(.*)$')

def parse_hdfs_log(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return []

    parsed_events = []
    with open(file_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            match = HDFS_LOG_PATTERN.match(line)
            if match:
                date_str, time_str, pid, level, component, message = match.groups()
                
                # Simple Anomaly Detection Logic
                is_anomaly = False
                severity = "NORMAL"
                
                if level in ["WARN", "ERROR"]:
                    is_anomaly = True
                    severity = "CRITICAL" if level == "ERROR" else "MAJOR"
                
                if "exception" in message.lower() or "failed" in message.lower():
                    is_anomaly = True
                    severity = "CRITICAL"

                event = {
                    "line": line_num,
                    "timestamp": f"20{date_str[:2]}-{date_str[2:4]}-{date_str[4:6]} {time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}",
                    "pid": pid,
                    "level": level,
                    "component": component,
                    "message": message,
                    "is_anomaly": is_anomaly,
                    "severity": severity
                }
                parsed_events.append(event)
            else:
                # Handle potential multi-line logs or non-matching lines
                # For demo purposes, we'll just skip them or log as raw
                pass
                
    return parsed_events

def main():
    log_file = "/Users/choisu/workspace_new/s_guard_AI/HDFS_2k.log"
    print(f"--- S-GUARD Layer 1: HDFS Log Parser ---")
    print(f"Parsing file: {log_file}")
    
    events = parse_hdfs_log(log_file)
    
    total_events = len(events)
    anomalies = [e for e in events if e['is_anomaly']]
    
    print(f"Total events parsed: {total_events}")
    print(f"Anomalies detected: {len(anomalies)}")
    print("-" * 50)
    
    # Print top 5 anomalies
    if anomalies:
        print("Top 5 Detected Anomalies:")
        for a in anomalies[:5]:
            print(f"[{a['timestamp']}] {a['level']} @ {a['component']}")
            print(f"  Message: {a['message'][:100]}...")
            print(f"  Severity: {a['severity']}")
            print()

    # Save to a JSON for potential ingestion
    output_file = "/Users/choisu/workspace_new/s_guard_AI/scripts/parsed_hdfs_events.json"
    with open(output_file, 'w') as f:
        json.dump(events, f, indent=2)
    print(f"Full parsed events saved to: {output_file}")

if __name__ == "__main__":
    main()
