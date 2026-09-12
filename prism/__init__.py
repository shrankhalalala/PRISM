"""Flask application factory for the PRISM Phase 1 foundation."""
import json
from pathlib import Path
import pandas as pd
from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException
from prism.config import DATA_DIR, ROOT
from prism.grid.model import load_grid, grid_summary
from prism.simulation.environment import GridEnvironment, Observation
from prism.dispatch.baseline import recommend, encode_state

MODULES = [
    dict(id="data",name="Data & forecasting",owner="Nishtha Jain",status="foundation_ready",description="Synthetic dataset, data dictionary, validation and quality audit. LSTM training follows in Phase 2."),
    dict(id="dispatch",name="Dispatch, Q-learning & XAI",owner="Himangi Mishra",status="foundation_ready",description="Baseline prototype, 270-state encoding and RL specification. No trained policy yet."),
    dict(id="grid",name="Graph & simulation",owner="Shrankhala Singh",status="foundation_ready",description="Validated synthetic topology, Neo4j seed adapter and resettable simulator skeleton. Dynamics follow in Phase 2."),
    dict(id="api",name="API & dashboard",owner="Gaurangi Tyagi",status="foundation_ready",description="Read-only grid/data APIs, baseline preview, API contract and interactive dashboard foundation."),
]


def create_app(test_config: dict | None = None) -> Flask:
    """Build an app that runs locally without Redis, Neo4j or model artifacts."""
    app=Flask(__name__)
    app.config.update(DATA_DIR=DATA_DIR, MAX_CONTENT_LENGTH=16384)
    if test_config:
        app.config.update(test_config)

    def topology():
        return load_grid(Path(app.config["DATA_DIR"]) / "raw/grid.json")

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/health")
    def health():
        return jsonify(status="ok",phase=1,data_source="synthetic")

    @app.get("/api/status")
    def status():
        return jsonify(phase=1,modules=MODULES)

    @app.get("/api/grid")
    def grid():
        payload=topology()
        return jsonify(**payload,summary=grid_summary(payload))

    @app.get("/api/measurements")
    def measurements():
        try:
            limit=int(request.args.get("limit","24"))
        except ValueError:
            return jsonify(error="invalid_request",message="limit must be an integer between 1 and 336"),400
        if not 1 <= limit <= 336:
            return jsonify(error="invalid_request",message="limit must be between 1 and 336"),400
        frame=pd.read_csv(Path(app.config["DATA_DIR"]) / "processed/measurements.csv")
        records=frame.tail(limit).to_dict(orient="records")
        return jsonify(data_source="synthetic",records=records,count=len(records))

    @app.get("/api/data/quality")
    def quality():
        return jsonify(json.loads((Path(app.config["DATA_DIR"]) / "processed/quality_report.json").read_text()))

    @app.route("/api/dispatch/baseline",methods=["GET","POST"])
    def baseline():
        if request.method=="GET":
            state=Observation(**GridEnvironment(topology()).reset())
        else:
            if not request.is_json:
                return jsonify(error="invalid_request",message="Use application/json"),415
            body=request.get_json()
            if not isinstance(body,dict):
                return jsonify(error="invalid_request",message="Expected an observation object"),400
            try:
                state=Observation(**body)
            except TypeError:
                return jsonify(error="invalid_request",message="Required: demand_mw, generation_mw, reserve_mw. Optional: battery_soc, renewable_trend, fault_present."),400
        try:
            result=recommend(state)
            encoded=encode_state(state)
        except ValueError as error:
            return jsonify(error="invalid_request",message=str(error)),400
        return jsonify(**result,data_source="synthetic" if request.method=="GET" else "user_supplied",encoded_state=encoded)

    @app.route("/api/forecast",methods=["GET"])
    @app.route("/api/dispatch",methods=["POST"])
    @app.route("/api/explain",methods=["POST"])
    @app.route("/api/scenario",methods=["POST"])
    def planned():
        return jsonify(error="not_implemented",phase=1,message="This module is defined in the API contract and will be implemented in Phases 2–3."),501

    @app.get("/api/openapi.json")
    def openapi():
        return jsonify(json.loads((ROOT / "docs/openapi.json").read_text()))

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error=error.name.lower().replace(" ","_"),message=error.description),error.code

    @app.errorhandler(FileNotFoundError)
    def missing_data(error):
        app.logger.error("Required fixture missing: %s",error)
        return jsonify(error="data_unavailable",message="Run python -m scripts.generate_sample and python -m scripts.prepare_data."),503

    return app
