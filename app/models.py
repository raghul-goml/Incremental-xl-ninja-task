from sqlalchemy import Column, Integer, String

from .database import Base


class ExcelRow(Base):

    __tablename__ = "excel_rows"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    row_id = Column(
        String,
        unique=True,
        index=True,
        nullable=False
    )

    name = Column(String)

    service = Column(String)

    status = Column(String)