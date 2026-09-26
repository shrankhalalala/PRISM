"""Flask application factory for the PRISM research prototype."""
import json
from dataclasses import asdict
from pathlib import Path
import pandas as pd
from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException
from prism.config import DATA_DIR, ROOT
from prism.grid.model import load_grid, grid_summary
from prism.forecasting import AutoregressiveForecaster, persistence_forecast
from prism.forecasting.models import TARGETS
from prism.simulation import Action, GridEnvironment, Observation, SimulationConfig, quarter_hour_profile
from prism.dispatch.baseline import recommend, encode_state

MODULES = [
    dict(id="data",name="Data & forecasting",owner="Nishtha Jain",status="phase2_in_progress",description="Validated synthetic data, persistence benchmark and autoregressive forecasting baseline. LSTM evaluation remains."),
    dict(id="dispatch",name="Dispatch, Q-learning & XAI",owner="Himangi Mishra",status="phase2_in_progress",description="Constrained baseline interface and trainable, persistent tabular Q-learning policy. XAI remains."),
    dict(id="grid",name="Graph & simulation",owner="Shrankhala Singh",status="phase2_core_ready",description="Deterministic 15-minute simulator with generator, battery, load-shedding and scheduled-fault dynamics."),
    dict(id="api",name="API & dashboard",owner="Gaurangi Tyagi",status="phase2_in_progress",description="Forecast and scenario APIs are available; interactive simulation dashboard work remains."),
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
        return jsonify(status="ok",phase=2,data_source="synthetic")

    @app.get("/api/status")
    def status():
        return jsonify(phase=2,modules=MODULES)

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
        if model not in {"persistence","autoregressive"}:
            return jsonify(error="invalid_request",message="model must be persistence or autoregressive"),400
        if not 1 <= horizon <= 24:
            return jsonify(error="invalid_request",message="horizon must be between 1 and 24"),400
        frame=pd.read_csv(Path(app.config["DATA_DIR"]) / "processed/measurements.csv")
        if model=="persistence":
            predictions=persistence_forecast(frame,target,horizon)
        else:
            predictions=AutoregressiveForecaster(lags=24).fit(frame,target).predict(frame,horizon)
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
        body=request.get_json()
        if not isinstance(body,dict):
            return jsonify(error="invalid_request",message="Expected a scenario object"),400
        unknown=set(body).difference({"steps","seed","actions","faults"})
        if unknown:
            return jsonify(error="invalid_request",message=f"Unknown scenario fields: {', '.join(sorted(unknown))}"),400
        steps=body.get("steps",8)
        seed=body.get("seed",42)
        actions=body.get("actions")
        faults=body.get("faults",[])
        if isinstance(steps,bool) or not isinstance(steps,int) or not 1 <= steps <= 96:
            return jsonify(error="invalid_request",message="steps must be an integer between 1 and 96"),400
        if isinstance(seed,bool) or not isinstance(seed,int):
            return jsonify(error="invalid_request",message="seed must be an integer"),400
        if actions is not None and (not isinstance(actions,list) or len(actions)!=steps):
            return jsonify(error="invalid_request",message="actions must contain exactly one action per step"),400
        if not isinstance(faults,list):
            return jsonify(error="invalid_request",message="faults must be an array"),400
        try:
            selected_actions=[Action(value) for value in actions] if actions is not None else None
            frame=pd.read_csv(Path(app.config["DATA_DIR"]) / "processed/measurements.csv")
            profile=quarter_hour_profile(frame,hours=24)[:steps]
            environment=GridEnvironment(
                topology(),
                profile=profile,
                faults=faults,
                config=SimulationConfig(episode_steps=steps),
                seed=seed,
            )
            trajectory=[]
            totals={"return":0.0,"unserved_mwh":0.0,"curtailed_mwh":0.0,"operating_cost":0.0,"emissions_kg":0.0}
            observation=Observation(**environment.reset(seed=seed))
            for index in range(steps):
                if selected_actions is None:
                    candidate=Action(recommend(observation)["action"])
                    action=candidate if candidate in environment.valid_actions() else Action.HOLD
                else:
                    action=selected_actions[index]
                next_raw,reward,terminated,info=environment.step(action)
                trajectory.append({"observation":asdict(observation),"reward":reward,**info})
                totals["return"]+=reward
                for key in ("unserved_mwh","curtailed_mwh","operating_cost","emissions_kg"):
                    totals[key]+=info["metrics"][key]
                observation=Observation(**next_raw)
                if terminated:
                    break
        except (TypeError,ValueError) as error:
            return jsonify(error="invalid_request",message=str(error)),400
        return jsonify(
            data_source="synthetic",
            policy="provided_actions" if selected_actions is not None else "rule_based_prototype",
            seed=seed,
            steps=len(trajectory),
            totals={key:round(value,6) for key,value in totals.items()},
            final_observation=asdict(observation),
            trajectory=trajectory,
            assurance="Synthetic aggregate simulation; no AC/DC power flow or operational switching.",
        )

    @app.route("/api/dispatch",methods=["POST"])
    @app.route("/api/explain",methods=["POST"])
    def planned():
        return jsonify(error="not_implemented",phase=2,message="A trained policy artifact or explainability model has not been configured."),501

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
