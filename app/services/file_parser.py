from io import BytesIO
import pandas as pd

def parse_upload(filename: str, contents: bytes, delimiter: str = ",") -> list[dict]:
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

    df.columns = [col.split("_")[0] for col in df.columns]  # Strips all column names to their 5-digit code prefix
    return df.to_dict(orient='records')