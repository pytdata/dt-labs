from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class AnalyzerTestMapping(Base):
    __tablename__ = "analyzer_test_mapping"

    id = Column(Integer, primary_key=True, index=True)
    analyzer_id = Column(Integer, ForeignKey("analyzers.id"))
    test_id = Column(Integer, ForeignKey("tests.id"))

    analyzer = relationship("Analyzer", back_populates="test_mappings")
    test = relationship("Test", back_populates="analyzer_mappings")
