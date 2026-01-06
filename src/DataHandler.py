import pandas as pd

ASANA_MAPPING = {
    'Task ID': 'TaskID',
    'Name': 'TaskName',
    'Start Date': 'StartDate',
    'Due Date': 'EndDate',
    'Created At': 'Created',
    'Completed At': 'Completed',
}

class DataModel:
    def __init__(self):
        self.df = None

    def load_csv(self, path: str) -> pd.DataFrame:
        df = pd.read_csv(path)
        df = self.clean(df)
        self.df = df
        return df

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        for k, v in ASANA_MAPPING.items():
            if k in df.columns:
                df = df.rename(columns={k: v})

        for c in ("StartDate", "EndDate"):
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors="coerce")

        return df.dropna(subset=["StartDate", "EndDate"])
