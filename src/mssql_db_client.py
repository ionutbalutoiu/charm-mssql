"""
Helpers for the Microsoft SQL Server charm.
"""

import logging

from pymssql import connect

from utils import retry_on_error

logger = logging.getLogger(__name__)


class MSSQLDatabaseClient(object):

    def __init__(self, user, password, host="localhost", port=1433):
        self._user = user
        self._password = password
        self._host = host
        self._port = port

    @retry_on_error()
    def _connection(self):
        return connect(server=self._host,
                       port=self._port,
                       user=self._user,
                       password=self._password)

    def create_database(self, db_name):
        conn = self._connection()
        conn.autocommit(True)
        cursor = conn.cursor()
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = '{db_name}')
        BEGIN
            CREATE DATABASE {db_name}
        END
        """.format(db_name=db_name))
        conn.close()

    def create_login(self, login_name, login_password):
        conn = self._connection()
        cursor = conn.cursor()
        cursor.execute("""
        IF NOT EXISTS(SELECT * FROM sys.syslogins WHERE name = '{login_name}')
        BEGIN
            CREATE LOGIN {login_name} WITH PASSWORD = '{login_password}',
                                           CHECK_EXPIRATION=OFF
        END
        ELSE
        BEGIN
            ALTER LOGIN {login_name} WITH PASSWORD = '{login_password}',
                                          CHECK_EXPIRATION=OFF
        END
        """.format(login_name=login_name, login_password=login_password))
        conn.commit()
        conn.close()

    def grant_access(self, db_name, db_user_name, login_name=None):
        if not login_name:
            login_name = db_user_name
        conn = self._connection()
        cursor = conn.cursor()
        cursor.execute("""
        USE {db_name}
        IF NOT EXISTS(SELECT * FROM sys.sysusers WHERE name = '{db_user_name}')
        BEGIN
            CREATE USER {db_user_name} FOR LOGIN {login_name}
        END
        ALTER ROLE db_owner ADD MEMBER {db_user_name}
        """.format(db_name=db_name,
                   db_user_name=db_user_name,
                   login_name=login_name))
        conn.commit()
        conn.close()

    def revoke_access(self, db_name, db_user_name):
        conn = self._connection()
        cursor = conn.cursor()
        cursor.execute("""
        USE {db_name}
        DROP USER IF EXISTS {db_user_name}
        """.format(db_name=db_name, db_user_name=db_user_name))
        conn.commit()
        conn.close()
