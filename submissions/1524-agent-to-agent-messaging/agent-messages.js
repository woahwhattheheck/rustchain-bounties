// Authenticated agent-to-agent messaging for Beacon Atlas.
//
// Atlas deliberately does not read or persist private keys. Callers provide a
// signRequest callback backed by their existing Beacon identity/session. The
// callback receives the exact request body that will be sent, so it can create
// the standard X-Agent-* signature headers used by Beacon contract writes.

export const AGENT_MESSAGE_SEND_PATH = '/beacon/api/agent-messages';
export const AGENT_MESSAGE_QUERY_PATH = '/beacon/api/agent-messages/query';

function requireSigner(signRequest) {
  if (typeof signRequest !== 'function') {
    throw new TypeError('A Beacon signRequest callback is required');
  }
}

async function signedPost(path, payload, signRequest, fetchImpl = fetch) {
  requireSigner(signRequest);
  const body = JSON.stringify(payload);
  const agentId = payload.from_agent || payload.agent_id;
  const authHeaders = await signRequest({
    method: 'POST',
    path,
    body,
    agentId,
  });
  if (!authHeaders || typeof authHeaders !== 'object') {
    throw new TypeError('signRequest must return Beacon authentication headers');
  }

  const response = await fetchImpl(path, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders,
    },
    body,
  });
  let data = {};
  try {
    data = await response.json();
  } catch (_) {
    // Preserve status below for non-JSON upstream errors.
  }
  if (!response.ok) {
    throw new Error(data.error || `Beacon message request failed (${response.status})`);
  }
  return data;
}

export function sendAgentMessage({ fromAgent, toAgent, message, signRequest, fetchImpl }) {
  return signedPost(
    AGENT_MESSAGE_SEND_PATH,
    { from_agent: fromAgent, to_agent: toAgent, message },
    signRequest,
    fetchImpl,
  );
}

export function loadAgentMessages({ agentId, peer = '', limit = 50, signRequest, fetchImpl }) {
  const payload = { agent_id: agentId, limit };
  if (peer) payload.peer = peer;
  return signedPost(AGENT_MESSAGE_QUERY_PATH, payload, signRequest, fetchImpl);
}

export function getInjectedAgentSession(root = globalThis) {
  const session = root?.beaconAgentSession;
  if (!session || typeof session.agentId !== 'string' || typeof session.signRequest !== 'function') {
    return null;
  }
  return session;
}
