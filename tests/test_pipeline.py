import pandas as pd
from src.models import build_stub_model
from src.pipeline import prepare_and_predict

def test_pipeline_runs():
    model = build_stub_model()
    df = pd.DataFrame([{
        "shipName":"TEST",
        "startGMTDate":"2025-01-01T00:00:00Z",
        "sessionId":"S1",
        "speed":10.0,
        "duration":2.0,
        "displacement":10000,
        "beaufortScale":2,
        "days_since_cleaning":30,
        "historical_avg_speed":9.0,
        "paint_x_speed":1.0,
        "paint_encoded":0
    }])
    out = prepare_and_predict(df, model=None)
    assert "baseline_consumption" in out.columns