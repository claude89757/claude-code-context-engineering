from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Version(Base):
    __tablename__ = "versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String, unique=True, nullable=False, index=True)
    detected_at = Column(DateTime, default=_utcnow, nullable=False)
    npm_metadata = Column(Text)  # stored as JSON string
    status = Column(String, default="detected", nullable=False)  # detected | testing | analyzed | error
    summary = Column(Text)

    test_runs = relationship("TestRun", back_populates="version", cascade="all, delete-orphan")
    diffs = relationship("VersionDiff", back_populates="version", foreign_keys="VersionDiff.version_id", cascade="all, delete-orphan")
    reports = relationship("AnalysisReport", back_populates="version", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Version {self.version}>"


class TestRun(Base):
    __tablename__ = "test_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version_id = Column(Integer, ForeignKey("versions.id"), nullable=False, index=True)
    scenario_key = Column(String, nullable=False)
    scenario_name = Column(String)
    scenario_group = Column(String)
    status = Column(String, default="pending", nullable=False)  # pending | running | success | error
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    raw_jsonl = Column(Text)  # file path or inline content
    error_message = Column(Text)

    version = relationship("Version", back_populates="test_runs")
    extracted_data = relationship("ExtractedData", back_populates="test_run", cascade="all, delete-orphan", uselist=False)

    def __repr__(self):
        return f"<TestRun {self.scenario_key} v{self.version_id}>"


class ExtractedData(Base):
    __tablename__ = "extracted_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    test_run_id = Column(Integer, ForeignKey("test_runs.id"), nullable=False, unique=True, index=True)
    system_prompt = Column(Text)
    system_blocks = Column(Text)  # JSON
    tools = Column(Text)  # JSON
    tool_names = Column(Text)  # JSON
    deferred_tools = Column(Text)  # JSON
    messages_chain = Column(Text)  # JSON
    api_calls = Column(Text)  # JSON
    system_reminders = Column(Text)  # JSON
    cache_strategy = Column(Text)  # JSON
    token_usage = Column(Text)  # JSON
    model_used = Column(String)

    test_run = relationship("TestRun", back_populates="extracted_data")

    def __repr__(self):
        return f"<ExtractedData run={self.test_run_id}>"


class VersionDiff(Base):
    __tablename__ = "version_diffs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version_id = Column(Integer, ForeignKey("versions.id"), nullable=False, index=True)
    prev_version_id = Column(Integer, ForeignKey("versions.id"), nullable=False, index=True)
    scenario_key = Column(String, nullable=False)
    diff_type = Column(String)  # system_prompt | tools | tool_names | etc.
    diff_content = Column(Text)
    change_summary = Column(Text)
    significance = Column(String)  # low | medium | high | critical

    version = relationship("Version", back_populates="diffs", foreign_keys=[version_id])
    prev_version = relationship("Version", foreign_keys=[prev_version_id])

    def __repr__(self):
        return f"<VersionDiff {self.version_id} vs {self.prev_version_id}>"


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version_id = Column(Integer, ForeignKey("versions.id"), nullable=False, index=True)
    report_type = Column(String, nullable=False)  # version_summary | diff_analysis | etc.
    title = Column(String)
    content = Column(Text)
    model_used = Column(String)
    generated_at = Column(DateTime, default=_utcnow, nullable=False)
    token_cost = Column(Text)  # JSON

    version = relationship("Version", back_populates="reports")

    def __repr__(self):
        return f"<AnalysisReport {self.title}>"
