# -*- coding: utf-8 -*-
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

# URI do Supabase (Transaction pooler)
DATABASE_URL = "postgresql://postgres.yfxfmwrasjukbsjjqbzs:kaio82046697@aws-1-us-west-2.pooler.supabase.com:6543/postgres"

print("Testando conexao com Supabase...")
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"connect_timeout": 10})
try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        print("CONECTADO:", result.fetchone())
except Exception as e:
    print("ERRO:", e)
    raise
