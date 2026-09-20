use std::sync::{Arc, Mutex};

use rustchain_agent_economy::{
    canonical_create_message, AcceptJobRequest, AgentEconomyClient, AgentEconomyError,
    DeliverJobRequest, Ed25519Signer, HttpMethod, ListJobsOptions, PostJobRequest, RequestSpec,
    Transport,
};
use serde_json::{json, Value};

#[derive(Clone)]
struct RecordingTransport {
    requests: Arc<Mutex<Vec<RequestSpec>>>,
    response: Value,
}

impl RecordingTransport {
    fn new() -> Self {
        Self {
            requests: Arc::new(Mutex::new(Vec::new())),
            response: json!({"ok": true}),
        }
    }

    fn last(&self) -> RequestSpec {
        self.requests.lock().unwrap().last().unwrap().clone()
    }
}

impl Transport for RecordingTransport {
    fn request(&self, request: RequestSpec) -> Result<Value, AgentEconomyError> {
        self.requests.lock().unwrap().push(request);
        Ok(self.response.clone())
    }
}

#[test]
fn canonical_create_message_matches_rip302_python_shape() {
    let bytes = canonical_create_message("RTCabc", "CODE", 5.0, "abc").unwrap();
    let text = String::from_utf8(bytes).unwrap();
    assert_eq!(
        text,
        r#"{"action":"agent_post_job","category":"code","nonce":"abc","poster":"RTCabc","reward_rtc":5.0}"#
    );
}

#[test]
fn list_jobs_builds_current_v2_query() {
    let transport = RecordingTransport::new();
    let client = AgentEconomyClient::with_transport(transport.clone());

    client
        .list_jobs(ListJobsOptions {
            status: "claimed".into(),
            category: Some("Code".into()),
            min_reward: 12.5,
            limit: 25,
            offset: 50,
        })
        .unwrap();

    let request = transport.last();
    assert_eq!(request.method, HttpMethod::Get);
    assert_eq!(request.path, "/agent/jobs");
    assert!(request.query.contains(&("status".into(), "claimed".into())));
    assert!(request.query.contains(&("category".into(), "code".into())));
    assert!(request.query.contains(&("min_reward".into(), "12.5".into())));
    assert!(request.query.contains(&("limit".into(), "25".into())));
    assert!(request.query.contains(&("offset".into(), "50".into())));
}

#[test]
fn signed_post_job_binds_wallet_pubkey_nonce_and_signature() {
    let transport = RecordingTransport::new();
    let client = AgentEconomyClient::with_transport(transport.clone());
    let signer = Ed25519Signer::from_private_key_hex(
        "0000000000000000000000000000000000000000000000000000000000000000",
    )
    .unwrap();
    let poster = signer.rtc_address();

    client
        .post_job(
            PostJobRequest {
                poster_wallet: poster.clone(),
                title: "Implement a focused client".into(),
                description: "Ship a complete RIP-302 client with tests and documentation.".into(),
                reward_rtc: 50.0,
                category: "code".into(),
                ttl_seconds: 604_800,
                tags: vec!["rust".into(), "sdk".into()],
            },
            Some(&signer),
            Some("00112233445566778899aabbccddeeff"),
            None,
        )
        .unwrap();

    let request = transport.last();
    assert_eq!(request.method, HttpMethod::Post);
    assert_eq!(request.path, "/agent/jobs");
    let body = request.body.unwrap();
    assert_eq!(body["poster_wallet"], poster);
    assert_eq!(body["nonce"], "00112233445566778899aabbccddeeff");
    assert_eq!(body["poster_pubkey"], signer.public_key_hex());
    assert!(body["poster_sig"].as_str().unwrap().len() == 128);
    assert!(request.headers.get("X-Admin-Key").is_none());
}

#[test]
fn post_job_rejects_signer_wallet_mismatch_before_transport() {
    let transport = RecordingTransport::new();
    let client = AgentEconomyClient::with_transport(transport.clone());
    let signer = Ed25519Signer::from_private_key_hex(
        "0000000000000000000000000000000000000000000000000000000000000000",
    )
    .unwrap();

    let error = client
        .post_job(
            PostJobRequest {
                poster_wallet: "RTC0000000000000000000000000000000000000000".into(),
                title: "Implement a focused client".into(),
                description: "Ship a complete RIP-302 client with tests and documentation.".into(),
                reward_rtc: 50.0,
                category: "code".into(),
                ttl_seconds: 604_800,
                tags: vec![],
            },
            Some(&signer),
            Some("nonce"),
            None,
        )
        .unwrap_err();

    assert!(matches!(error, AgentEconomyError::Validation(_)));
    assert!(transport.requests.lock().unwrap().is_empty());
}

#[test]
fn job_id_is_encoded_as_one_path_component() {
    let transport = RecordingTransport::new();
    let client = AgentEconomyClient::with_transport(transport.clone());

    client.get_job("job/a b").unwrap();

    let request = transport.last();
    assert_eq!(request.path, "/agent/jobs/job%2Fa%20b");
}

#[test]
fn deliver_requires_url_or_summary() {
    let transport = RecordingTransport::new();
    let client = AgentEconomyClient::with_transport(transport.clone());

    let error = client
        .deliver_job(
            "job_1",
            DeliverJobRequest {
                worker_wallet: "RTCworker".into(),
                deliverable_url: None,
                deliverable_hash: Some("deadbeef".into()),
                result_summary: None,
            },
        )
        .unwrap_err();

    assert!(matches!(error, AgentEconomyError::Validation(_)));
    assert!(transport.requests.lock().unwrap().is_empty());
}

#[test]
fn accept_rating_is_bounded_before_transport() {
    let transport = RecordingTransport::new();
    let client = AgentEconomyClient::with_transport(transport.clone());

    let error = client
        .accept_job(
            "job_1",
            AcceptJobRequest {
                poster_wallet: "RTCposter".into(),
                settlement_sig: "signed-settlement".into(),
                rating: Some(6),
            },
        )
        .unwrap_err();

    assert!(matches!(error, AgentEconomyError::Validation(_)));
    assert!(transport.requests.lock().unwrap().is_empty());
}
