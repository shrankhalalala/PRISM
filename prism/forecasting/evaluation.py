"""Gap-aware frozen-origin evaluation shared by experiments and lifecycle."""
import numpy as np
import pandas as pd

def origins(frame,start,end,window=24,horizon=24):
    """Daily nonoverlapping targets; all 48 source hours must be observed."""
    stamps=pd.to_datetime(frame.timestamp,utc=True)
    result=[]
    for i in range(start,end-horizon+1,24):
        piece=frame.iloc[i-window:i+horizon]
        if len(piece)!=window+horizon or piece.demand_mw.isna().any():continue
        if (stamps.iloc[i+horizon-1]-stamps.iloc[i-window])!=pd.Timedelta(hours=window+horizon-1):continue
        result.append(i)
    return result


def evaluate(frame,indices,models):
    actual=[];predictions={name:[] for name in models}
    for i in indices:
        history=frame.iloc[i-24:i]
        actual.append(frame.demand_mw.iloc[i:i+24].to_numpy())
        for name,model in models.items():
            predictions[name].append(model.predict(history,24) if model else [float(history.demand_mw.iloc[-1])]*24)
    if not actual:raise ValueError('No eligible held-out 24-hour origins')
    return np.asarray(actual),{name:np.asarray(values) for name,values in predictions.items()}
