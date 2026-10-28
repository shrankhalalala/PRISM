"""Run the local development server with python -m prism."""
import os
from dotenv import load_dotenv
from prism import create_app
from prism.config import ROOT


def configure_local():
    """Use host-published Docker ports; explicit shell values take precedence."""
    load_dotenv(ROOT / ".env", override=False)
    os.environ.setdefault("NEO4J_URI", "bolt://127.0.0.1:7687")
    os.environ.setdefault("NEO4J_USER", "neo4j")
    if os.environ.get("PRISM_DATABASE_URL") and os.environ.get("PRISM_REDIS_URL"):
        os.environ.setdefault("PRISM_USE_DURABLE_LIVE", "1")
        os.environ.setdefault("PRISM_REQUIRE_SERVICES", "1")

if __name__ == "__main__":
    configure_local()
    create_app().run(host=os.environ.get("PRISM_HOST", "127.0.0.1"),
                     port=int(os.environ.get("PRISM_PORT", "5051")), debug=False)
