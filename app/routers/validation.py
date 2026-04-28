from io import BytesIO
from fastapi import APIRouter, Request, UploadFile, File, HTTPException, status
import pandas as pd

router = APIRouter(
    prefix="/validate",
    tags=["validate"])

@router.post("/emt")
async def validate_emt(file: UploadFile = File(...), request: Request = None):
    """
    Validate EMT file.
    """
    # Read the files bytes
    contents = await file.read()

    # Check if the file is an Excel file based on its extension
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only Excel files (.xlsx, .xls) are supported"
        )

    try:
        data = pd.read_excel(BytesIO(contents), header=0)
        data.columns = [col.split("_")[0] for col in data.columns]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Excel parsing error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read file: {str(e)}"
        )

    rows = data.to_dict(orient='records')

    rule_engine = request.app.state.rule_engine
    validation_results = rule_engine.validate_file(rows, file.filename)
    return  validation_results
