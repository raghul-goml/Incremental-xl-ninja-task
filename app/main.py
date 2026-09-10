import io

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Depends,
    HTTPException
)

from sqlalchemy.orm import Session

from openpyxl import load_workbook

from .database import Base, engine, get_db
from .models import ExcelRow

from pydantic import BaseModel

app = FastAPI(
    title="Incremental Excel Upload API"
)


Base.metadata.create_all(bind=engine)


class items(BaseModel):
    name : str
    price : float
    avaliablity : bool





emp = [
    {'id':1,'name':'karan','service':'fast api','status':'active',
    'id':2,'name':'kumar','service':'fast api','status':'inactive',
    'id':3,'name':'gautam','service':'react','status':'active'}
]



@app.get("/display/{id}")
def view(id:int):
    for e in emp:
        if e['id'] == id:
            return e
        else:
            return "ID not found"

@app.get("/display")
def query_par(id : str):
    for e in emp:
        if e['name']==id:
            return e
        else:
            return "Id not found"

@app.get("/")
def root():
    return {
        "message": "Incremental Excel API is running"
    }


@app.post("/upload")
async def upload_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    if not file.filename.endswith(".xlsx"):
        raise HTTPException(
            status_code=400,
            detail="Only XLSX files are supported"
        )

    contents = await file.read()

    workbook = load_workbook(
        filename=io.BytesIO(contents),
        data_only=True
    )

    sheet = workbook.active

    headers = [
        cell.value
        for cell in sheet[1]
    ]

    processed_rows = []
    skipped_rows = []

    for row in sheet.iter_rows(
        min_row=2,
        values_only=True
    ):

        row_data = dict(
            zip(headers, row)
        )

        row_id = str(row_data["ID"])

        existing_row = (
            db.query(ExcelRow)
            .filter(
                ExcelRow.row_id == row_id
            )
            .first()
        )

        if existing_row:
            skipped_rows.append(row_id)
            continue

        new_row = ExcelRow(
            row_id=row_id,
            name=row_data.get("Name"),
            service=row_data.get("Service"),
            status=row_data.get("Status")
        )

        db.add(new_row)

        processed_rows.append(row_data)

    db.commit()

    return {
        "filename": file.filename,
        "processed_count": len(processed_rows),
        "skipped_count": len(skipped_rows),
        "processed_rows": processed_rows,
        "skipped_rows": skipped_rows
    }