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
    """
    Manages the loading and initial cleaning of Asana CSV exports.

    This class is responsible for reading the raw CSV file, standardizing
    column names according to `ASANA_MAPPING`, and ensuring date columns
    are properly formatted for Pandas operations.

    Attributes:
        df (pd.DataFrame | None): The currently loaded and cleaned dataframe.
    """
    def __init__(self):
        """Initializes an empty DataModel."""
        self.df = None

    def load_csv(self, path: str) -> pd.DataFrame:
        """
        Reads a CSV file from the given path and processes it.

        Args:
            path (str): The absolute path to the Asana CSV file.

        Returns:
            pd.DataFrame: The cleaned and formatted dataframe.
        """
        df = pd.read_csv(path)
        df = self.clean(df)
        self.df = df
        return df

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Renames columns and formats date fields.

        Standardizes column names and converts dates into datetime objects.
        It drops 'corrupted' tasks, for example a task with only a start date but
        no end date.

        Args:
            df (pd.DataFrame): The raw dataframe loaded directly from the CSV.

        Returns:
            pd.DataFrame: The cleaned dataframe
        """
        for k, v in ASANA_MAPPING.items():
            if k in df.columns:
                df = df.rename(columns={k: v})
        df = df.copy()
        for c in ("StartDate", "EndDate"):
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors="coerce")

        return df.dropna(subset=["StartDate", "EndDate"])
