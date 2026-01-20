from sqlalchemy import create_engine

ENGINE = create_engine(
    "sqlite:///calendar.db",
    echo=True,
    future=True,
)
