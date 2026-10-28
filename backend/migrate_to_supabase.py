import json
from sqlalchemy import create_engine, text
import psycopg2.extensions
import psycopg2.extras
from app.config import settings
from app.database import Base
import app.models

# Enable JSON serialization in psycopg2
psycopg2.extensions.register_adapter(dict, psycopg2.extras.Json)
psycopg2.extensions.register_adapter(list, psycopg2.extras.Json)

sqlite_url = 'sqlite:///./storage/aicte.db'
pg_url = settings.DATABASE_URL

print(f'Connecting to SQLite ({sqlite_url}) and PostgreSQL...')
sqlite_engine = create_engine(sqlite_url)
pg_engine = create_engine(pg_url)

# Recreate tables in Supabase PG
Base.metadata.create_all(bind=pg_engine)

tables_in_order = [
    'institutions',
    'institution_histories',
    'applications',
    'documents',
    'extracted_fields',
    'auth_results',
    'rule_results',
    'consistency_results',
    'deficiency_reports',
    'reviews',
    'audit_logs'
]

boolean_cols = {'needs_verification', 'passed'}

with sqlite_engine.connect() as s_conn, pg_engine.connect() as p_conn:
    print('Truncating existing Supabase tables...')
    for tbl in reversed(tables_in_order):
        p_conn.execute(text(f'TRUNCATE TABLE {tbl} CASCADE;'))
    p_conn.commit()

    print('Copying data from SQLite to Supabase...')
    for tbl in tables_in_order:
        rows = s_conn.execute(text(f'SELECT * FROM {tbl}')).fetchall()
        if not rows:
            print(f' - {tbl}: 0 rows')
            continue
        cols = rows[0]._fields
        col_names = ', '.join(cols)
        val_placeholders = ', '.join([f':{c}' for c in cols])
        insert_sql = text(f'INSERT INTO {tbl} ({col_names}) VALUES ({val_placeholders})')
        
        row_dicts = []
        for r in rows:
            d = dict(r._mapping)
            for k, v in d.items():
                if k in boolean_cols and v is not None:
                    d[k] = bool(v)
                elif isinstance(v, str) and ((v.startswith('{') and v.endswith('}')) or (v.startswith('[') and v.endswith(']'))):
                    try:
                        d[k] = json.loads(v)
                    except Exception:
                        pass
            row_dicts.append(d)
            
        p_conn.execute(insert_sql, row_dicts)
        p_conn.commit()
        print(f' - {tbl}: {len(row_dicts)} rows migrated')
        
        # Reset sequence for autoincrement ID if id column exists
        if 'id' in cols:
            p_conn.execute(text(f"SELECT setval(pg_get_serial_sequence('{tbl}', 'id'), COALESCE((SELECT MAX(id) FROM {tbl}), 1));"))
            p_conn.commit()

print('ALL DATA MIGRATED TO SUPABASE SUCCESSFULLY!')
