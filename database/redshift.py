import os
import psycopg2


def get_redshift_connection():
    return psycopg2.connect(
        host=os.getenv("REDSHIFT_HOST"),
        port=int(os.getenv("REDSHIFT_PORT", "5439")),
        dbname=os.getenv("REDSHIFT_DB", "dev"),
        user=os.getenv("REDSHIFT_USER"),
        password=os.getenv("REDSHIFT_PASSWORD"),
    )