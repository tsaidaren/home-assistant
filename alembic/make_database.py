import os

from sqlalchemy import create_engine

from homeassistant.components.recorder.models import Base

if os.path.exists("alembic/homeassistant-v2.db"):
    os.unlink("alembic/homeassistant-v2.db")

engine = create_engine("sqlite:///alembic/homeassistant-v2.db")
Base.metadata.create_all(engine)
