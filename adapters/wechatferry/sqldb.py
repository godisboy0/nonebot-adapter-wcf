import sqlite3
from sqlite3 import Connection
import os
import logging
import threading

logger = logging.getLogger(__name__)

singleton_dict = threading.local()

class database:

    def __init__(self, file_path, db_name="wcf") -> None:
        ## 如果同参数
        global singleton_dict
        if hasattr(singleton_dict, file_path):
            self.conn = getattr(singleton_dict, file_path)
            return
        
        if not file_path:
            raise ValueError("file_path can not be empty")
        if not os.path.exists(file_path):
            os.makedirs(file_path, exist_ok=True)
        
        datafile = os.path.join(file_path, db_name)
        self.conn = sqlite3.connect(datafile)
        singleton_dict.file_path = self.conn

    def create_table(self, sql: str) -> None:
        cursor = self.conn.cursor()
        try:
            cursor.execute(sql)
            self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to create table: {e}")
            raise e
        finally:
            cursor.close()

    def query(self, sql, *args) -> list:
        cursor = self.conn.cursor()
        try:
            cursor.execute(sql, args)
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to query: {e}")
            raise e
        finally:
            cursor.close()

    def execute(self, sql: str, *args) -> None:
        cursor = self.conn.cursor()
        try:
            cursor.execute(sql, args)
            self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to execute: {e}")
            raise e
        finally:
            cursor.close()

    def insert(self, sql: str, *args) -> None:
        cursor = self.conn.cursor()
        try:
            cursor.execute(sql, args)
            self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to insert: {e}")
            raise e
        finally:
            cursor.close()

    def update(self, sql: str, *args) -> None:
        cursor = self.conn.cursor()
        try:
            cursor.execute(sql, args)
            self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to update: {e}")
            raise e
        finally:
            cursor.close()

    def delete(self, sql: str, *args) -> None:
        cursor = self.conn.cursor()
        try:
            cursor.execute(sql, args)
            self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to delete: {e}")
            raise e
        finally:
            cursor.close()

    def table_exists(self, table_name: str) -> bool:
        sql = f"SELECT count(*) FROM sqlite_master WHERE type='table' AND name='{table_name}'"
        cursor = self.conn.cursor()
        try:
            cursor.execute(sql)
            return cursor.fetchone()[0] == 1
        except Exception as e:
            logger.error(f"Failed to check table {table_name} exists: {e}")
            return False
        finally:
            cursor.close()
