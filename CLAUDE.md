# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

The official **Neo4j pharmaceutical supply-chain demo** (see https://neo4j.com/developer/demos/supply_chain-demo). It is not a single app — it's four cooperating pieces around a Neo4j graph:

1. **Neo4j graph database** — the source of truth. A pharma supply-chain graph (suppliers → raw materials → APIs → drug products → distributors, plus the manufacturing layer: batches, equipment, process steps/stages, recipes). Schema lives in `model/` (`pharma_supply_chain-create_model.cypher`, `-model.json`, PNGs).
2. **`supply_chain_toolset/`** — a **FastAPI** HTTP service (`supply_chain_toolset.py`) that wraps complex Cypher queries as ~11 high-level tool endpoints returning JSON. Dockerized, intended for **Google Cloud Run**. This is the only long-running deployable service.
3. **`agent.yaml`** — a **Google ADK** (Agent Development Kit) agent config. Model is `litellm` → `openai/gpt-4.1`; its `toolset` points (over HTTP) at the FastAPI service's `/tools` discovery endpoint. The agent calls the toolset; it does not query Neo4j directly.
4. **`walkthrough/`** — Jupyter notebooks demonstrating the graph, the AI agent, and (planned) graph analytics. `src/dashboard-supplychain.json` is a NeoDash dashboard; `src/cypher_queries-saved.csv` are saved example queries.

The flow: **ADK agent (LLM) → HTTP → FastAPI toolset → Cypher → Neo4j**. The agent never sees Cypher or the schema; it discovers tools from `/tools` and calls them.

## Graph model essentials (needed to write/modify tools)

- **Products are multi-labelled.** A single node label set is `:Product:API:DIST:RM:FG:DP:BULK` — the material's role (raw material `RM`, active ingredient `API`, drug product `DP`, finished good `FG`, distribution unit `DIST`, `BULK`) is encoded as *additional labels* on `Product` nodes. Tools select by `description`/`globalBrand` plus the relevant label.
- **Core supply-chain relationships:** `(:Suppliers)-[:SUPPLIES_RM]->(:RM)`, `-[:PRODUCT_FLOW*]->` (the multi-hop transformation chain), `(:Product)-[:DISTRIBUTED_BY]->(:Distributor)`, `(:Product)-[:CONSUMES]->(:ProcessStep)`.
- **Manufacturing layer:** `Batch`, `Equipment`, `ProductionRun`, `ProcessStep`/`ProcessStage`, `Recipe`, `Employee`, linked via `BATCH_FLOW`, `USED_FOR_BATCH`, `IS_BATCH_FOR`, `PRODUCED_BATCH`, etc.
- **Queries depend on APOC** (`apoc.meta.data`, `apoc.coll.*` in `get_schema` and `logistics_optimization`). The target Neo4j must have APOC available (Neo4j Aura includes APOC core).

## Running locally

The toolset and the agent are separate processes; both need Neo4j credentials.

```bash
# 1. Neo4j credentials — copy a template and fill in (note: same vars used by both pieces)
cp scp.env.template .env        # NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, OPENAPI_KEY

# 2. Run the toolset (FastAPI) locally
cd supply_chain_toolset
pip install -r requirements.txt          # fastapi, uvicorn, neo4j, pydantic
uvicorn supply_chain_toolset:app --host 0.0.0.0 --port 8080
#   GET /tools   → tool catalogue;  GET /health → Neo4j connectivity check

# 3. Agent dependencies (repo root) — google-adk, litellm, langchain, neo4j, etc.
pip install -r requirements.txt
```

The agent is driven through Google ADK (`agent.yaml` is its config) and the `walkthrough/02_Walkthrough_with_AI_Agent.ipynb` notebook; point `agent.yaml`'s `toolset.connection_params.url` at your own toolset deployment's `/tools`.

There is **no test suite, linter, or build step** in this repo — the deliverables are the container image, the notebooks, and the Cypher/model files.

## Deploying the toolset

`supply_chain_toolset/push.sh` builds and deploys to **Google Cloud Run** (edit `PROJECT_ID` first; requires the `gcloud` CLI):

```bash
cd supply_chain_toolset
./push.sh        # gcloud builds submit → gcr.io/$PROJECT_ID/supply-chain-toolset → gcloud run deploy
```

Set `NEO4J_URI` / `NEO4J_USERNAME` / `NEO4J_PASSWORD` as Cloud Run env vars (see the commented `--set-env-vars` block in `push.sh`; Secret Manager is recommended).

## Gotchas

- **The `.backup` data file is NOT in the repo.** `dump/` contains only `.DS_Store` despite the README's "Option 1: it's in `dump/`". Get it from the Google Drive link in the root `README.md`, then import into Neo4j (see the Neo4j demo setup guide). `model/pharma_supply_chain-create_model.cypher` defines the schema only, not the data.
- **The Dockerfile hardcodes `--port 8080`**, which matches Cloud Run's default container-port contract. On platforms that inject a dynamic `$PORT` (Railway, Render, Fly), change the `CMD` to bind `$PORT` (e.g. `sh -c "uvicorn supply_chain_toolset:app --host 0.0.0.0 --port ${PORT:-8080}"`).
- **Env var naming is inconsistent.** The toolset reads `NEO4J_URI`/`NEO4J_USERNAME`/`NEO4J_PASSWORD` (the toolset README mistakenly calls it `NEO4J_USER`). The `.env` templates label the OpenAI key `OPENAPI_KEY` (looks like a typo for `OPENAI_API_KEY`/`OPENAI_KEY`) — verify what your agent runtime actually reads.
- **`agent.yaml` points at the demo's public Cloud Run instance** (`supply-chain-toolset-373589861902.us-central1.run.app`). Repoint it to your own deployment, otherwise you depend on Neo4j's shared demo backend.
- **`run_cypher` is an unrestricted query tool** exposed over HTTP with `--allow-unauthenticated` in `push.sh`. A public deployment lets anyone run arbitrary Cypher against your graph — add auth or restrict it before exposing real data.
