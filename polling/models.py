from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship

Base = declarative_base()

class States:
    default = 'default'
    get_link = 'get_link'
    get_doc_id = 'get_doc_id'
    get_address = 'get_address'
    edit = 'edit'
    get_real_name = 'get_real_name'
    
    
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    persian_name = Column(String)
    real_name = Column(String)
    state = Column(String)
    tlg_id = Column(Integer)
    cache = Column(String)
    cache1 = Column(String)
    num_seen = Column(Integer)
    num_import = Column(Integer)
    num_edit = Column(Integer)

    files = relationship("File",  back_populates="user")


class File(Base):
    __tablename__ = 'files'

    id = Column(Integer, primary_key=True)
    page = Column(String)
    text = Column(String)


    user_id = Column(Integer, ForeignKey('users.id'))

    user = relationship("User", back_populates="files")
    
