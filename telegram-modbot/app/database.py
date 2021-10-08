from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import os

print()
POSTGRES_USER = os.getenv('POSTGRES_USER')              ; print(POSTGRES_USER)
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')      ; print(POSTGRES_PASSWORD)
POSTGRES_SERVER = os.getenv('POSTGRES_SERVER')          ; print(POSTGRES_SERVER)
POSTGRES_PORT = os.getenv('POSTGRES_PORT')              ; print(POSTGRES_PORT)
POSTGRES_DB = os.getenv('POSTGRES_DB')                  ; print(POSTGRES_DB)

# https://docs.sqlalchemy.org/en/14/core/engines.html#database-urls
# URL format: dialect+driver://username:password@host:port/database
SQLALCHEMY_DATABASE_URL = f'postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}'
print(SQLALCHEMY_DATABASE_URL)
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(engine)

Base = declarative_base()

def get_db():
    db =SessionLocal()
    try:
        yield db
    finally:
        db.close()
