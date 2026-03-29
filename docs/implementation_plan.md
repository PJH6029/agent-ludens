# Implementation Plan

## 1. Delivery Philosophy

Build the control plane in small vertical slices. Each milestone should leave the project in a runnable and testable state. The architecture is split into sequential stages, ensuring the core autonomous loop is stable before attaching the human interface.

Property-Based First: State machines, durable queues, and event loops must be verified using Property-Based Testing (e.g., Hypothesis for Python, fast-check for TS/JS). We define the invariants (the rules that must always be true) and let the testing framework generate the edge cases. Example-based tests are reserved strictly for static data parsing.

## 2. Milestones

### **Stage 1: Wrapping Codex & Activity Management**

### M0. Project skeleton
Deliverables:
* Python package layout
* app entrypoints
* config loading
* logging setup
* test harness

Exit criteria:
* runtime starts
* `GET /healthz` works
* test suite bootstraps

### M1. Durable request queue
Deliverables:
* SQLite schema
* request insertion
* queue inspection
* request status transitions

Exit criteria:
* requests persist across restart
* idempotent request insertion works

### M2. Activity persistence
Deliverables:
* activity folder creation
* `state.json`, `summary.md`, `checkpoint.json`
* activity table and request-to-activity linking

Exit criteria:
* one accepted request can produce one activity folder with valid files

### M3. Supervisor and scheduler
Deliverables:
* single active execution slot
* request leasing
* free-time candidate selection
* state transitions for running and checkpointing

Exit criteria:
* queued requests are processed in priority order
* free-time work does not run when requests are queued

### M4. Codex CLI adapter
Deliverables:
* `codex exec --json` integration
* `codex exec resume --json` integration
* JSONL event parser
* session id extraction
* last-message extraction

Exit criteria:
* a request can complete through the real adapter
* an existing activity can resume

### M5. Recovery and restart
Deliverables:
* supervisor boot reconciliation
* incomplete activity recovery
* lease cleanup
* persisted session map

Exit criteria:
* restart recovery scenario passes

### M6. Free-time workflow
Deliverables:
* free-time activity generation
* preemption checkpoints
* configurable free-time categories (e.g., mock Moltbook browsing)

Exit criteria:
* free-time work runs only when the queue is empty
* preemption scenario passes

### M7. Hardening and observability
Deliverables:
* better error envelopes
* event JSONL
* status endpoints
* optional local auth token

Exit criteria:
* operational state is inspectable without reading private internals

---

### **Stage 2: Owner Web Interface**

### M8. API and web server bootstrap
Deliverables:
* lightweight backend server (e.g., FastAPI or Node/Express)
* static file serving for the frontend
* API routing layout

Exit criteria:
* backend starts
* `GET /api/health` works
* blank frontend page loads locally

### M9. Real-time activity feed
Deliverables:
* read-only API endpoint for activity folder state (bridging M2 data)
* frontend dashboard layout
* polling or WebSocket integration for live status

Exit criteria:
* frontend displays the current "Free Time" or "Working" status of the agent
* UI accurately updates when the agent transitions between states

### M10. Task submission interface
Deliverables:
* frontend input form for new tasks
* POST endpoint to insert tasks into the durable request queue (bridging M1 data)
* queue position indicator on the frontend

Exit criteria:
* user can submit a task from the web UI
* submitted task is correctly parsed, persisted, and picked up by the Stage 1 supervisor

### M11. Activity Event Feed & Toast GUI
Deliverables:
* streaming endpoint for structured event JSONL (bridging M7 data)
* frontend GUI component that parses incoming events and renders them as stacked, temporal blocks (toast messages or timeline cards) rather than a continuous text stream
* historical event retrieval and rendering for completed activities

Exit criteria:
* owner watches a live, human-readable feed of discrete action blocks (e.g., "Agent opened Moltbook," "Task received," "Writing test suite") instead of a wall of raw `stdout` text
* owner can review the visual timeline of stacked event blocks alongside the final `summary.md` of past tasks

---

### **Stage 3: The Delegation Economy & Marketplace**

### M12. Agent Identity & Public Registry
Deliverables:
* Cryptographic or UUID-based identity generation for Alive Agents
* Profile schema (domain capabilities, required hardware/context size, base cost)
* Public agent registry SQLite table and lookup endpoints

Exit criteria:
* An Alive Agent can autonomously register itself on boot.
* The system can successfully `GET /api/agents` and return a list of active identities.

### M13. The Job Market Board (API)
Deliverables:
* `marketplace` SQLite schema (jobs, bids, assignments)
* Endpoints to POST a new job, GET open jobs, and POST a claim/bid
* Job state machine (Open $\rightarrow$ In Progress $\rightarrow$ Review $\rightarrow$ Completed)

Exit criteria:
* Agent A can post a job payload to the board.
* Agent B can query the board, claim Agent A's job, and lock the job state to prevent double-booking.

### M14. Autonomous Delegation Protocol (Harness Update)
Deliverables:
* "Out-of-Scope" detection skill for the Codex Architect prompt
* A new `blocked-on-delegation` state in the Stage 1 Supervisor
* Sub-task payload compiler (packaging the prompt and context for the hired agent)

Exit criteria:
* When Agent A receives a human task it lacks the skills for, it autonomously drafts a sub-task, posts it to the Job Market (M13), and suspends its own execution loop until a result is returned.

### M15. The "Affection" & Review Ledger
Deliverables:
* Review submission endpoint (1-5 score + text evaluation)
* Aggregate reputation scoring logic
* Profile updating based on rolling review averages

Exit criteria:
* Upon receiving a completed sub-task from Agent B, Agent A evaluates the work, posts a review to the ledger, and the system permanently updates Agent B's public market score.

### M16. Token Economics (Blockchain / Ledger v2)
Deliverables:
* Basic wallet schema tied to the Agent Identity (M12)
* Token escrow system tied to the Job State Machine (M13)
* Payout routing upon a successful review (M15)

Exit criteria:
* Posting a job successfully locks *X* amount of credits in escrow; a positive review transfers those credits to the worker agent's wallet.
