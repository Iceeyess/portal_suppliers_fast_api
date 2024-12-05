from datetime import datetime
from serializers import ResponseInvoices, ResponseSearchByInvoice


def re_format_cycle(obj):
    try:
        if len(obj[0]) == 11:
            for index in range(len(obj)):
                obj[index] = ResponseInvoices(
                    invoiceNumber=obj[index][0],
                    invoiceInitialIssueDate=str(
                        datetime.strptime(obj[index][1], '%Y-%m-%dT%H:%M:%S').strftime('%d-%m-%Y')),
                    invoiceDescription=obj[index][2],
                    storeNum=obj[index][3],
                    storeName=obj[index][4],
                    paymentDate=str(datetime.strptime(obj[index][5], '%Y-%m-%dT%H:%M:%S').strftime('%d-%m-%Y')),
                    grossAmount=float(obj[index][6]),
                    amountRemaining=float(obj[index][7]),
                    factualReqDate=str(datetime.strptime(str(obj[index][8]), '%Y-%m-%dT%H:%M:%S').strftime('%d-%m-%Y')),
                    factualReqNum=str(obj[index][9]),
                    invoiceStatus=obj[index][10]
                )
        elif len(obj[0]) == 14:
            for index in range(len(obj)):
                obj[index] = ResponseSearchByInvoice(
                    invoiceNumber=obj[index][0],
                    invoiceInitialIssueDate=str(
                        datetime.strptime(obj[index][1], '%Y-%m-%dT%H:%M:%S').strftime('%d-%m-%Y')),
                    invoiceDescription=obj[index][2],
                    storeNum=obj[index][3],
                    storeName=obj[index][4],
                    invoicePaymentDueDate=str(
                        datetime.strptime(obj[index][5], '%Y-%m-%dT%H:%M:%S').strftime('%d-%m-%Y')),
                    grossAmount=float(obj[index][6]),
                    amountRemaining=float(obj[index][7]),
                    factualReqDate=str(datetime.strptime(str(obj[index][8]), '%Y-%m-%dT%H:%M:%S').strftime('%d-%m-%Y')),
                    factualReqNum=str(obj[index][9]),
                    invoiceStatus=obj[index][10],
                    paymentDate=str(datetime.strptime(str(obj[index][11]), '%Y-%m-%dT%H:%M:%S').strftime('%d-%m-%Y')),
                    checkNumber=str(obj[index][12]),
                    paymentAmount=float(obj[index][13])
                )
    except IndexError:
        return {"error": "По запросу нет данных."}
    return obj