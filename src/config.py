"""
config.py

Database connection configuration.
Reads credentials from environment variables (set via .env / docker-compose).
"""
import os


def get_db_config() -> dict:
    my_dict = {
       "host": os.getenv("DB_HOST", "db"),  
       "port": int(os.getenv("DB_PORT", "5432")),
       "dbname": os.getenv("POSTGRES_DB"),
       "user": os.getenv("POSTGRES_USER"),
       "password": os.getenv("POSTGRES_PASSWORD")
    }
    return my_dict
