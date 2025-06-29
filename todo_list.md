## TransferAI LLM Compiler Roadmap → Evals v1

### 1. Helper & Composer Layers (v1)
- [x] `agent/helper.py` – merge **≥2** tool outputs into a single summary JSON (canonical schema)
  - Input: `results: Dict[node_id, output]`
  - Output: `summary_json: str`
  - Keep tool-specific merger functions in `agent/helpers/<tool>.py` for clarity
- [x] `agent/composer.py` (extend)
  - [x] Add `compose_from_execution(question, results)` convenience wrapper
  - [x] CLI: `python -m agent.composer results.json --question "..."`
  - [x] Unit test with monkey-patched `llm_client.chat`

---

### 2. Critic + Retry (v1)
- [x] `agent/critic.py` – GPT-3.5 model that scores composer output 0-1
  - Prompt with quality checklist (see `agent/checker_prompt.xml`)
- [x] Retry wrapper: re-compose when score < 0.8 (see `agent/retry_composer.py`)
- [x] Unit tests: low-score mock triggers retry path

---

### 3. LangGraph Pipeline (v1)
- [x] Add `agent/graph_runner.py` using LangGraph (or own mini framework) with 5 nodes:
  1. planner
  2. executor (parallel disabled initially)
  3. helper
  4. composer
  5. critic
- [x] Conditional edge Planner→Critic (retry) based on score
- [x] Helper function `run_full(question)` returning markdown

---

### 4. Parallel Task Fetching Unit (v1.5)
- [x] Refactor `agent.executor` → async scheduler with `asyncio.gather`
  - Publish `TaskStarted` / `TaskFinished` events to in-proc bus
  - Guarantee DAG order w/ topological ready-queue
- [x] Add unit test proving nodes A/B/C run concurrently when deps satisfied

---

### 5. Iterative Re-Planner Loop (v2)
- [ ] `agent/joiner.py` – incremental aggregator (same logic as helper) but streaming
- [ ] `agent/replanner.py` – invoke planner again when joiner sets `needs_more_tasks`
- [ ] Extend graph to include Joiner→Planner feedback loop; exit when `more_tasks == false` **or** retry budget exhausted


---

### 6. Eval Harness (v1)
- [ ] Directory `eval/` with ≥10 real user prompts + gold markdown answers
- [ ] Script `make eval` →
  - Runs pipeline for each prompt
  - Computes precision/recall or simple F1 vs gold (use `rapidfuzz`) ignoring markdown formatting tokens
  - Produces leaderboard JSON
- [ ] GitHub Action: fail CI if score < 0.85

---

### 7. Documentation
- [ ] Update `README.md` with architecture diagram & quick-start commands
- [ ] Add ADR (Architecture Decision Record) for event-bus scheduler vs LangGraph rationale

---

### 8. Stretch Goals
- [ ] Replace in-proc event bus with Redis Streams for distributed workers
- [ ] Add embeddings cache service for vector tools
- [ ] Integrate `tenacity` for robust retries on transient tool errors
- [ ] Implement Streaming FastAPI endpoint for real-time SSE (was Step 6) 