"""
MySQL (AWS RDS 포함) 연결용 헬퍼.

- pymysql을 사용해서 커넥션을 만든다.
- cursorclass=DictCursor 로 해서 결과를 dict로 받게 함.
"""

import pymysql
from pymysql.cursors import DictCursor

import config


def get_conn():
    """
    DB 커넥션 생성.
    사용 후 conn.close() 꼭 호출해야 함.
    """
    if not config.DB_HOST or not config.DB_USER:
        raise RuntimeError("DB 환경변수(DB_HOST, DB_USER 등)가 설정되지 않았습니다.")

    conn = pymysql.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        cursorclass=DictCursor,
        autocommit=False,
        charset="utf8mb4",
    )
    return conn