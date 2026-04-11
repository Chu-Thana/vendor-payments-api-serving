import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_redshift_connection():
    host = os.getenv("REDSHIFT_HOST")
    port = int(os.getenv("REDSHIFT_PORT", "5439"))
    dbname = os.getenv("REDSHIFT_DB", "dev")
    user = os.getenv("REDSHIFT_USER")
    password = os.getenv("REDSHIFT_PASSWORD")

    if not all([host, user, password]):
        raise ValueError("Missing Redshift environment variables.")

    return psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
    )