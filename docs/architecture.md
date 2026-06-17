# Scalable Distributed Architecture for Sentiment Analysis System

## Phase 1: System Analysis

### End-to-End Business Logic & Core Workflows
- **Purpose:** The system processes audio or text grievances, analyzes them for sentiment, emotion, urgency, and category, and stores structured results for analytics and resolution.
- **Workflow:**
  1. **Audio Input:** User uploads audio (or submits text).
  2. **Transcription:** Audio is transcribed using an omnilingual ASR model.
  3. **Language Detection:** The transcript’s language is detected.
  4. **Translation:** If not English, the transcript is translated to English.
  5. **NLP Analysis:** Sentiment, emotion, and grievance category are determined using HuggingFace models.
  6. **Urgency Derivation:** Urgency is mapped from emotion.
  7. **Persistence:** All results are stored in PostgreSQL.
  8. **APIs:** Expose endpoints for analysis, CRUD, and analytics.

### Data Flow Between Components
- **API Layer:** Receives requests, authenticates via API key, and routes to service layer.
- **Service Layer:** Orchestrates the pipeline (transcription → language detection → translation → NLP → DB).
- **Model Layer:** Defines request/response schemas and ORM models.
- **Database Layer:** Handles persistence using SQLAlchemy and PostgreSQL.
- **External Dependencies:** HuggingFace models, OpenAI/Ollama for translation, ffmpeg for audio conversion.

### Current Architecture Style
- **Type:** Modular monolith (single FastAPI app, modularized by responsibility).
- **Patterns:** Synchronous API endpoints, orchestrated pipeline, direct DB access, in-process model inference.

### Internal Dependencies & Module Structure
- **Routers:** `analysis.py` (audio pipeline), `grievance.py` (CRUD/analytics)
- **Services:** `pipeline.py` (orchestrator), `sentiment.py`, `category.py`, `language.py`, `translation.py`, `audio.py`
- **DB:** `models.py` (ORM), `database.py` (session/engine)
- **Config:** Centralized via Pydantic settings.
- **Auth:** API key model and dependency.

### Bottlenecks, Failure Points, Scalability Constraints
- **Model Inference:** All NLP/ASR runs in-process; not horizontally scalable.
- **Database:** Single PostgreSQL instance; no sharding or replication.
- **API Server:** Single FastAPI process; limited by Python GIL and process count.
- **No Message Queue:** All processing is synchronous; no async/event-driven decoupling.
- **File Handling:** Temp files for audio; potential I/O bottleneck.
- **No Caching:** Model results and translations are recomputed each time.
- **Observability:** Basic logging only; no distributed tracing or metrics.
- **Fault Tolerance:** Minimal; failures in any pipeline step return errors to the client.

---

## Phase 2: System Explanation (Non-Technical)

- **What the System Does:**  
  The system lets users submit audio or text describing a problem. It automatically converts speech to text, figures out the language, translates it to English if needed, and uses AI to determine the mood (sentiment), emotion, urgency, and type of problem. All this information is saved for later review and analysis.

- **Core Components:**
  - **API Gateway:** Receives and authenticates requests.
  - **Audio Processor:** Converts speech to text.
  - **Language Detector & Translator:** Identifies language and translates to English.
  - **NLP Analyzer:** Determines sentiment, emotion, urgency, and category.
  - **Database:** Stores all results and metadata.
  - **Admin/Analytics APIs:** Allow querying and aggregating stored data.

- **Current Architecture:**  
  Everything runs as one application, with different parts (modules) handling different tasks. All processing happens in the same process, and results are stored in a single database.

- **Data Flow:**  
  User input → API → Audio/NLP pipeline → Database → Analytics/CRUD APIs

- **Key Constraints:**
  - Can’t easily scale to handle many requests at once.
  - If one part fails (e.g., model loading), the whole request fails.
  - All processing is synchronous and blocking.
  - No event-driven or distributed processing.

---

## Phase 3: Proposed Scalable Architecture

### A. Microservices Breakdown

| Service Name         | Responsibility & Boundaries                                                                 | Dependencies                |
|----------------------|--------------------------------------------------------------------------------------------|-----------------------------|
| **API Gateway**      | Authenticates, validates, and routes requests.                                             | All downstream services     |
| **Audio Service**    | Handles audio file uploads, conversion, and ASR transcription.                            | Storage, ASR Model Service  |
| **ASR Model Service**| Runs speech-to-text models (can be scaled independently).                                 | Model cache, storage        |
| **Language Service** | Detects language of text.                                                                 | -                           |
| **Translation Service** | Translates text to English using LLMs or external APIs.                                | LLM API, cache              |
| **NLP Service**      | Runs sentiment, emotion, and category models.                                             | Model cache                 |
| **Urgency Service**  | Maps emotion to urgency.                                                                  | -                           |
| **Persistence Service** | Handles all DB writes/reads, enforces schema, and exposes CRUD/analytics APIs.         | PostgreSQL, cache           |
| **Analytics Service**| Aggregates and serves analytics data.                                                     | Persistence Service         |
| **Auth Service**     | Manages API keys and authentication.                                                      | Persistence Service         |

- **Why:** Each service can scale independently, be deployed separately, and fail without affecting the whole system.

---

### B. Messaging Layer (RabbitMQ / Event System)

- **Exchange Types:**  
  - **Topic Exchange:** For routing events by type (e.g., `audio.uploaded`, `transcription.completed`).
  - **Direct Exchange:** For targeted service-to-service communication.
- **Queue Design:**  
  - `audio_upload_queue`, `transcription_queue`, `nlp_queue`, `db_write_queue`, `analytics_queue`
- **Naming Strategy:**  
  - Use clear, domain-based names: `service.event_type` (e.g., `audio.transcribed`)
- **Routing Keys:**  
  - Use event type and entity: `audio.uploaded`, `text.translated`, `nlp.analyzed`
- **DLQ Design:**  
  - Each queue has a corresponding DLQ (e.g., `nlp_queue.dlq`) for failed messages.
- **Retry/Backoff:**  
  - Exponential backoff for retries; max retry count before moving to DLQ.

---

### C. Infrastructure Components

- **Dockerization:**  
  - Each service in its own Docker image.  
  - Shared base images for Python services.  
  - Model weights mounted via volumes or pulled at startup.

- **Redis Usage:**  
  - **Cache:** Store recent translations, model results, and session data.
  - **Queue (optional):** For lightweight background jobs.
  - **Rate Limiting:** API Gateway enforces per-user limits.

- **Database:**  
  - **PostgreSQL:**  
    - **Replication:** Read replicas for analytics/queries.
    - **Sharding:** By beneficiary or region if needed.
    - **Indexing:** On `beneficiary_id`, `created_at`, `category`.
    - **Read/Write Split:** Writes go to primary, reads to replicas.

- **Kafka vs. RabbitMQ:**  
  - **RabbitMQ** is preferred for workflow/event-driven processing (easier routing, DLQ, retries).
  - **Kafka** is better for high-throughput, immutable event logs and analytics.
  - **Recommendation:** Start with RabbitMQ for workflow orchestration; add Kafka for analytics/event sourcing if needed.

---

### D. Scalability & Reliability

- **Horizontal Scaling:**  
  - Each service can be scaled independently (e.g., more ASR workers for audio-heavy loads).
- **Load Balancing:**  
  - API Gateway and service endpoints behind load balancers (e.g., NGINX, Kubernetes Service).
- **Fault Tolerance:**  
  - DLQs for failed events, health checks, circuit breakers.
- **Backpressure:**  
  - Queue length monitoring, auto-scaling workers, reject new requests if overloaded.
- **Idempotency:**  
  - Use unique request IDs; services check for duplicates before processing.

---

### E. Observability

- **Logging:**  
  - Structured logs (JSON), centralized (e.g., ELK stack), log all requests, errors, and key events.
- **Metrics:**  
  - Prometheus metrics for request counts, latency, error rates, queue lengths.
- **Tracing:**  
  - Distributed tracing (OpenTelemetry/Jaeger) across all services and message flows.

---

### F. Deployment Strategy

- **Docker Compose:**  
  - For local dev: Compose file spins up all services, RabbitMQ, Redis, PostgreSQL.
- **Kubernetes:**  
  - Each service as a Deployment, with Service and HPA (Horizontal Pod Autoscaler).
  - RabbitMQ/Redis/PostgreSQL as StatefulSets.
  - ConfigMaps/Secrets for environment/config.
  - Ingress for API Gateway.

---

## Phase 4: Architecture Diagram (Text-Based)

```
+-------------------+      +-------------------+      +-------------------+
|    API Gateway    | ---> |   Auth Service    | ---> | Persistence Svc   |
+-------------------+      +-------------------+      +-------------------+
         |                        |                           |
         v                        |                           v
+-------------------+      +-------------------+      +-------------------+
|   Audio Service   | ---> | ASR Model Svc     | ---> | Language Svc      |
+-------------------+      +-------------------+      +-------------------+
         |                        |                           |
         v                        v                           v
+-------------------+      +-------------------+      +-------------------+
| Translation Svc   | ---> |   NLP Service     | ---> | Urgency Svc       |
+-------------------+      +-------------------+      +-------------------+
         |                        |                           |
         +------------------------+---------------------------+
                                  |
                                  v
                          +-------------------+
                          |   Message Broker  |
                          +-------------------+
                                  |
                                  v
                          +-------------------+
                          |   Analytics Svc   |
                          +-------------------+
                                  |
                                  v
                          +-------------------+
                          |   PostgreSQL DB   |
                          +-------------------+
                                  |
                                  v
                          +-------------------+
                          |   Redis Cache     |
                          +-------------------+
```

---

## Phase 5: Event Flow Example: "Audio Grievance Submission"

1. **User uploads audio via API Gateway.**
   - API Gateway authenticates and stores file in object storage.
   - Event: `audio.uploaded` sent to `audio_upload_queue`.

2. **Audio Service picks up event, converts audio if needed.**
   - Event: `audio.converted` sent to `transcription_queue`.

3. **ASR Model Service transcribes audio.**
   - Event: `transcription.completed` sent to `nlp_queue`.

4. **Language Service detects language.**
   - If not English, Translation Service translates transcript.
   - Event: `text.translated` sent to `nlp_queue`.

5. **NLP Service analyzes sentiment, emotion, category.**
   - Event: `nlp.analyzed` sent to `db_write_queue`.

6. **Urgency Service maps emotion to urgency.**
   - Event: `urgency.derived` sent to `db_write_queue`.

7. **Persistence Service writes all results to PostgreSQL.**
   - Event: `grievance.stored` sent to `analytics_queue`.

8. **Analytics Service updates aggregates.**
   - Event: `analytics.updated`.

**Failure Handling:**
- If any service fails, the message is retried (with backoff).
- After max retries, message goes to DLQ for manual review.
- Idempotency keys prevent duplicate processing.

---

## Assumptions
- System must handle millions of events per day.
- All model inference is containerized and horizontally scalable.
- Object storage (e.g., S3) is used for audio files in production.
- All services communicate via message broker, not direct calls.
- Security, observability, and reliability are first-class concerns.

---

**This documentation is designed to guide backend engineers and architects in implementing a robust, scalable, and observable distributed system for high-volume audio/text sentiment analysis and grievance management.**  