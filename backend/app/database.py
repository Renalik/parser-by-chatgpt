from sqlalchemy import create_engine, Column, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from .settings import settings
import json

engine = create_engine(
    settings.database_url,
    connect_args=(
        {"check_same_thread": False}
        if settings.database_url.startswith("sqlite")
        else {}
    ),
)
Session = sessionmaker(bind=engine)
Base = declarative_base()


class Record(Base):
    __tablename__ = "records"
    key = Column(String, primary_key=True)
    kind = Column(String, index=True)
    body = Column(Text, nullable=False)


Base.metadata.create_all(engine)


def put(kind, key, data):
    with Session.begin() as s:
        s.merge(Record(key=key, kind=kind, body=json.dumps(data, ensure_ascii=False)))


def get(key):
    with Session() as s:
        row = s.get(Record, key)
        return json.loads(row.body) if row else None


def all_records(kind):
    with Session() as s:
        return [json.loads(r.body) for r in s.query(Record).filter_by(kind=kind).all()]


def delete(key):
    with Session.begin() as s:
        r = s.get(Record, key)
        if r:
            s.delete(r)
