from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, JSON, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class SSOTFieldMapping(Base):
    """
    Defines mappings between SSOT fields and platform-specific fields for transformation.
    
    This table provides a configurable way to map fields from SSOT format to platform-specific
    formats (e.g., Zoom) for different job types and entities.
    """
    __tablename__ = "ssot_field_mappings"
    
    id = Column(Integer, primary_key=True)
    job_type_id = Column(Integer, nullable=False, index=True)
    source_platform = Column(String(50), nullable=False)  # Always 'ssot' for this implementation
    target_entity = Column(String(50), nullable=False)    # E.g., 'user', 'site', 'call_queue'
    ssot_field = Column(String(100), nullable=False)      # Source field name in SSOT
    target_field = Column(String(100), nullable=False)    # Target field name in Zoom
    transformation_rule = Column(String(200))             # Optional transformation logic
    is_required = Column(Boolean, default=False)          # Whether this field is required
    description = Column(Text)                            # Description of the mapping
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


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


class ExtractorConfig(Base):
    """
    Registry for storing extraction plans generated by the LLM.
    
    This model stores extraction plans for specific job types.
    Mirrors the ExtractorRegistry model in the etl_prism_poc Django application.
    """
    __tablename__ = "extractor_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, nullable=False, index=True)
    job_type_id = Column(Integer, nullable=False, index=True)
    platform_id = Column(Integer, nullable=False, index=True)
    extraction_plan = Column(JSON, nullable=False)
    group_id = Column(Integer, nullable=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LoaderConfig(Base):
    """
    Registry for storing loading plans generated by the LLM.
    
    This model stores loading plans for specific job types.
    Mirrors the LoaderRegistry model in the etl_prism_poc Django application.
    """
    __tablename__ = "loader_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, nullable=False, index=True)
    job_type_id = Column(Integer, nullable=False, index=True)
    platform_id = Column(Integer, nullable=False, index=True)
    loading_plan = Column(JSON, nullable=False)
    group_id = Column(Integer, nullable=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TransformerConfig(Base):
    """
    Model for storing transformation configurations (formerly SSOT schemas).
    
    This model defines the transformation logic that serves as the
    intermediary between different platforms.
    Mirrors the SSOTSchema model in the etl_prism_poc Django application.
    """
    __tablename__ = "transformer_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    job_type_id = Column(Integer, nullable=False, index=True)
    transformation_config = Column(Text, nullable=False)  # YAML transformation config (was schema_yaml)
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    group_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_transformation_dict(self):
        """
        Get the transformation configuration as a Python dictionary.
        
        Returns:
            dict: The transformation configuration as a Python dictionary
        """
        import yaml
        return yaml.safe_load(self.transformation_config)


class JobTypeConfig(Base):
    """
    Represents a type of ETL job that can be performed.
    Mirrors the JobType model in the etl_prism_poc Django application.
    """
    __tablename__ = "job_type_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, nullable=False, index=True)
    code = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    source_platform_id = Column(Integer, nullable=True)
    target_platform_id = Column(Integer, nullable=True)
    prompt = Column(Text, nullable=True)
    is_extraction_only = Column(Boolean, default=False)
    jobtype_dependencies = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)