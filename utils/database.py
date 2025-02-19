import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, List, Dict, Any
import os
import logging
from dotenv import load_dotenv
from contextlib import contextmanager

load_dotenv()  

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class DatabaseConfig:
    def __init__(
        self,
        host: str = os.getenv("DB_HOST", "localhost"),
        port: str = os.getenv("DB_PORT", "5432"),
        database: str = os.getenv("DB_NAME", "postgres"),
        user: str = os.getenv("DB_USER", "postgres"),
        password: str = os.getenv("DB_PASSWORD", ""),
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password

class Database:
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._conn = None
        # logger.info(f"DB HOST: {config.host}")
        # logger.info(f"DB port: {config.port}")
        # logger.info(f"DB database: {config.database}")
        # logger.info(f"DB user: {config.user}")
        # logger.info(f"DB password: {config.password}")

    @contextmanager
    def connection(self):
        """Context manager for database connections"""
        try:
            conn = psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password
            )
            yield conn
        finally:
            if conn is not None:
                conn.close()

    @contextmanager
    def cursor(self):
        """Context manager for database cursors"""
        with self.connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            try:
                yield cursor
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()

    def execute(self, query: str, params: Optional[tuple] = None) -> None:
        """Execute a query without returning results"""
        with self.cursor() as cursor:
            cursor.execute(query, params)

    def fetch_one(self, query: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        """Fetch a single row from the database"""
        with self.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()

    def fetch_all(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Fetch all rows from the database"""
        with self.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()

    def insert(self, table: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Insert a row into the database and return the inserted row"""
        columns = list(data.keys())
        values = list(data.values())
        placeholders = [f'%s' for _ in values]
        
        query = f"""
            INSERT INTO {table} ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            RETURNING *
        """
        
        return self.fetch_one(query, tuple(values))

    def update(self, table: str, data: Dict[str, Any], where: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update rows in the database and return the updated row"""
        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        where_clause = ' AND '.join([f"{k} = %s" for k in where.keys()])
        
        query = f"""
            UPDATE {table}
            SET {set_clause}
            WHERE {where_clause}
            RETURNING *
        """
        
        params = tuple(list(data.values()) + list(where.values()))
        return self.fetch_one(query, params)

    def delete(self, table: str, where: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Delete rows from the database and return the deleted row"""
        where_clause = ' AND '.join([f"{k} = %s" for k in where.keys()])
        
        query = f"""
            DELETE FROM {table}
            WHERE {where_clause}
            RETURNING *
        """
        
        return self.fetch_one(query, tuple(where.values()))
    
    
    def upsert(self, table: str, data: Dict[str, Any], where: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Upsert a record into the database and return the upserted record"""
        # First, delete the record if it exists
        # where_clause = ' AND '.join([f"{k} = %s" for k in where.keys()])
        # delete_query = f"""
        #     DELETE FROM {table}
        #     WHERE {where_clause}
        #     RETURNING *
        # """
        # delete_params = tuple(where.values())
        # self.fetch_one(delete_query, delete_params)

        self.delete(table, where)
        return self.insert(table, data)

        # # Then, insert the record
        # columns = list(data.keys())
        # values = list(data.values())
        # placeholders = [f'%s' for _ in values]
        # insert_query = f"""
        #     INSERT INTO {table} ({', '.join(columns)})
        #     VALUES ({', '.join(placeholders)})
        #     RETURNING *
        # """
        # logger.debug(insert_query)
        # logger.debug(values)

        # return self.fetch_one(insert_query, values)
