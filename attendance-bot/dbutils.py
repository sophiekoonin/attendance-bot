from urllib import parse
import psycopg2
import os

def connect_to_db():
    parse.uses_netloc.append("postgres")
    url = parse.urlparse(os.environ["DATABASE_URL"])

    return psycopg2.connect(
        database=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port
    )

def commit_or_rollback(db):
    try:
        db.commit()
    except Exception as e:
        db.rollback()
    finally:
        pass

def execute_with_cursor(db, query, *args):
    cur = db.cursor()
    cur.execute(query, args)
    return cur

def execute_fetchone(db, query, *args):
    return execute_with_cursor(db, query, *args).fetchone()

def execute_fetchall(db, query, *args):
    return execute_with_cursor(db, query, *args).fetchall()
