PATH_LIB = r'C:\oracle\instantclient_23_6'

PARAMETERS = f"""(DESCRIPTION=
                (ADDRESS=(PROTOCOL=tcp)(HOST=oxlrd1db01-vip.hq.ru.corp.leroymerlin.com)(PORT=1562))
            (CONNECT_DATA=
                (SERVICE_NAME=GSS1RU)
                (INSTANCE_NAME=gss1ru1)
            )
        )"""
