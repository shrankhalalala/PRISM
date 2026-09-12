"""Run the local development server with python -m prism."""
import os
from prism import create_app

if __name__ == "__main__":
    create_app().run(host=os.environ.get("PRISM_HOST", "127.0.0.1"),
                     port=int(os.environ.get("PRISM_PORT", "5050")), debug=False)
