#!/usr/bin/env python3
"""
Claude Code session logger.
Logs prompts (via UserPromptSubmit hook) and responses (via Stop hook)
to daily log files in claude_logs/.

Usage (configured via hooks in .claude/settings.local.json):
  UserPromptSubmit: python3 /Users/sanjeev/iot_dashboard/claude_logger.py prompt
  Stop:             python3 /Users/sanjeev/iot_dashboard/claude_logger.py stop

Reasoning: To allow claude to run this each time automatically with the prompts
"""

import glob
import json
import os
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, "claude_logs")
os.makedirs(LOG_DIR, exist_ok=True)

date_str = datetime.now().strftime("%Y-%m-%d")
log_file = os.path.join(LOG_DIR, f"{date_str}.log")
event_type = sys.argv[1] if len(sys.argv) > 1 else "unknown"
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

try:
    data = json.load(sys.stdin)
except Exception:
    data = {}


def extract_last_response(path):
    """Extract the last assistant text block from a JSONL transcript file."""
    last_response = None
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("type") == "assistant":
                        content = entry.get("message", {}).get("content", "")
                        if isinstance(content, list):
                            texts = [
                                b.get("text", "")
                                for b in content
                                if b.get("type") == "text"
                            ]
                            text = "\n".join(t for t in texts if t)
                        elif isinstance(content, str):
                            text = content
                        else:
                            text = ""
                        if text:
                            last_response = text
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass
    return last_response


def get_last_assistant_response(session_id):
    """Find the transcript for the given session_id and return the last assistant message."""
    home = os.path.expanduser("~")
    transcript_dirs = glob.glob(os.path.join(home, ".claude", "projects", "*"))
    for tdir in transcript_dirs:
        transcript = os.path.join(tdir, f"{session_id}.jsonl")
        if os.path.exists(transcript):
            return extract_last_response(transcript)
    return None


with open(log_file, "a", encoding="utf-8") as f:
    if event_type == "prompt":
        prompt = data.get("prompt", "")
        f.write(f"\n{'='*60}\n[{timestamp}] USER:\n{prompt}\n")
    elif event_type == "stop":
        session_id = data.get("session_id", "")
        response = get_last_assistant_response(session_id) if session_id else None
        f.write(f"\n[{timestamp}] CLAUDE:\n")
        if response:
            f.write(f"{response}\n")
        else:
            f.write("(response not captured — check ~/.claude/projects/ for full transcript)\n")
        f.write(f"{'='*60}\n")
