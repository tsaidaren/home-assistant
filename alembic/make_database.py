from sqlalchemy import create_engine

from homeassistant.components.recorder.models import Base

engine = create_engine("sqlite:///alembic/homeassistant-v2.db")
Base.metadata.create_all(engine)
