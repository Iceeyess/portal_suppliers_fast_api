from dotenv import load_dotenv
from fastapi import FastAPI
import oracledb, os, pathlib, uvicorn
from fastapi.params import Depends
from constants import PATH_LIB
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from serializers import DataValidation
from services import re_format_cycle


dot_env = os.path.join(pathlib.Path().resolve(), '.env')
load_dotenv(dotenv_path=dot_env)
app = FastAPI()


@app.get("/invoices-classified-by-date")
def get_invoices_classified_by_date(invoice_status: str, data: DataValidation = Depends()):
    oracledb.init_oracle_client(lib_dir=PATH_LIB)
    conn = oracledb.connect(user=os.getenv('USER'), password=os.getenv('PASSWORD'), host=os.getenv('HOST'),
                            port=os.getenv('PORT'), service_name=os.getenv('SERVICE_NAME'))
    cur = conn.cursor()
    request = f"""
    -----------------------------------
    --Список счетов по дате оплаты version_7
    -----------------------------------

    with vendors as (
    SELECT DISTINCT v.segment1, v.vendor_id, s.ORG_ID, decode(nvl(v.ATTRIBUTE1,'0'),'0',s.VENDOR_SITE_CODE_ALT,p.PARTY_NAME) vendor_name, 
           v.GLOBAL_ATTRIBUTE1 uniquePartnerIdentifier, v.end_date_active, s.inactive_date, 
           v.VENDOR_TYPE_LOOKUP_CODE v_type, ltrim(decode(nvl(v.ATTRIBUTE1,'0'),'0',v.VAT_REGISTRATION_NUM,p.TAX_REFERENCE)) INN, nvl(v.ATTRIBUTE1,'0') fact
    FROM po.po_vendor_sites_all s, po.po_vendors v, ar.HZ_CUST_ACCT_SITES_ALL cas, ar.hz_cust_accounts a, ar.hz_parties p, ap.ap_terms_tl t
    WHERE 1 = 1
    --    and   s.vendor_id = 18130
    AND   s.org_id IN (82, 224)
    AND   nvl(s.INACTIVE_DATE,sysdate+1) >= SYSDATE 
    AND   v.VENDOR_ID = s.VENDOR_ID 
    --    and   v.GLOBAL_ATTRIBUTE1 = '10008118'
    AND   nvl(v.END_DATE_ACTIVE,sysdate+1) >= sysdate
    AND   t."LANGUAGE" = 'RU'
    AND   t.TERM_ID = s.TERMS_ID 
    AND   CAS.attribute7 = s.VENDOR_SITE_CODE
    AND   a.CUST_ACCOUNT_ID  = cas.CUST_ACCOUNT_ID
    AND   a.status = 'A'
    AND   p.PARTY_ID = a.PARTY_ID
       ), 
    flex_values_description AS (
    SELECT f.FLEX_VALUE, f.DESCRIPTION  
    FROM apps.FND_FLEX_VALUES_VL f 
    WHERE f.VALUE_CATEGORY = 'LM_RU_ENT_SI'
    )
    SELECT  /*+ORDERED*/nvl(i.attribute6,i.invoice_num) "Номер счета", nvl(to_date(i.attribute7, 'YYYY/MM/DD HH24:MI:SS'), i.invoice_date) "Дата счета", 
       i.description "Внутр. номер", i.attribute1 "Номер магазина", (SELECT DISTINCT fvd.DESCRIPTION FROM flex_values_description fvd WHERE fvd.FLEX_VALUE = i.attribute1) AS "Наимен. маг-на",
       a.PLANNED_DATE "Дата платежа", 
       nvl(a.amount, ps.GROSS_AMOUNT) "Сумма к оплате", 
       ps.amount_remaining "Ост. оплатить", a.FACTUAL_REQ_DATE AS Дата_заявки, a.FACTUAL_REQ_NUM AS Номер_заявки,
       nvl((select 'Заблокирован для оплаты' from ap.ap_holds_all h
         where h.invoice_id = i.invoice_id
         and   h.release_lookup_code is null
         and   rownum = 1), 'Ожидает оплату') "Статус счета"
    from vendors v, ap.ap_invoices_all i , AP.ap_payment_schedules_all ps, xxt.xxt_bc_factual_req_headers_all a
    where 1=1 
    AND i.vendor_id = v.vendor_id
    and ps.invoice_id = i.invoice_id
    AND a.invoice_id(+) = i.invoice_id
    and   v.org_id IN (82, 224) 
    and   a.PLANNED_DATE between TO_DATE('{data.date_from}','YYYY-MM-DD') and TO_DATE('{data.date_to}', 'YYYY-MM-DD') -- Внешний параметh Front END (даты)
    AND   v.uniquePartnerIdentifier = '{data.unique_partner_identifier}'  -- параметр соответствия между порталом и OEBS. PCS - uniquePartnerIdentifier
    AND EXISTS (select '1' from ap.ap_holds_all h
         where h.invoice_id = i.invoice_id
         and   h.release_lookup_code IS null
         and   rownum = 1 AND '{invoice_status}'  = 'Заблокирован для оплаты' -- параметр "Все"(левое выражение) -внешний входящий параметр от Front end. Параметр может быть один из 3 вариаций: Все, Ожидает оплату, Заблокирован для оплаты
         UNION
         SELECT '1' FROM DUAL WHERE '{invoice_status}'  IN ('Ожидает оплату', 'Все')) -- параметр "Все"(левое выражение) -внешний входящий параметр от Front end. Параметр может быть один из 3 вариаций: Все, Ожидает оплату, Заблокирован для оплаты
    AND not EXISTS (select '1' from ap.ap_holds_all h
         where h.invoice_id = i.invoice_id
         and   h.release_lookup_code IS null
         and   rownum = 1 AND '{invoice_status}'  = 'Ожидает оплату') -- параметр "Все"(левое выражение) -внешний входящий параметр от Front end. Параметр может быть один из 3 вариаций: Все, Ожидает оплату, Заблокирован для оплаты
    """
    cur.execute(request)
    results = cur.fetchall()
    results = jsonable_encoder(results)
    results = re_format_cycle(results)
    results = jsonable_encoder(results)
    return JSONResponse(content=results)


@app.get("/search-by-invoice")
def get_search_by_invoice(unique_partner_identifier, num, check_num):
    oracledb.init_oracle_client(lib_dir=PATH_LIB)
    conn = oracledb.connect(user=os.getenv('USER'), password=os.getenv('PASSWORD'), host=os.getenv('HOST'),
                            port=os.getenv('PORT'), service_name=os.getenv('SERVICE_NAME'))
    cur = conn.cursor()
    request = f"""
    -----------------------------------
    --Поиск по счету version_8
    -----------------------------------
    WITH vendors AS (
        SELECT /*+ ORDERED */ DISTINCT v.segment1, v.vendor_id, s.ORG_ID, decode(nvl(v.ATTRIBUTE1,'0'),'0',s.VENDOR_SITE_CODE_ALT,p.PARTY_NAME) vendor_name, 
               v.GLOBAL_ATTRIBUTE1 uniquePartnerIdentifier, v.end_date_active, s.inactive_date, 
               v.VENDOR_TYPE_LOOKUP_CODE v_type, ltrim(decode(nvl(v.ATTRIBUTE1,'0'),'0',v.VAT_REGISTRATION_NUM,p.TAX_REFERENCE)) INN, nvl(v.ATTRIBUTE1,'0') fact
        FROM po.po_vendors v, po.po_vendor_sites_all s, ar.HZ_CUST_ACCT_SITES_ALL cas, ar.hz_cust_accounts a, ar.hz_parties p, ap.ap_terms_tl t
        WHERE 1 = 1
        and   v.GLOBAL_ATTRIBUTE1 = '{unique_partner_identifier}' -- Внешний входящий параметр Front end, соответствия между порталом и OEBS. PCS - uniquePartnerIdentifier
        AND   v.VENDOR_ID = s.VENDOR_ID 
    --    and   s.vendor_id = 18130
        AND   s.org_id IN (82, 224)
        AND   nvl(s.INACTIVE_DATE,sysdate+1) >= SYSDATE 
        AND   nvl(v.END_DATE_ACTIVE,sysdate+1) >= sysdate
        AND   t."LANGUAGE" = 'RU'
        AND   t.TERM_ID = s.TERMS_ID 
        AND   CAS.attribute7 = s.VENDOR_SITE_CODE
        AND   a.CUST_ACCOUNT_ID  = cas.CUST_ACCOUNT_ID
        AND   a.status = 'A'
        AND   p.PARTY_ID = a.PARTY_ID
           ), 
    flex_values_description AS (
    SELECT f.FLEX_VALUE, f.DESCRIPTION
    FROM apps.FND_FLEX_VALUES_VL f 
    WHERE 1 = 1
    and   f.FLEX_VALUE_SET_ID = 1013414
    )
    SELECT  /*+ ORDERED PARALLEL(8) */ i.invoice_num "Номер счета", 
            nvl(to_date(i.attribute7, 'YYYY/MM/DD HH24:MI:SS'), 
            i.invoice_date) "Дата счета", 
            i.description "Внутр. номер", 
            i.attribute1 "Номер магазина", 
            (SELECT DISTINCT fvd.DESCRIPTION FROM flex_values_description fvd WHERE fvd.FLEX_VALUE = i.attribute1) AS "Наимен. маг-на",
            ps.DUE_DATE "Срок оплаты",
            nvl(a.amount, ps.GROSS_AMOUNT) "Сумма к оплате",
            ps.amount_remaining "Ост. оплатить", 
            a.FACTUAL_REQ_DATE AS Дата_заявки, 
            a.FACTUAL_REQ_NUM AS Номер_заявки,
            nvl((select 'Заблокирован для оплаты' from ap.ap_holds_all h
                where h.invoice_id = i.invoice_id
                and   h.release_lookup_code is null
                and   rownum = 1), 'Ожидает оплату') "Статус счета",
            a.PLANNED_DATE "Дата платежа", 
            aca.CHECK_NUMBER "Номер п/п",
            aca.AMOUNT "Сумма платежа"
    from vendors v, ap.ap_invoices_all i , AP.ap_payment_schedules_all ps, 
         ap.AP_INVOICE_PAYMENTS_ALL aipa, ap.AP_CHECKS_ALL aca, xxt.xxt_bc_factual_req_headers_all a
    where 1=1
    AND   v.org_id IN (82, 224)
    AND i.vendor_id = v.vendor_id
    AND i.invoice_num LIKE CONCAT('{num}', '%') -- внешний параметр от Front END, поисковое значение номера счета 
    AND ps.invoice_id = i.invoice_id
    AND a.invoice_id(+) = i.invoice_id
    AND aipa.INVOICE_ID = ps.INVOICE_ID
    AND aipa.payment_num = ps.payment_num
    AND aipa.REVERSAL_FLAG = 'N'    --обязательный флаг для фильтрации номера п/п
    AND aca.CHECK_ID = aipa.CHECK_ID 
    AND aca.CHECK_NUMBER LIKE CONCAT('%', '{check_num}')  -- Внешний параметр номера п/п.
    """
    cur.execute(request)
    results = cur.fetchall()
    results = jsonable_encoder(results)
    results = re_format_cycle(results)
    results = jsonable_encoder(results)
    return JSONResponse(content=results)


@app.get("/paid-invoices")
def get_paid_invoices(data: DataValidation = Depends()):
    oracledb.init_oracle_client(lib_dir=PATH_LIB)
    conn = oracledb.connect(user=os.getenv('USER'), password=os.getenv('PASSWORD'), host=os.getenv('HOST'),
                            port=os.getenv('PORT'), service_name=os.getenv('SERVICE_NAME'))
    cur = conn.cursor()
    request = f"""
    -----------------------------------
    --Список оплаченных счетов version_7
    -----------------------------------
    with vendors as (
        SELECT DISTINCT v.segment1, v.vendor_id, s.ORG_ID, decode(nvl(v.ATTRIBUTE1,'0'),'0',s.VENDOR_SITE_CODE_ALT,p.PARTY_NAME) vendor_name, 
               v.GLOBAL_ATTRIBUTE1 uniquePartnerIdentifier, v.end_date_active, s.inactive_date, 
               v.VENDOR_TYPE_LOOKUP_CODE v_type, ltrim(decode(nvl(v.ATTRIBUTE1,'0'),'0',v.VAT_REGISTRATION_NUM,p.TAX_REFERENCE)) INN, nvl(v.ATTRIBUTE1,'0') fact
        FROM po.po_vendor_sites_all s, po.po_vendors v, ar.HZ_CUST_ACCT_SITES_ALL cas, ar.hz_cust_accounts a, ar.hz_parties p, ap.ap_terms_tl t
        WHERE 1 = 1
    --    and   s.vendor_id = 18130
        AND   s.org_id IN (82, 224)
        AND   nvl(s.INACTIVE_DATE,sysdate+1) >= SYSDATE 
        AND   v.VENDOR_ID = s.VENDOR_ID 
    --    and   v.GLOBAL_ATTRIBUTE1 = '10008118'
        AND   nvl(v.END_DATE_ACTIVE,sysdate+1) >= sysdate
        AND   t."LANGUAGE" = 'RU'
        AND   t.TERM_ID = s.TERMS_ID 
        AND   CAS.attribute7 = s.VENDOR_SITE_CODE
        AND   a.CUST_ACCOUNT_ID  = cas.CUST_ACCOUNT_ID
        AND   a.status = 'A'
        AND   p.PARTY_ID = a.PARTY_ID
           ), 
    flex_values_description AS (
    SELECT f.FLEX_VALUE, f.DESCRIPTION  
    FROM apps.FND_FLEX_VALUES_VL f 
    WHERE f.VALUE_CATEGORY = 'LM_RU_ENT_SI'
    )
    SELECT /*+ORDERED*/nvl(i.attribute6,i.invoice_num) "Номер счета", nvl(to_date(i.attribute7, 'YYYY/MM/DD HH24:MI:SS'), i.invoice_date) "Дата счета", 
           i.description "Внутр. номер", i.attribute1 "Номер магазина", (SELECT DISTINCT fvd.DESCRIPTION FROM flex_values_description fvd WHERE fvd.FLEX_VALUE = i.attribute1) AS "Наимен. маг-на",
           a.PLANNED_DATE "Дата платежа",
           nvl(a.amount, ps.GROSS_AMOUNT) "Сумма к оплате", 
           ps.amount_remaining "Ост. оплатить", a.FACTUAL_REQ_DATE AS Дата_заявки, a.FACTUAL_REQ_NUM AS Номер_заявки,
           nvl((select 'Заблокирован для оплаты' from ap.ap_holds_all h
             where h.invoice_id = i.invoice_id
             and   h.release_lookup_code is null
             and   rownum = 1), 'Ожидает оплату') "Статус счета"
    from vendors v, ap.ap_invoices_all i , AP.ap_payment_schedules_all ps, xxt.xxt_bc_factual_req_headers_all a
    WHERE 1=1 
    AND i.vendor_id = v.vendor_id
    AND ps.invoice_id = i.invoice_id
    AND a.invoice_id = i.invoice_id
    AND   v.org_id IN (82, 224) 
    AND   a.PLANNED_DATE between to_date('{data.date_from}','YYYY-MM-DD') and to_date('{data.date_to}','YYYY-MM-DD') -- Внешний параметh Front END (даты)
    AND   v.uniquePartnerIdentifier = {data.unique_partner_identifier}  -- параметр соответствия между порталом и OEBS. PCS - uniquePartnerIdentifier
    AND   a.status IN ('PAYMENT_CREATED')
    """
    cur.execute(request)
    results = cur.fetchall()
    results = jsonable_encoder(results)
    results = re_format_cycle(results)
    results = jsonable_encoder(results)
    return JSONResponse(content=results)


@app.get("/invoices-confirmed-for-payment")
def get_invoices_confirmed_for_payment(data: DataValidation = Depends()):
    oracledb.init_oracle_client(lib_dir=PATH_LIB)
    conn = oracledb.connect(user=os.getenv('USER'), password=os.getenv('PASSWORD'), host=os.getenv('HOST'),
                            port=os.getenv('PORT'), service_name=os.getenv('SERVICE_NAME'))
    cur = conn.cursor()
    request = f"""
    -----------------------------------
    --Список счетов подтвержденных к оплате version_7
    -----------------------------------
    with vendors as (
        SELECT DISTINCT v.segment1, v.vendor_id, s.ORG_ID, decode(nvl(v.ATTRIBUTE1,'0'),'0',s.VENDOR_SITE_CODE_ALT,p.PARTY_NAME) vendor_name, 
               v.GLOBAL_ATTRIBUTE1 uniquePartnerIdentifier, v.end_date_active, s.inactive_date, 
               v.VENDOR_TYPE_LOOKUP_CODE v_type, ltrim(decode(nvl(v.ATTRIBUTE1,'0'),'0',v.VAT_REGISTRATION_NUM,p.TAX_REFERENCE)) INN, nvl(v.ATTRIBUTE1,'0') fact
        FROM po.po_vendor_sites_all s, po.po_vendors v, ar.HZ_CUST_ACCT_SITES_ALL cas, ar.hz_cust_accounts a, ar.hz_parties p, ap.ap_terms_tl t
        WHERE 1 = 1
    --    and   s.vendor_id = 18130
        AND   s.org_id IN (82, 224)
        AND   nvl(s.INACTIVE_DATE,sysdate+1) >= SYSDATE 
        AND   v.VENDOR_ID = s.VENDOR_ID 
    --    and   v.GLOBAL_ATTRIBUTE1 = '10008118'
        AND   nvl(v.END_DATE_ACTIVE,sysdate+1) >= sysdate
        AND   t."LANGUAGE" = 'RU'
        AND   t.TERM_ID = s.TERMS_ID 
        AND   CAS.attribute7 = s.VENDOR_SITE_CODE
        AND   a.CUST_ACCOUNT_ID  = cas.CUST_ACCOUNT_ID
        AND   a.status = 'A'
        AND   p.PARTY_ID = a.PARTY_ID
           ), 
    flex_values_description AS (
    SELECT f.FLEX_VALUE, f.DESCRIPTION  
    FROM apps.FND_FLEX_VALUES_VL f 
    WHERE f.VALUE_CATEGORY = 'LM_RU_ENT_SI'
    )
    SELECT /*+ORDERED*/nvl(i.attribute6,i.invoice_num) "Номер счета", nvl(to_date(i.attribute7, 'YYYY/MM/DD HH24:MI:SS'), i.invoice_date) "Дата счета", 
           i.description "Внутр. номер", i.attribute1 "Номер магазина", (SELECT DISTINCT fvd.DESCRIPTION FROM flex_values_description fvd WHERE fvd.FLEX_VALUE = i.attribute1) AS "Наимен. маг-на",
           a.PLANNED_DATE "Дата платежа", 
           nvl(a.amount, ps.GROSS_AMOUNT) "Сумма к оплате", 
           ps.amount_remaining "Ост. оплатить", a.FACTUAL_REQ_DATE AS Дата_заявки, a.FACTUAL_REQ_NUM AS Номер_заявки,
           nvl((select 'Заблокирован для оплаты' from ap.ap_holds_all h
             where h.invoice_id = i.invoice_id
             and   h.release_lookup_code is null
             and   rownum = 1), 'Ожидает оплату') "Статус счета"
    from vendors v, ap.ap_invoices_all i , AP.ap_payment_schedules_all ps, xxt.xxt_bc_factual_req_headers_all a
    where 1=1 
    AND i.vendor_id = v.vendor_id
    and ps.invoice_id = i.invoice_id
    AND a.invoice_id(+) = i.invoice_id
    and   v.org_id IN (82, 224)  
    and   a.PLANNED_DATE between to_date('{data.date_from}','YYYY-MM-DD') and to_date('{data.date_to}','YYYY-MM-DD') -- Внешний параметр Front END (даты)
    AND   v.uniquePartnerIdentifier = {data.unique_partner_identifier}  -- параметр соответствия между порталом и OEBS. PCS - uniquePartnerIdentifier
    AND nvl(i.PAYMENT_STATUS_FLAG, 'N') != 'Y'
    """
    cur.execute(request)
    results = cur.fetchall()
    results = jsonable_encoder(results)
    results = re_format_cycle(results)
    results = jsonable_encoder(results)
    return JSONResponse(content=results)


if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=8000, workers=True)
