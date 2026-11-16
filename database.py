from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from config import database_url

engine = create_async_engine(database_url, echo=True)
Session = async_sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()
