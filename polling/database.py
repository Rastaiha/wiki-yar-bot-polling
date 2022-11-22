from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from models import *

engine = create_engine('sqlite:///database.sqlite3', convert_unicode=True, echo=True)
Session = sessionmaker(bind=engine)
db_session = Session()

def init_db():
    
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
