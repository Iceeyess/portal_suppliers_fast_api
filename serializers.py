from pydantic import BaseModel, root_validator


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
