import psycopg2
from psycopg2 import pool as pg_pool

DB_PARAMS = dict(
    dbname="pechenka", user="postgres", password="0000",
    host="localhost", port="5432"
)

# Пул соединений создаётся лениво один раз на процесс.
_connection_pool = None


def get_pool(minconn=1, maxconn=10):
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = pg_pool.ConnectionPool(minconn, maxconn, **DB_PARAMS)
    return _connection_pool


class _PooledConnection:
    """Обёртка соединения из пула: контекст-менеджер с автоматическим
    commit/rollback и возвратом соединения в пул (API совместим с old get_connection)."""

    def __init__(self, conn):
        self._conn = conn

    def cursor(self, *args, **kwargs):
        return self._conn.cursor(*args, **kwargs)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    @property
    def autocommit(self):
        return self._conn.autocommit

    @autocommit.setter
    def autocommit(self, value):
        self._conn.autocommit = value

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is not None:
                self._conn.rollback()
            elif not self._conn.autocommit:
                try:
                    self._conn.commit()   # фиксируем незакрытые транзакции
                except psycopg2.Error:
                    self._conn.rollback()
        finally:
            get_pool().putconn(self._conn)  # соединение всегда возвращается в пул живым
        return False


def get_connection():
    """Быстрое получение соединения из пула (без нового TCP-хэндшейка)."""
    return _PooledConnection(get_pool().getconn())
