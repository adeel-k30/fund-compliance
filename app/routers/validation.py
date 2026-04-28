from fastapi import APIRouter, Request, UploadFile, File, HTTPException, status, Form

from app.services.file_parser import parse_upload

router = APIRouter(
    prefix="/validate",
    tags=["validate"])

@router.post("/emt")
async def validate_emt(request: Request, file: UploadFile = File(...), delimiter: str = Form(",")):
    extension = file.filename.split('.')[-1].lower()
    if extension not in ['xlsx', 'xls', 'csv']:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only Excel (.xlsx, .xls) and CSV files are supported"
        )

    # Read the files bytes
    contents = await file.read()

    try:
        rows = parse_upload(file.filename, contents, delimiter)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    rule_engine = request.app.state.rule_engine
    validation_results = rule_engine.validate_file(rows, file.filename)
    return  validation_results
