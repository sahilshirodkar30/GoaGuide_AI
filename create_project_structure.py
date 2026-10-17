from pathlib import Path

root = Path(".")

folders = [
    "app/agents/nodes",
    "app/gateway",
    "app/guardrails",        # fixed typo
    "app/services/retrieval",
    "app/ingestion/chunking",
    "app/ingestion/loaders",
    "app/data",
    "app/ui",
]

files = [
    # Agents
    "app/agents/__init__.py",
    "app/agents/graph.py",
    "app/agents/state.py",
    "app/agents/nodes/__init__.py",
    "app/agents/nodes/planner.py",
    "app/agents/nodes/responder.py",
    "app/agents/nodes/retriever.py",
    # Gateway
    "app/gateway/__init__.py",
    "app/gateway/client.py",
    # Guardrails
    "app/guardrails/__init__.py",
    "app/guardrails/colang_rules.py",
    "app/guardrails/rails.py",
    # Ingestion
    "app/ingestion/__init__.py",
    "app/ingestion/processor.py",
    "app/ingestion/chunking/__init__.py",
    "app/ingestion/chunking/splitter.py",
    "app/ingestion/loaders/__init__.py",
    "app/ingestion/loaders/html.py",
    "app/ingestion/loaders/office.py",
    "app/ingestion/loaders/pdf.py",
    "app/ingestion/loaders/text.py",
    "app/ingestion/loaders/markdown.py",   # renamed
    # Services
    "app/services/__init__.py",
    "app/services/retrieval/__init__.py",
    "app/services/retrieval/embedding.py",
    "app/services/retrieval/pinecone_service.py",
    "app/services/retrieval/ranking_service.py",
    # Root
    "app/__init__.py",
    "app/config.py",
    "app/main.py",
    "requirements.txt",
    "run.py",
    ".env",
    ".gitignore",
    "app/data/",
    "app/logger.py"
]

for folder in folders:
    (root / folder).mkdir(parents=True, exist_ok=True)

for file in files:
    p = root / file
    p.parent.mkdir(parents=True, exist_ok=True)
    p.touch(exist_ok=True)

print("✅ Project structure created successfully.")