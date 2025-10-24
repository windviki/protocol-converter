from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class ProtocolFamily(Base):
    """协议族模型"""
    __tablename__ = 'protocol_families'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False, comment='协议族名称')
    description = Column(Text, comment='协议族描述')
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 关系
    protocols = relationship("Protocol", back_populates="family", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ProtocolFamily(name='{self.name}')>"


class Protocol(Base):
    """协议模板模型"""
    __tablename__ = 'protocols'
    
    id = Column(Integer, primary_key=True)
    protocol_id = Column(String(100), nullable=False, comment='协议ID，如A-1')
    family_id = Column(Integer, ForeignKey('protocol_families.id'), nullable=False, comment='协议族ID')
    template_content = Column(Text, nullable=False, comment='Jinja2模板内容')
    raw_schema = Column(Text, nullable=False, comment='原始JSON Schema')
    variables = Column(Text, comment='提取的变量列表，JSON格式')
    special_variables = Column(Text, comment='特殊变量列表，JSON格式')
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 关系
    family = relationship("ProtocolFamily", back_populates="protocols")
    
    # 索引
    __table_args__ = (
        Index('idx_protocol_id', 'protocol_id'),
        Index('idx_family_id', 'family_id'),
    )
    
    def __repr__(self):
        return f"<Protocol(protocol_id='{self.protocol_id}', family='{self.family.name}')>"


class ConversionLog(Base):
    """转换日志模型"""
    __tablename__ = 'conversion_logs'
    
    id = Column(Integer, primary_key=True)
    source_protocol = Column(String(100), nullable=False, comment='源协议ID')
    target_protocol = Column(String(100), nullable=False, comment='目标协议ID')
    source_json = Column(Text, nullable=False, comment='源JSON内容')
    target_json = Column(Text, comment='目标JSON内容')
    variables_kv = Column(Text, comment='提取的变量键值对，JSON格式')
    matched_protocol = Column(String(100), comment='匹配的协议ID')
    conversion_time = Column(DateTime, default=datetime.utcnow, comment='转换时间')
    success = Column(Integer, default=1, comment='是否成功，1成功，0失败')
    error_message = Column(Text, comment='错误信息')
    
    def __repr__(self):
        return f"<ConversionLog(from='{self.source_protocol}', to='{self.target_protocol}')>"