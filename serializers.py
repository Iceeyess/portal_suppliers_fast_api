import datetime

from pydantic import BaseModel, root_validator
from fastapi import responses, HTTPException
from fastapi import status


class ResponseSearchByInvoice(BaseModel):
    """class for serializing search-by-invoice method"""
    invoiceNumber: str
    invoiceInitialIssueDate: str
    invoiceDescription: str
    storeNum: str
    storeName: str
    invoicePaymentDueDate: str
    grossAmount: float
    amountRemaining: float
    factualReqDate: str
    factualReqNum: str
    invoiceStatus: str
    paymentDate: str
    checkNumber: str
    paymentAmount: float

class ResponseInvoices(BaseModel):
    """class for serializing other methods"""
    invoiceNumber: str
    invoiceInitialIssueDate: str
    invoiceDescription: str
    storeNum: str
    storeName: str
    paymentDate: str
    grossAmount: float
    amountRemaining: float
    factualReqDate: str
    factualReqNum: str
    invoiceStatus: str

class DateValidation(BaseModel):
    date_from: str
    date_to: str

    @root_validator(pre=True)
    def validate_dates(cls, values):
        date_from, date_to = values.get("date_from"), values.get("date_to")
        if date_from and date_to and date_from > date_to:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Начальная дата должна быть меньше конечной даты')
        elif not date_from or not date_to:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Необходимо указать обе даты')
        else:
            try:
                datetime.datetime.strptime(date_from, '%Y-%m-%d')
                datetime.datetime.strptime(date_to, '%Y-%m-%d')
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Даты должны быть в формате YYYY-MM-DD')

        return values
