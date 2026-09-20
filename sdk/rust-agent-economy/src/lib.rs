//! Rust client for the current RIP-302 v2 Agent Economy API.
//!
//! The client deliberately returns the complete JSON response object from wire
//! methods so new server metadata is not discarded. Typed response models are
//! also exported for callers that want to deserialize known fields.

use std::collections::BTreeMap;
use std::time::Duration;

use ed25519_dalek::{Signer, SigningKey};
use percent_encoding::{utf8_percent_encode, NON_ALPHANUMERIC};
use rand_core::{OsRng, RngCore};
use reqwest::blocking::Client as HttpClient;
use reqwest::Method;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use thiserror::Error;

pub const DEFAULT_BASE_URL: &str = "https://bulbous-bouffant.metalseed.net";
pub const AGENT_JOB_CATEGORIES: &[&str] = &[
    "research",
    "code",
    "video",
    "audio",
    "writing",
    "translation",
    "data",
    "design",
    "testing",
    "other",
];

#[derive(Debug, Error)]
pub enum AgentEconomyError {
    #[error("RIP-302 validation error: {0}")]
    Validation(String),

    #[error("RIP-302 transport error: {0}")]
    Transport(String),

    #[error("RIP-302 {path}: HTTP {status}: {message}")]
    Api {
        status: u16,
        path: String,
        code: Option<String>,
        error: Option<String>,
        body: Value,
        message: String,
    },

    #[error("RIP-302 crypto error: {0}")]
    Crypto(String),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HttpMethod {
    Get,
    Post,
}

#[derive(Debug, Clone, PartialEq)]
pub struct RequestSpec {
    pub method: HttpMethod,
    pub path: String,
    pub query: Vec<(String, String)>,
    pub body: Option<Value>,
    pub headers: BTreeMap<String, String>,
}

impl RequestSpec {
    fn get(path: impl Into<String>) -> Self {
        Self {
            method: HttpMethod::Get,
            path: path.into(),
            query: Vec::new(),
            body: None,
            headers: BTreeMap::new(),
        }
    }

    fn post(path: impl Into<String>, body: Value) -> Self {
        Self {
            method: HttpMethod::Post,
            path: path.into(),
            query: Vec::new(),
            body: Some(body),
            headers: BTreeMap::new(),
        }
    }
}

pub trait Transport: Send + Sync {
    fn request(&self, request: RequestSpec) -> Result<Value, AgentEconomyError>;
}

#[derive(Clone)]
pub struct ReqwestTransport {
    base_url: String,
    client: HttpClient,
}

impl ReqwestTransport {
    pub fn new(
        base_url: &str,
        timeout_seconds: f64,
        verify_tls: bool,
    ) -> Result<Self, AgentEconomyError> {
        let base_url = base_url.trim();
        if base_url.is_empty() {
            return Err(AgentEconomyError::Validation(
                "base_url must be a non-empty string".into(),
            ));
        }
        let parsed = reqwest::Url::parse(base_url)
            .map_err(|e| AgentEconomyError::Validation(format!("invalid base_url: {e}")))?;
        if !matches!(parsed.scheme(), "http" | "https") {
            return Err(AgentEconomyError::Validation(
                "base_url must use http or https".into(),
            ));
        }
        if !timeout_seconds.is_finite() || timeout_seconds <= 0.0 {
            return Err(AgentEconomyError::Validation(
                "timeout_seconds must be positive and finite".into(),
            ));
        }

        let client = HttpClient::builder()
            .timeout(Duration::from_secs_f64(timeout_seconds))
            .danger_accept_invalid_certs(!verify_tls)
            .user_agent("rustchain-agent-economy-rust/0.1.0")
            .build()
            .map_err(|e| AgentEconomyError::Transport(format!("client setup failed: {e}")))?;

        Ok(Self {
            base_url: base_url.trim_end_matches('/').to_string(),
            client,
        })
    }
}

impl Transport for ReqwestTransport {
    fn request(&self, request: RequestSpec) -> Result<Value, AgentEconomyError> {
        let url = format!("{}{}", self.base_url, request.path);
        let method = match request.method {
            HttpMethod::Get => Method::GET,
            HttpMethod::Post => Method::POST,
        };

        let mut builder = self.client.request(method, &url);
        if !request.query.is_empty() {
            builder = builder.query(&request.query);
        }
        for (name, value) in &request.headers {
            builder = builder.header(name, value);
        }
        if let Some(body) = &request.body {
            builder = builder.json(body);
        }

        let response = builder.send().map_err(|e| {
            AgentEconomyError::Transport(format!("{}: request failed: {e}", request.path))
        })?;
        let status = response.status();
        let text = response.text().map_err(|e| {
            AgentEconomyError::Transport(format!("{}: response read failed: {e}", request.path))
        })?;

        let body = if text.trim().is_empty() {
            json!({})
        } else {
            match serde_json::from_str::<Value>(&text) {
                Ok(value) => value,
                Err(e) if status.is_success() => {
                    return Err(AgentEconomyError::Transport(format!(
                        "{}: response was not valid JSON: {e}",
                        request.path
                    )));
                }
                Err(_) => json!({ "error": text }),
            }
        };

        if !status.is_success() {
            return Err(api_error(status.as_u16(), &request.path, body));
        }
        if !body.is_object() {
            return Err(AgentEconomyError::Transport(format!(
                "{}: expected a JSON object response",
                request.path
            )));
        }

        Ok(body)
    }
}

fn api_error(status: u16, path: &str, body: Value) -> AgentEconomyError {
    let code = body
        .get("code")
        .and_then(Value::as_str)
        .map(ToOwned::to_owned);
    let error = body
        .get("error")
        .and_then(Value::as_str)
        .map(ToOwned::to_owned);
    let message = match (&code, &error) {
        (Some(code), Some(error)) => format!("{code}: {error}"),
        (_, Some(error)) => error.clone(),
        _ => format!("HTTP {status}"),
    };

    AgentEconomyError::Api {
        status,
        path: path.to_string(),
        code,
        error,
        body,
        message,
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PostJobRequest {
    pub poster_wallet: String,
    pub title: String,
    pub description: String,
    pub reward_rtc: f64,
    #[serde(default = "default_category")]
    pub category: String,
    #[serde(default = "default_ttl_seconds")]
    pub ttl_seconds: u64,
    #[serde(default)]
    pub tags: Vec<String>,
}

fn default_category() -> String {
    "other".into()
}

const fn default_ttl_seconds() -> u64 {
    604_800
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct DeliverJobRequest {
    pub worker_wallet: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub deliverable_url: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub deliverable_hash: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result_summary: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct AcceptJobRequest {
    pub poster_wallet: String,
    pub settlement_sig: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub rating: Option<u8>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct DisputeJobRequest {
    pub poster_wallet: String,
    pub reason: String,
    pub settlement_sig: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CancelJobRequest {
    pub poster_wallet: String,
    pub settlement_sig: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default, PartialEq)]
pub struct Job {
    #[serde(default)]
    pub id: Option<String>,
    #[serde(default)]
    pub job_id: Option<String>,
    #[serde(default)]
    pub title: Option<String>,
    #[serde(default)]
    pub description: Option<String>,
    #[serde(default)]
    pub category: Option<String>,
    #[serde(default)]
    pub reward_rtc: Option<f64>,
    #[serde(default)]
    pub status: Option<String>,
    #[serde(default)]
    pub poster_wallet: Option<String>,
    #[serde(default)]
    pub worker_wallet: Option<String>,
    #[serde(default)]
    pub created_at: Option<Value>,
    #[serde(default)]
    pub updated_at: Option<Value>,
    #[serde(flatten)]
    pub extra: BTreeMap<String, Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default, PartialEq)]
pub struct AgentReputation {
    #[serde(default)]
    pub wallet: Option<String>,
    #[serde(default)]
    pub trust_score: Option<f64>,
    #[serde(default)]
    pub trust_level: Option<String>,
    #[serde(default)]
    pub avg_rating: Option<f64>,
    #[serde(default)]
    pub total_rtc_earned: Option<f64>,
    #[serde(flatten)]
    pub extra: BTreeMap<String, Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default, PartialEq)]
pub struct MarketplaceStats {
    #[serde(default)]
    pub total_jobs: Option<u64>,
    #[serde(default)]
    pub total_rtc_volume: Option<f64>,
    #[serde(default)]
    pub platform_fees: Option<f64>,
    #[serde(default)]
    pub active_agents: Option<u64>,
    #[serde(default)]
    pub escrow_balance: Option<f64>,
    #[serde(flatten)]
    pub extra: BTreeMap<String, Value>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct ListJobsOptions {
    pub status: String,
    pub category: Option<String>,
    pub min_reward: f64,
    pub limit: u16,
    pub offset: u64,
}

impl Default for ListJobsOptions {
    fn default() -> Self {
        Self {
            status: "open".into(),
            category: None,
            min_reward: 0.0,
            limit: 50,
            offset: 0,
        }
    }
}

pub struct Ed25519Signer {
    signing_key: SigningKey,
}

impl Ed25519Signer {
    pub fn from_private_key_hex(private_key_hex: &str) -> Result<Self, AgentEconomyError> {
        let raw = hex::decode(private_key_hex)
            .map_err(|_| AgentEconomyError::Crypto("private key must be hex".into()))?;
        let bytes: [u8; 32] = raw.try_into().map_err(|_| {
            AgentEconomyError::Crypto("Ed25519 private key must be exactly 32 bytes".into())
        })?;
        Ok(Self {
            signing_key: SigningKey::from_bytes(&bytes),
        })
    }

    pub fn public_key_bytes(&self) -> [u8; 32] {
        self.signing_key.verifying_key().to_bytes()
    }

    pub fn public_key_hex(&self) -> String {
        hex::encode(self.public_key_bytes())
    }

    pub fn rtc_address(&self) -> String {
        let digest = Sha256::digest(self.public_key_bytes());
        format!("RTC{}", hex::encode(&digest[..20]))
    }

    pub fn sign_create(
        &self,
        poster_wallet: &str,
        category: &str,
        reward_rtc: f64,
        nonce: &str,
    ) -> Result<String, AgentEconomyError> {
        let message = canonical_create_message(poster_wallet, category, reward_rtc, nonce)?;
        Ok(hex::encode(self.signing_key.sign(&message).to_bytes()))
    }
}

pub fn canonical_create_message(
    poster_wallet: &str,
    category: &str,
    reward_rtc: f64,
    nonce: &str,
) -> Result<Vec<u8>, AgentEconomyError> {
    let mut payload = BTreeMap::<&str, Value>::new();
    payload.insert("action", Value::String("agent_post_job".into()));
    payload.insert("category", Value::String(validate_category(category)?));
    payload.insert("nonce", Value::String(require_text(nonce, "nonce", 1)?));
    payload.insert(
        "poster",
        Value::String(require_text(poster_wallet, "poster_wallet", 1)?),
    );
    payload.insert("reward_rtc", json!(validate_reward(reward_rtc)?));

    serde_json::to_vec(&payload)
        .map_err(|e| AgentEconomyError::Transport(format!("canonical JSON failed: {e}")))
}

pub struct AgentEconomyClient<T = ReqwestTransport> {
    transport: T,
}

impl AgentEconomyClient<ReqwestTransport> {
    pub fn new(base_url: &str) -> Result<Self, AgentEconomyError> {
        Self::new_with_options(base_url, 30.0, true)
    }

    pub fn new_with_options(
        base_url: &str,
        timeout_seconds: f64,
        verify_tls: bool,
    ) -> Result<Self, AgentEconomyError> {
        Ok(Self {
            transport: ReqwestTransport::new(base_url, timeout_seconds, verify_tls)?,
        })
    }
}

impl<T: Transport> AgentEconomyClient<T> {
    pub fn with_transport(transport: T) -> Self {
        Self { transport }
    }

    pub fn list_jobs(&self, options: ListJobsOptions) -> Result<Value, AgentEconomyError> {
        if options.limit > 100 {
            return Err(AgentEconomyError::Validation(
                "limit must be from 0 to 100".into(),
            ));
        }
        if !options.min_reward.is_finite() || options.min_reward < 0.0 {
            return Err(AgentEconomyError::Validation(
                "min_reward must be non-negative and finite".into(),
            ));
        }

        let mut request = RequestSpec::get("/agent/jobs");
        request.query = vec![
            ("status".into(), require_text(&options.status, "status", 1)?),
            ("min_reward".into(), options.min_reward.to_string()),
            ("limit".into(), options.limit.to_string()),
            ("offset".into(), options.offset.to_string()),
        ];
        if let Some(category) = options.category {
            request
                .query
                .push(("category".into(), validate_category(&category)?));
        }
        self.transport.request(request)
    }

    pub fn get_job(&self, job_id: &str) -> Result<Value, AgentEconomyError> {
        self.transport
            .request(RequestSpec::get(job_path(job_id, None)?))
    }

    pub fn post_job(
        &self,
        mut request: PostJobRequest,
        signer: Option<&Ed25519Signer>,
        nonce: Option<&str>,
        admin_key: Option<&str>,
    ) -> Result<Value, AgentEconomyError> {
        request.poster_wallet = require_text(&request.poster_wallet, "poster_wallet", 1)?;
        request.title = require_text(&request.title, "title", 5)?;
        request.description = require_text(&request.description, "description", 20)?;
        request.category = validate_category(&request.category)?;
        request.reward_rtc = validate_reward(request.reward_rtc)?;
        if request.ttl_seconds == 0 {
            return Err(AgentEconomyError::Validation(
                "ttl_seconds must be positive".into(),
            ));
        }

        let mut body = serde_json::to_value(&request)
            .map_err(|e| AgentEconomyError::Transport(format!("request JSON failed: {e}")))?;

        let mut headers = BTreeMap::new();
        if let Some(signer) = signer {
            if request.poster_wallet.starts_with("RTC")
                && !signer
                    .rtc_address()
                    .eq_ignore_ascii_case(&request.poster_wallet)
            {
                return Err(AgentEconomyError::Validation(
                    "signer public key does not match poster_wallet RTC address".into(),
                ));
            }
            let nonce = match nonce {
                Some(value) => require_text(value, "nonce", 1)?,
                None => random_nonce(),
            };
            let sig = signer.sign_create(
                &request.poster_wallet,
                &request.category,
                request.reward_rtc,
                &nonce,
            )?;

            let object = body.as_object_mut().expect("serialized request is an object");
            object.insert("nonce".into(), Value::String(nonce));
            object.insert(
                "poster_pubkey".into(),
                Value::String(signer.public_key_hex()),
            );
            object.insert("poster_sig".into(), Value::String(sig));
        } else if let Some(admin_key) = admin_key {
            headers.insert(
                "X-Admin-Key".into(),
                require_text(admin_key, "admin_key", 1)?,
            );
        }

        let mut spec = RequestSpec::post("/agent/jobs", body);
        spec.headers = headers;
        self.transport.request(spec)
    }

    pub fn claim_job(
        &self,
        job_id: &str,
        worker_wallet: &str,
    ) -> Result<Value, AgentEconomyError> {
        let body = json!({
            "worker_wallet": require_text(worker_wallet, "worker_wallet", 1)?
        });
        self.transport
            .request(RequestSpec::post(job_path(job_id, Some("claim"))?, body))
    }

    pub fn deliver_job(
        &self,
        job_id: &str,
        mut request: DeliverJobRequest,
    ) -> Result<Value, AgentEconomyError> {
        if request.deliverable_url.is_none() && request.result_summary.is_none() {
            return Err(AgentEconomyError::Validation(
                "deliverable_url or result_summary is required".into(),
            ));
        }
        request.worker_wallet = require_text(&request.worker_wallet, "worker_wallet", 1)?;
        let body = serde_json::to_value(request)
            .map_err(|e| AgentEconomyError::Transport(format!("request JSON failed: {e}")))?;
        self.transport
            .request(RequestSpec::post(job_path(job_id, Some("deliver"))?, body))
    }

    pub fn accept_job(
        &self,
        job_id: &str,
        mut request: AcceptJobRequest,
    ) -> Result<Value, AgentEconomyError> {
        request.poster_wallet = require_text(&request.poster_wallet, "poster_wallet", 1)?;
        request.settlement_sig = require_text(&request.settlement_sig, "settlement_sig", 1)?;
        if let Some(rating) = request.rating {
            if !(1..=5).contains(&rating) {
                return Err(AgentEconomyError::Validation(
                    "rating must be from 1 to 5".into(),
                ));
            }
        }
        let body = serde_json::to_value(request)
            .map_err(|e| AgentEconomyError::Transport(format!("request JSON failed: {e}")))?;
        self.transport
            .request(RequestSpec::post(job_path(job_id, Some("accept"))?, body))
    }

    pub fn dispute_job(
        &self,
        job_id: &str,
        mut request: DisputeJobRequest,
    ) -> Result<Value, AgentEconomyError> {
        request.poster_wallet = require_text(&request.poster_wallet, "poster_wallet", 1)?;
        request.reason = require_text(&request.reason, "reason", 1)?;
        request.settlement_sig = require_text(&request.settlement_sig, "settlement_sig", 1)?;
        let body = serde_json::to_value(request)
            .map_err(|e| AgentEconomyError::Transport(format!("request JSON failed: {e}")))?;
        self.transport
            .request(RequestSpec::post(job_path(job_id, Some("dispute"))?, body))
    }

    pub fn cancel_job(
        &self,
        job_id: &str,
        mut request: CancelJobRequest,
    ) -> Result<Value, AgentEconomyError> {
        request.poster_wallet = require_text(&request.poster_wallet, "poster_wallet", 1)?;
        request.settlement_sig = require_text(&request.settlement_sig, "settlement_sig", 1)?;
        let body = serde_json::to_value(request)
            .map_err(|e| AgentEconomyError::Transport(format!("request JSON failed: {e}")))?;
        self.transport
            .request(RequestSpec::post(job_path(job_id, Some("cancel"))?, body))
    }

    pub fn get_reputation(&self, wallet_id: &str) -> Result<Value, AgentEconomyError> {
        let wallet = require_text(wallet_id, "wallet_id", 1)?;
        let encoded = utf8_percent_encode(&wallet, NON_ALPHANUMERIC);
        self.transport.request(RequestSpec::get(format!(
            "/agent/reputation/{encoded}"
        )))
    }

    pub fn get_stats(&self) -> Result<Value, AgentEconomyError> {
        self.transport.request(RequestSpec::get("/agent/stats"))
    }
}

fn require_text(value: &str, name: &str, min_len: usize) -> Result<String, AgentEconomyError> {
    let value = value.trim();
    if value.len() < min_len {
        return Err(AgentEconomyError::Validation(format!(
            "{name} must be at least {min_len} non-whitespace characters"
        )));
    }
    Ok(value.to_string())
}

fn validate_reward(value: f64) -> Result<f64, AgentEconomyError> {
    if !value.is_finite() || !(0.01..=10_000.0).contains(&value) {
        return Err(AgentEconomyError::Validation(
            "reward_rtc must be between 0.01 and 10000".into(),
        ));
    }
    Ok(value)
}

fn validate_category(category: &str) -> Result<String, AgentEconomyError> {
    let category = require_text(category, "category", 1)?.to_lowercase();
    if !AGENT_JOB_CATEGORIES.contains(&category.as_str()) {
        return Err(AgentEconomyError::Validation(format!(
            "category must be one of: {}",
            AGENT_JOB_CATEGORIES.join(", ")
        )));
    }
    Ok(category)
}

fn job_path(job_id: &str, action: Option<&str>) -> Result<String, AgentEconomyError> {
    let job_id = require_text(job_id, "job_id", 1)?;
    let encoded = utf8_percent_encode(&job_id, NON_ALPHANUMERIC);
    Ok(match action {
        Some(action) => format!("/agent/jobs/{encoded}/{action}"),
        None => format!("/agent/jobs/{encoded}"),
    })
}

fn random_nonce() -> String {
    let mut bytes = [0_u8; 16];
    OsRng.fill_bytes(&mut bytes);
    hex::encode(bytes)
}
