import os

from sqlalchemy import create_engine

from homeassistant.components.recorder.models import ALL_TABLES, Base

engine = create_engine("sqlite:///alembic/homeassistant-v2.db")


for table in ALL_TABLES:
   engine.execute(f"DROP TABLE IF EXISTS {table};")

Base.metadata.create_all(engine)
