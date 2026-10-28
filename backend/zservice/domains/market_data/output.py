"""Step 5: the last `rows` bars as JSON-ready records (ET wall time, no offset)."""

import numpy as np
import pandas as pd


def to_records(df: pd.DataFrame, rows: int) -> list[dict]:
    df_latest = df.tail(rows).copy()
    df_latest.reset_index(inplace=True)
    # tvDatafeed names the index 'datetime' or 'index'; rename it to 'datetime' to be sure
    if "index" in df_latest.columns and "datetime" not in df_latest.columns:
        df_latest.rename(columns={"index": "datetime"}, inplace=True)
    if "datetime" in df_latest.columns:
        try:
            if pd.api.types.is_datetime64_any_dtype(df_latest["datetime"]):
                df_latest["datetime"] = df_latest["datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                df_latest["datetime"] = (
                    df_latest["datetime"]
                    .astype(str)
                    .str.replace(r"[-+]\d{2}:\d{2}$", "", regex=True)
                )
        except Exception:
            df_latest["datetime"] = df_latest["datetime"].astype(str)
    # NaN -> None for JSON
    df_latest = df_latest.replace({np.nan: None})
    return df_latest.to_dict(orient="records")
