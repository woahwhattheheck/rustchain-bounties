use reqwest::{Client as HttpClient, Method, StatusCode};
use serde::{de::DeserializeOwned, Deserialize, Serialize};
use serde_json::Value;
use std::time::Duration;
use thiserror::Error;

const DEFAULT_BASE_URL: &str = "https://50.28.86.131";

#[derive(Debug, Error)]
pub enum Error {
    #[error("invalid base URL: {0}")]
    InvalidBaseUrl(String),
    #[error("HTTP transport error: {0}")]
    Transport(#[from] reqwest::Error),
    #[error("RustChain API returned HTTP {status}: {message}")]
    Api {
        status: StatusCode,
        message: String,
        body: Value,
    },
}

pub type Result<T> = std::result::Result<T, Error>;

#[derive(Debug, Clone)]
pub struct AgentEconomyClient {
    base_url: String,
    http: HttpClient,
}

impl AgentEconomyClient {
    pub fn new(base_url: impl Into<String>) -> Result<Self> {
        let base_url = normalize_base_url(base_url.into())?;
        let http = HttpClient::builder()
            .timeout(Duration::from_secs(30))
            .build()?;
        Ok(Self { base_url, http })
    }

    pub fn production() -> Result<Self> {
        Self::new(DEFAULT_BASE_URL)
    }

    pub fn base_url(&self) -> &str {
        &self.base_url
    }

    pub async fn post_job(&self, request: &PostJobRequest) -> Result<PostJobResponse> {
        self.request(Method::POST, "/agent/jobs", None, Some(request))
            .await
    }

    pub async fn list_jobs(&self, query: &ListJobsQuery) -> Result<JobListResponse> {
        let mut params = Vec::new();
        if let Some(value) = &query.category {
            params.push(("category", value.to_string()));
        }
        if let Some(value) = &query.status {
            params.push(("status", value.to_string()));
        }
        if let Some(value) = query.limit {
            params.push(("limit", value.to_string()));
        }
        if let Some(value) = query.offset {
            params.push(("offset", value.to_string()));
        }
        if let Some(value) = query.min_reward {
            params.push(("min_reward", value.to_string()));
        }
        self.request::<(), _>(Method::GET, "/agent/jobs", Some(&params), None)
            .await
    }

    pub async fn get_job(&self, job_id: &str) -> Result<JobDetailResponse> {
        let path = format!("/agent/jobs/{}", encode_segment(job_id));
        self.request::<(), _>(Method::GET, &path, None, None).await
    }

    pub async fn claim_job(&self, job_id: &str, worker_wallet: &str) -> Result<ClaimJobResponse> {
        let path = format!("/agent/jobs/{}/claim", encode_segment(job_id));
        self.request(
            Method::POST,
            &path,
            None,
            Some(&ClaimJobRequest { worker_wallet }),
        )
        .await
    }

    pub async fn deliver_job(
        &self,
        job_id: &str,
        request: &DeliverJobRequest<'_>,
    ) -> Result<ActionResponse> {
        let path = format!("/agent/jobs/{}/deliver", encode_segment(job_id));
        self.request(Method::POST, &path, None, Some(request)).await
    }

    pub async fn accept_delivery(
        &self,
        job_id: &str,
        poster_wallet: &str,
        rating: Option<u8>,
    ) -> Result<AcceptJobResponse> {
        let path = format!("/agent/jobs/{}/accept", encode_segment(job_id));
        self.request(
            Method::POST,
            &path,
            None,
            Some(&AcceptJobRequest {
                poster_wallet,
                rating,
            }),
        )
        .await
    }

    pub async fn dispute_job(
        &self,
        job_id: &str,
        poster_wallet: &str,
        reason: &str,
    ) -> Result<ActionResponse> {
        let path = format!("/agent/jobs/{}/dispute", encode_segment(job_id));
        self.request(
            Method::POST,
            &path,
            None,
            Some(&DisputeJobRequest {
                poster_wallet,
                reason,
            }),
        )
        .await
    }

    pub async fn cancel_job(&self, job_id: &str, poster_wallet: &str) -> Result<CancelJobResponse> {
        let path = format!("/agent/jobs/{}/cancel", encode_segment(job_id));
        self.request(
            Method::POST,
            &path,
            None,
            Some(&CancelJobRequest { poster_wallet }),
        )
        .await
    }

    pub async fn reputation(&self, wallet: &str) -> Result<ReputationResponse> {
        let path = format!("/agent/reputation/{}", encode_segment(wallet));
        self.request::<(), _>(Method::GET, &path, None, None).await
    }

    pub async fn stats(&self) -> Result<MarketplaceStatsResponse> {
        self.request::<(), _>(Method::GET, "/agent/stats", None, None)
            .await
    }

    async fn request<B, R>(
        &self,
        method: Method,
        path: &str,
        query: Option<&[(&str, String)]>,
        body: Option<&B>,
    ) -> Result<R>
    where
        B: Serialize + ?Sized,
        R: DeserializeOwned,
    {
        let url = format!("{}{}", self.base_url, path);
        let mut request = self.http.request(method, url);
        if let Some(query) = query {
            let pairs: Vec<(&str, &str)> = query
                .iter()
                .map(|(key, value)| (*key, value.as_str()))
                .collect();
            request = request.query(&pairs);
        }
        if let Some(body) = body {
            request = request.json(body);
        }

        let response = request.send().await?;
        let status = response.status();
        let bytes = response.bytes().await?;
        let value = if bytes.is_empty() {
            Value::Null
        } else {
            serde_json::from_slice::<Value>(&bytes).unwrap_or_else(|_| {
                Value::String(String::from_utf8_lossy(&bytes).into_owned())
            })
        };

        if !status.is_success() {
            let message = value
                .get("error")
                .and_then(Value::as_str)
                .or_else(|| value.get("message").and_then(Value::as_str))
                .unwrap_or("request failed")
                .to_string();
            return Err(Error::Api {
                status,
                message,
                body: value,
            });
        }

        serde_json::from_value(value).map_err(|error| Error::Api {
            status,
            message: format!("invalid JSON response: {error}"),
            body: Value::Null,
        })
    }
}

fn normalize_base_url(mut base_url: String) -> Result<String> {
    base_url = base_url.trim().trim_end_matches('/').to_string();
    if !(base_url.starts_with("http://") || base_url.starts_with("https://")) {
        return Err(Error::InvalidBaseUrl(base_url));
    }
    Ok(base_url)
}

fn encode_segment(value: &str) -> String {
    urlencoding::encode(value).into_owned()
}

#[derive(Debug, Clone, Serialize)]
pub struct PostJobRequest {
    pub poster_wallet: String,
    pub title: String,
    pub description: String,
    #[serde(default = "default_category")]
    pub category: String,
    pub reward_rtc: f64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub ttl_seconds: Option<u64>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub tags: Vec<String>,
}

fn default_category() -> String {
    "other".to_string()
}

#[derive(Debug, Clone, Default)]
pub struct ListJobsQuery {
    pub category: Option<String>,
    pub status: Option<String>,
    pub limit: Option<u32>,
    pub offset: Option<u32>,
    pub min_reward: Option<f64>,
}

#[derive(Debug, Serialize)]
struct ClaimJobRequest<'a> {
    worker_wallet: &'a str,
}

#[derive(Debug, Clone, Serialize)]
pub struct DeliverJobRequest<'a> {
    pub worker_wallet: &'a str,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub deliverable_url: Option<&'a str>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub deliverable_hash: Option<&'a str>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result_summary: Option<&'a str>,
}

#[derive(Debug, Serialize)]
struct AcceptJobRequest<'a> {
    poster_wallet: &'a str,
    #[serde(skip_serializing_if = "Option::is_none")]
    rating: Option<u8>,
}

#[derive(Debug, Serialize)]
struct DisputeJobRequest<'a> {
    poster_wallet: &'a str,
    reason: &'a str,
}

#[derive(Debug, Serialize)]
struct CancelJobRequest<'a> {
    poster_wallet: &'a str,
}

#[derive(Debug, Clone, Deserialize)]
pub struct PostJobResponse {
    pub ok: bool,
    pub job_id: String,
    pub status: String,
    pub poster_wallet: String,
    pub reward_rtc: f64,
    pub platform_fee_rtc: f64,
    pub escrow_total_rtc: f64,
    pub expires_at: i64,
    pub expires_in_hours: f64,
    pub message: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ClaimJobResponse {
    pub ok: bool,
    pub job_id: String,
    pub status: String,
    pub worker_wallet: String,
    pub reward_rtc: f64,
    pub expires_at: i64,
    pub message: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ActionResponse {
    pub ok: bool,
    pub job_id: String,
    pub status: String,
    pub message: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct AcceptJobResponse {
    pub ok: bool,
    pub job_id: String,
    pub status: String,
    pub worker_wallet: String,
    pub reward_paid_rtc: f64,
    pub platform_fee_rtc: f64,
    pub message: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct CancelJobResponse {
    pub ok: bool,
    pub job_id: String,
    pub status: String,
    #[serde(default)]
    pub refunded_rtc: Option<f64>,
    pub message: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct JobListResponse {
    #[serde(default)]
    pub jobs: Vec<Value>,
    #[serde(default)]
    pub total: Option<u64>,
    #[serde(flatten)]
    pub extra: serde_json::Map<String, Value>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct JobDetailResponse {
    #[serde(flatten)]
    pub data: serde_json::Map<String, Value>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ReputationResponse {
    #[serde(flatten)]
    pub data: serde_json::Map<String, Value>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct MarketplaceStatsResponse {
    #[serde(flatten)]
    pub data: serde_json::Map<String, Value>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalizes_base_url() {
        let client = AgentEconomyClient::new("https://example.invalid/").unwrap();
        assert_eq!(client.base_url(), "https://example.invalid");
    }

    #[test]
    fn rejects_non_http_base_url() {
        assert!(matches!(
            AgentEconomyClient::new("example.invalid"),
            Err(Error::InvalidBaseUrl(_))
        ));
    }

    #[test]
    fn encodes_path_segments() {
        assert_eq!(encode_segment("job/a b"), "job%2Fa%20b");
    }

    #[test]
    fn serializes_post_job_shape() {
        let request = PostJobRequest {
            poster_wallet: "RTCposter".into(),
            title: "Write a Rust client".into(),
            description: "Implement the full RIP-302 Agent Economy client surface.".into(),
            category: "code".into(),
            reward_rtc: 50.0,
            ttl_seconds: Some(86_400),
            tags: vec!["rust".into(), "sdk".into()],
        };
        let value = serde_json::to_value(request).unwrap();
        assert_eq!(value["poster_wallet"], "RTCposter");
        assert_eq!(value["reward_rtc"], 50.0);
        assert_eq!(value["ttl_seconds"], 86_400);
        assert_eq!(value["tags"][0], "rust");
    }
}
