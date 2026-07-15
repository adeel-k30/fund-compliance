# Parses an uploaded EMT file (CSV or Excel) into a list of row dicts.
#
# EMT column headers look like "00010_ISIN" — we strip everything after the
# underscore so the rule engine can look up values by the 5-digit field code
# (e.g. row["00010"]) rather than the full column name.

from io import BytesIO
import pandas as pd

def parse_upload(filename: str, contents: bytes, delimiter: str = ",") -> list[dict]:
    # BytesIO lets pandas read raw bytes as if they were a file on disk
    extension = filename.split('.')[-1].lower()
    if extension == 'csv':
        try:
            df = pd.read_csv(BytesIO(contents), header=0, delimiter=delimiter)
        except Exception as e:
            raise ValueError(f"Error parsing CSV file: {str(e)}")
    else:
        try:
            df = pd.read_excel(BytesIO(contents), header=0)
        except Exception as e:
            raise ValueError(f"Error parsing Excel file: {str(e)}")

    # "00010_ISIN" → "00010" so the rule engine can match by field code
    df.columns = [col.split("_")[0] for col in df.columns]
    # orient='records' → [{"00010": "IE00B...", "00030": "Acme Fund", ...}, ...]
    return df.to_dict(orient='records')