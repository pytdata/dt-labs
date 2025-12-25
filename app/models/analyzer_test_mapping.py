from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class AnalyzerTestMapping(Base):
    __tablename__ = "analyzer_test_mapping"

    id = Column(Integer, primary_key=True, index=True)
    analyzer_id = Column(Integer, ForeignKey("analyzer.id"))
    test_id = Column(Integer, ForeignKey("test.id"))

    analyzer = relationship("Analyzers", back_populates="test_mappings")
    test = relationship("Tests", back_populates="analyzer_mappings")

