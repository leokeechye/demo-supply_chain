"""Google ADK agent for the Neo4j pharma supply-chain demo.

Wraps the live FastAPI toolset (deployed on Railway) as ADK function tools.
The agent never touches Neo4j directly: it calls HTTP tool endpoints, which
run Cypher against the AuraDB Professional instance.

Flow:  ADK agent (gpt-4.1 via litellm) -> HTTP -> FastAPI toolset -> Cypher -> Neo4j
"""

import os
from typing import Any

import requests
from dotenv import load_dotenv

from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm

# Load OPENAI_API_KEY (+ Neo4j vars) from the repo-root .env
load_dotenv(os.path.join(os.path.dirname(__file__), os.pardir, ".env"))

TOOLSET_URL = os.environ.get(
    "TOOLSET_URL", "https://supply-chain-toolset-production.up.railway.app"
)
TIMEOUT = 60


def _get(path: str) -> dict[str, Any]:
    r = requests.get(f"{TOOLSET_URL}{path}", timeout=TIMEOUT)
    r.raise_for_status()
    return {"result": r.json()}


def _post(path: str, payload: dict) -> dict[str, Any]:
    r = requests.post(f"{TOOLSET_URL}{path}", json=payload, timeout=TIMEOUT)
    r.raise_for_status()
    return {"result": r.json()}


# --- no-parameter tools (GET) ----------------------------------------------

def find_single_supplier_risks() -> dict:
    """Find raw materials that are supplied by only a single company (single-source supply risk)."""
    return _get("/tools/find_single_supplier_risks")


def top_suppliers_by_product_count() -> dict:
    """List the top suppliers ranked by how many products they supply."""
    return _get("/tools/top_suppliers_by_product_count")


def raw_materials_by_supplier_count() -> dict:
    """List raw materials and their number of suppliers, flagging single-supplier ones."""
    return _get("/tools/raw_materials_by_supplier_count")


def api_dependency_risk() -> dict:
    """Identify Active Pharmaceutical Ingredients (APIs) used in 5 or more different drug products."""
    return _get("/tools/api_dependency_risk")


def get_schema() -> dict:
    """Return the Neo4j graph schema (node labels, relationship types, properties)."""
    return _get("/tools/get_schema")


# --- product-scoped tools (POST {"description": ...}) ----------------------

def trace_supply_path(description: str) -> dict:
    """Trace the full supply path for a product, given its product name/description."""
    return _post("/tools/trace_supply_path", {"description": description})


def dependency_chain(description: str) -> dict:
    """Get the full dependency chain for a product, given its product name/description."""
    return _post("/tools/dependency_chain", {"description": description})


def top_suppliers_for_product(description: str) -> dict:
    """For a given product (by description), return the top suppliers ranked by product count."""
    return _post("/tools/top_suppliers_for_product", {"description": description})


def distributors_for_product(description: str) -> dict:
    """List the distributors for a product, given its description."""
    return _post("/tools/distributors_for_product", {"description": description})


def logistics_optimization(description: str) -> dict:
    """Analyze shipment logistics for a product to find inefficiencies (cross-border or cyclic routes)."""
    return _post("/tools/logistics_optimization", {"description": description})


# --- expert escape hatch (POST {"query": ...}) -----------------------------

def run_cypher(query: str) -> dict:
    """Execute a custom read-only Cypher query against the pharma supply-chain graph.
    Use only when no higher-level tool fits. Always use a LIMIT to bound results."""
    return _post("/tools/run_cypher", {"query": query})


root_agent = Agent(
    model=LiteLlm(model="openai/gpt-4.1"),
    name="supply_chain_agent",
    description="Answers pharmaceutical supply-chain questions over a Neo4j graph via a remote toolset.",
    instruction=(
        "You are a pharmaceutical supply-chain analyst. Answer questions about suppliers, "
        "raw materials, APIs, drug products, distributors, and logistics by calling the "
        "provided tools, which query a Neo4j graph. Prefer the specific high-level tools; "
        "use run_cypher only as a last resort and always bound it with LIMIT. "
        "Summarize results clearly for a business audience and cite concrete names/numbers."
    ),
    tools=[
        find_single_supplier_risks,
        top_suppliers_by_product_count,
        raw_materials_by_supplier_count,
        api_dependency_risk,
        get_schema,
        trace_supply_path,
        dependency_chain,
        top_suppliers_for_product,
        distributors_for_product,
        logistics_optimization,
        run_cypher,
    ],
)
