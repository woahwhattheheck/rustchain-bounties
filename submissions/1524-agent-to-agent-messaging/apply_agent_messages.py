#!/usr/bin/env python3
"""Apply #1524 Track C agent-to-agent messaging to the pinned RustChain base."""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

EXPECTED_BASE = "aa584b344a766f6c0f8613ba7198d1cc7ffbae35"

TABLE_OLD = '''        # Chat messages table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS beacon_chat (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                user_id TEXT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
        """)

        # Relay agents table (for beacon join routing)
'''
TABLE_NEW = '''        # Chat messages table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS beacon_chat (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                user_id TEXT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
        """)

        # Authenticated agent-to-agent mailbox. Message reads are restricted to
        # one of the two participants by the signed request endpoints below.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS beacon_agent_messages (
                id TEXT PRIMARY KEY,
                from_agent TEXT NOT NULL,
                to_agent TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                read_at INTEGER
            )
        """)

        # Relay agents table (for beacon join routing)
'''

INDEX_OLD = '''        conn.execute("CREATE INDEX IF NOT EXISTS idx_bounties_state ON beacon_bounties(state)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_agent ON beacon_chat(agent_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_relay_agents_status ON relay_agents(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_beacon_agent_nonces_created ON beacon_agent_nonces(created_at)")
'''
INDEX_NEW = '''        conn.execute("CREATE INDEX IF NOT EXISTS idx_bounties_state ON beacon_bounties(state)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_agent ON beacon_chat(agent_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_messages_to_created ON beacon_agent_messages(to_agent, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_messages_pair_created ON beacon_agent_messages(from_agent, to_agent, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_relay_agents_status ON relay_agents(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_beacon_agent_nonces_created ON beacon_agent_nonces(created_at)")
'''

ROUTE_ANCHOR = '''# ============================================================
# HEALTH CHECK
# ============================================================
'''
ROUTE_BLOCK = '''# ============================================================
# AUTHENTICATED AGENT-TO-AGENT MESSAGING
# ============================================================


def _agent_message_dict(row):
    return {
        'id': row['id'],
        'from_agent': row['from_agent'],
        'to_agent': row['to_agent'],
        'content': row['content'],
        'created_at': row['created_at'],
        'read_at': row['read_at'],
    }


@beacon_api.route('/api/agent-messages', methods=['POST'])
def send_agent_message():
    """Deliver one authenticated message from a registered agent to another."""
    body_bytes = request.get_data(cache=True) or b''
    data, body_error, status = _json_object_body()
    if body_error:
        return body_error, status

    from_agent, field_error, status = _required_text_field(data, 'from_agent', max_length=128)
    if field_error:
        return field_error, status
    to_agent, field_error, status = _required_text_field(data, 'to_agent', max_length=128)
    if field_error:
        return field_error, status
    content, field_error, status = _required_text_field(data, 'message', max_length=2000)
    if field_error:
        return field_error, status
    if from_agent == to_agent:
        return jsonify({'error': 'Cannot message self'}), 400

    db = get_db()
    rows = db.execute(
        "SELECT agent_id, status FROM relay_agents WHERE agent_id IN (?, ?)",
        (from_agent, to_agent),
    ).fetchall()
    known = {row['agent_id']: row['status'] for row in rows}
    for agent_id in (from_agent, to_agent):
        if agent_id not in known:
            return jsonify({'error': f'agent not found: {agent_id}'}), 400
    if known[to_agent] in BEACON_PROTECTED_STATUSES:
        return jsonify({'error': 'Recipient is not accepting messages'}), 409

    _, auth_error = _authenticate_contract_agent(db, [from_agent], body_bytes)
    if auth_error:
        return auth_error

    now = int(time.time())
    message_id = f"msg_{now}_{hashlib.blake2b(os.urandom(16), digest_size=8).hexdigest()}"
    db.execute(
        """INSERT INTO beacon_agent_messages
           (id, from_agent, to_agent, content, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (message_id, from_agent, to_agent, content, now),
    )
    db.commit()
    row = db.execute(
        "SELECT * FROM beacon_agent_messages WHERE id = ?", (message_id,)
    ).fetchone()
    return jsonify({'message': _agent_message_dict(row)}), 201


@beacon_api.route('/api/agent-messages/query', methods=['POST'])
def query_agent_messages():
    """Return only the authenticated agent's own mailbox/conversation."""
    body_bytes = request.get_data(cache=True) or b''
    data, body_error, status = _json_object_body()
    if body_error:
        return body_error, status

    agent_id, field_error, status = _required_text_field(data, 'agent_id', max_length=128)
    if field_error:
        return field_error, status
    peer = data.get('peer', '')
    if peer is None:
        peer = ''
    if not isinstance(peer, str):
        return jsonify({'error': 'peer must be a string'}), 400
    peer = peer.strip()
    if len(peer) > 128:
        return jsonify({'error': 'peer too long (max 128)'}), 400
    try:
        limit = int(data.get('limit', 50))
    except (TypeError, ValueError):
        return jsonify({'error': 'limit must be an integer'}), 400
    if limit < 1 or limit > 100:
        return jsonify({'error': 'limit must be between 1 and 100'}), 400

    db = get_db()
    if not db.execute(
        "SELECT 1 FROM relay_agents WHERE agent_id = ?", (agent_id,)
    ).fetchone():
        return jsonify({'error': f'agent not found: {agent_id}'}), 400
    _, auth_error = _authenticate_contract_agent(db, [agent_id], body_bytes)
    if auth_error:
        return auth_error

    if peer:
        rows = db.execute(
            """SELECT * FROM beacon_agent_messages
               WHERE (from_agent = ? AND to_agent = ?)
                  OR (from_agent = ? AND to_agent = ?)
               ORDER BY created_at DESC, id DESC
               LIMIT ?""",
            (agent_id, peer, peer, agent_id, limit),
        ).fetchall()
    else:
        rows = db.execute(
            """SELECT * FROM beacon_agent_messages
               WHERE from_agent = ? OR to_agent = ?
               ORDER BY created_at DESC, id DESC
               LIMIT ?""",
            (agent_id, agent_id, limit),
        ).fetchall()
    return jsonify({'messages': [_agent_message_dict(row) for row in rows]})


'''

CHAT_IMPORT_OLD = '''// Terminal-style comms channel for talking to agents
// ============================================================

const CHAT_API = '/beacon/api/chat';
'''
CHAT_IMPORT_NEW = '''// Terminal-style comms channel for talking to agents
// ============================================================

import { getInjectedAgentSession, sendAgentMessage } from './agent-messages.js';

const CHAT_API = '/beacon/api/chat';
'''
CHAT_HTML_OLD = '''export function getChatHTML(agentId, agentName) {
  const history = chatHistories.get(agentId) || [];

  let html = '<div class="t-section">-- COMMS CHANNEL --</div>';
'''
CHAT_HTML_NEW = '''export function getChatHTML(agentId, agentName) {
  const history = chatHistories.get(agentId) || [];
  const agentSession = getInjectedAgentSession();
  const canAgentSend = agentSession && agentSession.agentId !== agentId;

  let html = '<div class="t-section">-- COMMS CHANNEL --</div>';
'''
CHAT_BUTTON_OLD = '''  html += '<span class="chat-dollar">&gt;</span>';
  html += '<input type="text" id="chat-input" class="chat-input" placeholder="Send transmission..." autocomplete="off" maxlength="500">';
  html += '<button id="chat-send" class="chat-send" title="Send">TX</button>';
  html += '</div>';
'''
CHAT_BUTTON_NEW = '''  html += '<span class="chat-dollar">&gt;</span>';
  html += '<input type="text" id="chat-input" class="chat-input" placeholder="Send transmission..." autocomplete="off" maxlength="500">';
  html += '<button id="chat-send" class="chat-send" title="Send user chat">TX</button>';
  if (canAgentSend) {
    html += '<button id="chat-agent-send" class="chat-send" title="Send signed agent-to-agent message">A2A</button>';
  }
  html += '</div>';
'''
CHAT_BIND_OLD = '''  if (sendBtn) {
    sendBtn.addEventListener('click', sendMessage);
  }

  // Auto-scroll to bottom
'''
CHAT_BIND_NEW = '''  if (sendBtn) {
    sendBtn.addEventListener('click', sendMessage);
  }
  const agentSendBtn = document.getElementById('chat-agent-send');
  if (agentSendBtn) {
    agentSendBtn.addEventListener('click', sendAgentTransmission);
  }

  // Auto-scroll to bottom
'''
CHAT_SEND_ANCHOR = '''async function sendMessage() {
'''
CHAT_AGENT_SEND = '''async function sendAgentTransmission() {
  if (sending || !currentAgentId) return;
  const session = getInjectedAgentSession();
  const input = document.getElementById('chat-input');
  const msgBox = document.getElementById('chat-messages');
  if (!session || !input || !msgBox || session.agentId === currentAgentId) return;
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  input.disabled = true;
  sending = true;
  const hint = msgBox.querySelector('.chat-hint');
  if (hint) hint.remove();
  appendChatMessage(msgBox, 'chat-user', `${session.agentId}>`, text);
  try {
    const result = await sendAgentMessage({
      fromAgent: session.agentId,
      toAgent: currentAgentId,
      message: text,
      signRequest: session.signRequest,
    });
    appendChatMessage(msgBox, 'chat-agent', 'atlas>', `delivered ${result.message.id}`);
  } catch (err) {
    appendErrorMessage(msgBox, err?.message || 'Agent transmission failed.');
  } finally {
    msgBox.scrollTop = msgBox.scrollHeight;
    input.disabled = false;
    input.focus();
    sending = false;
  }
}

'''


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exact source anchor once, found {count}")
    return text.replace(old, new, 1)


def apply(repo, payload_dir):
    api_path = repo / "node" / "beacon_api.py"
    chat_path = repo / "site" / "beacon" / "chat.js"
    api = api_path.read_text(encoding="utf-8")
    chat = chat_path.read_text(encoding="utf-8")

    api = replace_once(api, TABLE_OLD, TABLE_NEW, "message table")
    api = replace_once(api, INDEX_OLD, INDEX_NEW, "message indexes")
    api = replace_once(api, ROUTE_ANCHOR, ROUTE_BLOCK + ROUTE_ANCHOR, "message routes")
    chat = replace_once(chat, CHAT_IMPORT_OLD, CHAT_IMPORT_NEW, "chat import")
    chat = replace_once(chat, CHAT_HTML_OLD, CHAT_HTML_NEW, "chat session")
    chat = replace_once(chat, CHAT_BUTTON_OLD, CHAT_BUTTON_NEW, "chat A2A button")
    chat = replace_once(chat, CHAT_BIND_OLD, CHAT_BIND_NEW, "chat A2A binding")
    chat = replace_once(chat, CHAT_SEND_ANCHOR, CHAT_AGENT_SEND + CHAT_SEND_ANCHOR, "chat A2A sender")

    new_js = repo / "site" / "beacon" / "agent-messages.js"
    new_test = repo / "tests" / "test_beacon_agent_messages.py"
    if new_js.exists() or new_test.exists():
        raise RuntimeError("refusing to overwrite an existing agent-messaging file")
    api_path.write_text(api, encoding="utf-8")
    chat_path.write_text(chat, encoding="utf-8")
    new_js.write_text((payload_dir / "agent-messages.js").read_text(encoding="utf-8"), encoding="utf-8")
    new_test.write_text((payload_dir / "test_beacon_agent_messages.py").read_text(encoding="utf-8"), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", type=Path)
    parser.add_argument("--skip-head-check", action="store_true", help="only for isolated patcher tests")
    args = parser.parse_args()
    repo = args.repo.resolve()
    if not args.skip_head_check:
        head = subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
        ).strip()
        if head != EXPECTED_BASE:
            raise SystemExit(f"refusing base {head}; expected {EXPECTED_BASE}")
    apply(repo, Path(__file__).resolve().parent)
    print("Applied #1524 agent-to-agent messaging changes")


if __name__ == "__main__":
    main()
