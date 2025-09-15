from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class ZoomCredential(Base):
    """
    Stores Zoom API credentials for authentication
    """
    __tablename__ = "zoom_credentials"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(String(255), unique=True, index=True)
    access_token = Column(Text)
    refresh_token = Column(Text)
    token_type = Column(String(50), default="bearer")
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    extract_jobs = relationship("ExtractJob", back_populates="credential")


class ExtractJob(Base):
    """
    Tracks data extraction jobs from Zoom API
    """
    __tablename__ = "extract_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(255), unique=True, index=True)
    credential_id = Column(Integer, ForeignKey("zoom_credentials.id"))
    resource_type = Column(String(100))  # meetings, recordings, users, etc.
    parameters = Column(JSON)  # Query parameters used for extraction
    status = Column(String(50))  # pending, in_progress, completed, failed
    result_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    credential = relationship("ZoomCredential", back_populates="extract_jobs")
    extracted_data = relationship("ExtractedData", back_populates="extract_job")


class ExtractedData(Base):
    """
    Stores data extracted from Zoom API
    """
    __tablename__ = "extracted_data"

    id = Column(Integer, primary_key=True, index=True)
    extract_job_id = Column(Integer, ForeignKey("extract_jobs.id"))
    resource_id = Column(String(255), index=True)  # Zoom resource ID
    resource_type = Column(String(100))  # meetings, recordings, users, etc.
    data = Column(JSON)  # Raw JSON data from Zoom API
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    extract_job = relationship("ExtractJob", back_populates="extracted_data")


class MCPRequest(Base):
    """
    Tracks Machine Communication Protocol requests
    """
    __tablename__ = "mcp_requests"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(255), unique=True, index=True)
    operation = Column(String(100))  # extract, transform, load, etc.
    parameters = Column(JSON)
    status = Column(String(50))  # pending, in_progress, completed, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    responses = relationship("MCPResponse", back_populates="request")


class MCPResponse(Base):
    """
    Stores responses to MCP requests
    """
    __tablename__ = "mcp_responses"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("mcp_requests.id"))
    status_code = Column(Integer)
    content = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    request = relationship("MCPRequest", back_populates="responses")