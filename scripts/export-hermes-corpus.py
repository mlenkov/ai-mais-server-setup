#!/usr/bin/env python3
"""Export Hermes agent memories, conversations, and configs to a text corpus for Graphify."""

import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
CORPUS_DIR = HERMES_HOME / "graphify-corpus"
TIMESTAMP = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def export_messages(state_db: Path, profile_name: str) -> list[Path]:
    """Export state.db messages to per-session markdown files."""
    if not state_db.exists():
        return []
    conn = sqlite3.connect(str(state_db))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    sess_dir = CORPUS_DIR / "conversations" / profile_name
    sess_dir.mkdir(parents=True, exist_ok=True)

    files = []
    cur.execute("SELECT id, source, user_id, chat_id, display_name FROM sessions")
    sessions = {r["id"]: r for r in cur.fetchall()}

    for session_id, sess in sessions.items():
        cur.execute(
            "SELECT role, content, tool_call_id, id FROM messages WHERE session_id=? ORDER BY id",
            (session_id,),
        )
        msgs = cur.fetchall()
        if not msgs:
            continue

        lines = [
            "---",
            f'source: "hermes/state.db"',
            f"profile: {profile_name}",
            f"session_id: {session_id}",
            f'chat_source: "{sess["source"]}"',
            f"exported_at: {TIMESTAMP}",
            "---",
            "",
            f"# Session: {sess['display_name'] or session_id}",
            f"Source: {sess['source']} | Date: {TIMESTAMP}",
            "",
        ]
        for m in msgs:
            role = m["role"]
            content = m["content"] or ""
            if role == "user":
                lines.append(f"## User\n\n{content}\n")
            elif role == "assistant":
                lines.append(f"## Assistant\n\n{content}\n")
            elif role == "tool":
                lines.append(
                    f"## Tool Call ({m['tool_call_id'] or 'unknown'})\n\n{content}\n"
                )
            else:
                lines.append(f"## {role.capitalize()}\n\n{content}\n")

        filepath = sess_dir / f"{session_id}.md"
        filepath.write_text("\n".join(lines), encoding="utf-8")
        files.append(filepath)

    conn.close()
    return files


def export_memories(memories_dir: Path, profile_name: str) -> list[Path]:
    """Copy memory files to corpus with frontmatter."""
    if not memories_dir.exists():
        return []
    mem_dir = CORPUS_DIR / "memories" / profile_name
    mem_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for fname in ["MEMORY.md", "USER.md"]:
        src = memories_dir / fname
        if not src.exists():
            continue
        dst = mem_dir / fname
        content = src.read_text(encoding="utf-8")
        if not content.strip().startswith("---"):
            content = (
                "---\n"
                f'source: "hermes/memories/{fname}"\n'
                f"profile: {profile_name}\n"
                f"exported_at: {TIMESTAMP}\n"
                "---\n\n"
                + content
            )
        dst.write_text(content, encoding="utf-8")
        files.append(dst)
    return files


def export_config(profile_path: Path, profile_name: str) -> list[Path]:
    """Export profile config and SOUL to corpus."""
    cfg_dir = CORPUS_DIR / "configs" / profile_name
    cfg_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for fname in ["config.yaml", "SOUL.md", "channel_directory.json"]:
        src = profile_path / fname
        if not src.exists():
            continue
        dst = cfg_dir / fname
        content = src.read_text(encoding="utf-8")
        if not content.strip().startswith("---"):
            content = (
                "---\n"
                f'source: "hermes/{fname}"\n'
                f"profile: {profile_name}\n"
                f"exported_at: {TIMESTAMP}\n"
                "---\n\n"
                + content
            )
        dst.write_text(content, encoding="utf-8")
        files.append(dst)
    return files


def main():
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)

    total = []

    # Default profile
    print("Exporting profile: default")
    total += export_messages(HERMES_HOME / "state.db", "default")
    total += export_memories(HERMES_HOME / "memories", "default")
    total += export_config(HERMES_HOME, "default")

    # Aira profile
    aira_path = HERMES_HOME / "profiles" / "aira"
    if aira_path.exists():
        print("Exporting profile: aira")
        total += export_messages(aira_path / "state.db", "aira")
        total += export_memories(aira_path / "memories", "aira")
        total += export_config(aira_path, "aira")

    print(f"Exported {len(total)} files to {CORPUS_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
