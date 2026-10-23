"""Flask application factory for the PRISM research prototype."""
import json
from dataclasses import asdict
from pathlib import Path
import pandas as pd
from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException
from prism.config import DATA_DIR, ROOT
from prism.data.gridwatch import GridWatchClient
from prism.data.stations import StationClient
from prism.streaming.api import api as durable_api
from prism.forecasting.real_api import api as real_forecast_api
from prism.dispatch.api import api as surrogate_api
from prism.explain.api import api as explanation_api
from prism.simulation.runner import run_scenario
from prism.operations.api import api as operations_api
from prism.grid.model import load_grid, grid_summary
from prism.grid.presentation import reference_view
from prism.forecasting import AutoregressiveForecaster, LSTMForecaster, persistence_forecast
from prism.forecasting.models import TARGETS
from prism.simulation import Action, GridEnvironment, Observation, SimulationConfig, quarter_hour_profile
from prism.dispatch.baseline import recommend, encode_state
from prism.dispatch.evaluation import baseline_action, q_action
from prism.dispatch.q_learning import QLearningAgent, state_index

MODULES = [
    dict(id="data",name="Data & forecasting",status="phase2_complete",description="Audited 90-day synthetic series with persistence, autoregressive, and LSTM comparison."),
    dict(id="dispatch",name="Dispatch & Q-learning",status="phase2_complete",description="Rule-based and reviewed tabular Q-learning recommendations with paired multi-seed evidence."),
    dict(id="grid",name="Graph & simulation",status="phase2_complete",description="Versioned scenarios and deterministic 15-minute generator, battery, shedding, and fault dynamics."),
    dict(id="api",name="API & dashboard",status="phase2_complete",description="Interactive forecasting and policy-comparison workflows with explicit synthetic labels."),
]


def create_app(test_config: dict | None = None) -> Flask:
    """Build an app that runs locally without Redis, Neo4j or model artifacts."""
    app=Flask(__name__)
    app.config.update(DATA_DIR=DATA_DIR, MAX_CONTENT_LENGTH=16384)
    if test_config:
        app.config.update(test_config)

    app.register_blueprint(durable_api)
    app.register_blueprint(real_forecast_api)
    app.register_blueprint(surrogate_api)
    app.register_blueprint(explanation_api)
    app.register_blueprint(operations_api)

    app.extensions["gridwatch"] = app.config.get("GRIDWATCH_CLIENT") or GridWatchClient()

    @app.get("/api/live/gridwatch")
    def live_gridwatch():
        snapshot = app.extensions["gridwatch"].snapshot()
        response = jsonify(snapshot)
        response.status_code = 503 if snapshot["status"] == "unavailable" else 200
        response.headers["Cache-Control"] = "no-store"
        return response

    app.extensions['stations'] = app.config.get('STATION_CLIENT') or StationClient()

    @app.get('/api/live/stations')
    def live_stations():
        snapshot = app.extensions['stations'].snapshot()
        try:
            assets = reference_payload()['assets']
        except (OSError, ValueError, TypeError, KeyError):
            return jsonify(error='reference_data_unavailable'), 503
        known = {a['id'] for a in assets}
        mapped = {r['asset_id'] for r in snapshot['readings']} & known
        snapshot['coverage'] = dict(reference_assets=len(known), measured_assets=len(mapped),
            unavailable_asset_ids=sorted(known-mapped))
        response = jsonify(snapshot)
        response.headers['Cache-Control'] = 'no-store'
        return response, 503 if snapshot['status'] == 'unavailable' else 200

    @app.get('/api/live/assets/<identifier>')
    def live_asset(identifier):
        try:
            assets = reference_payload()['assets']
        except (OSError, ValueError, TypeError, KeyError):
            return jsonify(error='reference_data_unavailable'), 503
        if identifier not in {a['id'] for a in assets}:
            return jsonify(error='not_found'), 404
        snapshot = app.extensions['stations'].snapshot()
        reading = next((r for r in snapshot['readings'] if r['asset_id'] == identifier), None)
        response = jsonify(asset_id=identifier, status=reading['status'] if reading else 'unavailable',
            reading=reading, source_url=snapshot['source_url'], error=snapshot['error'],
            limitation=snapshot['limitation'])
        response.headers['Cache-Control'] = 'no-store'
        return response

    model_root = ROOT / "models"

    def topology():
        return load_grid(Path(app.config["DATA_DIR"]) / "raw/grid.json")

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/health")
    def health():
        return jsonify(status="ok",phase=2,data_source="synthetic")

    @app.get("/api/status")
    def status():
        return jsonify(phase=2,modules=MODULES)

    @app.get("/api/grid")
    def grid():
        payload=topology()
        return jsonify(**payload,summary=grid_summary(payload))

    def reference_payload():
        return reference_view(app.config.get('REFERENCE_DATASET_PATH',ROOT/'data/topology/delhi/reference_dataset.json'))

    @app.get('/api/reference-grid')
    def reference_grid():
        try:
            payload=reference_payload()
        except (OSError,ValueError,TypeError,KeyError):
            return jsonify(error='reference_data_unavailable',message='The reviewed reference export is unavailable or invalid.'),503
        response=jsonify(payload)
        response.set_etag(payload['dataset']+'-view-v2')
        response.headers['Cache-Control']='public, max-age=300'
        return response.make_conditional(request)

    @app.get('/api/reference-grid/assets/<identifier>')
    def reference_asset(identifier):
        try:
            payload=reference_payload()
        except (OSError,ValueError,TypeError,KeyError):
            return jsonify(error='reference_data_unavailable',message='The reviewed reference export is unavailable or invalid.'),503
        asset=next((a for a in payload['assets'] if a['id']==identifier),None)
        if not asset:return jsonify(error='not_found',message='Reference asset not found.'),404
        connections=[c for c in payload['connections'] if identifier in [c['source'],c['target']]]
        ids=set(asset['evidence_ids'])|{e for c in connections for e in c['evidence_ids']}
        return jsonify(dataset=payload['dataset'],mode='reference_only',asset=asset,connections=connections,
                       evidence={e:payload['evidence'][e] for e in ids})

    @app.get("/api/measurements")
    def measurements():
        frame=pd.read_csv(Path(app.config["DATA_DIR"]) / "processed/measurements.csv")
        maximum=len(frame)
        try:
            limit=int(request.args.get("limit","24"))
        except ValueError:
            return jsonify(error="invalid_request",message=f"limit must be an integer between 1 and {maximum}"),400
        if not 1 <= limit <= maximum:
            return jsonify(error="invalid_request",message=f"limit must be between 1 and {maximum}"),400
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

    @app.get("/api/forecast")
    def forecast():
        target=request.args.get("target","demand_mw")
        model=request.args.get("model","persistence")
        try:
            horizon=int(request.args.get("horizon","1"))
        except ValueError:
            return jsonify(error="invalid_request",message="horizon must be an integer between 1 and 24"),400
        if target not in TARGETS:
            return jsonify(error="invalid_request",message=f"target must be one of {', '.join(TARGETS)}"),400
        if model not in {"persistence","autoregressive","lstm"}:
            return jsonify(error="invalid_request",message="model must be persistence, autoregressive, or lstm"),400
        if not 1 <= horizon <= 24:
            return jsonify(error="invalid_request",message="horizon must be between 1 and 24"),400
        frame=pd.read_csv(Path(app.config["DATA_DIR"]) / "processed/measurements.csv")
        if model=="persistence":
            predictions=persistence_forecast(frame,target,horizon)
        elif model=="autoregressive":
            predictions=AutoregressiveForecaster(lags=24).fit(frame,target).predict(frame,horizon)
        else:
            predictions=LSTMForecaster.load(model_root / "forecasting" / f"{target}_lstm.json").predict(frame,horizon)
        return jsonify(
            data_source="synthetic",
            model=model,
            target=target,
            horizon_hours=horizon,
            predictions=[round(value,6) for value in predictions],
            limitation="Development forecast from synthetic history; not operationally validated.",
        )

    @app.post("/api/scenario")
    def scenario():
        if not request.is_json:
            return jsonify(error="invalid_request",message="Use application/json"),415
        try:
            return jsonify(run_scenario(request.get_json(),app.config['DATA_DIR']))
        except (TypeError,ValueError) as error:
            return jsonify(error='invalid_request',message=str(error)),400

    @app.post("/api/dispatch")
    def learned_dispatch():
        if not request.is_json:
            return jsonify(error="invalid_request",message="Use application/json"),415
        body=request.get_json()
        if not isinstance(body,dict):
            return jsonify(error="invalid_request",message="Expected an observation object"),400
        valid_raw=body.pop("valid_actions",None)
        try:
            observation=Observation(**body)
            encode_state(observation)
            valid=tuple(Action(value) for value in valid_raw) if valid_raw is not None else tuple(Action)
            action=QLearningAgent.load(model_root / "q_learning/phase2_policy.json").action(observation,valid)
        except (TypeError,ValueError) as error:
            return jsonify(error="invalid_request",message=str(error)),400
        return jsonify(policy="q_learning_phase2",action=action.value,state_index=state_index(observation),valid_actions=[item.value for item in valid],data_source="user_supplied",executable=False,assurance="Reviewed synthetic Phase 2 artifact; recommendation only, without power-flow validation.")

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
