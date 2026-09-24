"""
Database connection helpers for the Streamlit dashboard.

Reads Postgres credentials from the .env file at the repo root (same
credentials used by psql and the notebooks). Cached so every page in
this multipage app shares one connection pool and repeated queries
don't re-hit Postgres on every rerun.
"""

import os

import pandas as pd
import streamlit as st
from dotenv import find_dotenv, load_dotenv
from sqlalchemy import create_engine

load_dotenv(find_dotenv())


@st.cache_resource
def get_engine():
    return create_engine(
        f"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
        f"@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}"
    )


@st.cache_data(ttl=600)
def run_query(sql: str) -> pd.DataFrame:
    return pd.read_sql(sql, get_engine())
