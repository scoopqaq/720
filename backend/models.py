from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
# 注意：我们要用 python 的 datetime，而不是 sqlalchemy 的 func
from datetime import datetime 
from database import Base

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category = Column(String, default="其他")
    cover_url = Column(String, nullable=True)
    
    # [修改] 改用 Python 的 datetime.now 获取本地时间
    # 这里的 default=datetime.now 是在插入时执行 Python 函数
    # onupdate=datetime.now 是在更新时执行 Python 函数
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    scenes = relationship("Scene", back_populates="project", cascade="all, delete-orphan")

class Scene(Base):
    __tablename__ = "scenes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    image_url = Column(String)
    cover_url = Column(String, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    
    # 视角配置
    initial_heading = Column(Float, default=0.0)
    initial_pitch = Column(Float, default=0.0)
    fov_min = Column(Float, default=70.0)
    fov_max = Column(Float, default=120.0)
    fov_default = Column(Float, default=95.0)
    limit_h_min = Column(Float, default=-180.0)
    limit_h_max = Column(Float, default=180.0)
    limit_v_min = Column(Float, default=-90.0)
    limit_v_max = Column(Float, default=90.0)
    
    project = relationship("Project", back_populates="scenes")
    hotspots = relationship("Hotspot", back_populates="source_scene", foreign_keys="Hotspot.source_scene_id", cascade="all, delete-orphan")

class Hotspot(Base):
    __tablename__ = "hotspots"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String)
    x = Column(Float)
    y = Column(Float)
    z = Column(Float)
    source_scene_id = Column(Integer, ForeignKey("scenes.id"))
    target_scene_id = Column(Integer, ForeignKey("scenes.id"))
    source_scene = relationship("Scene", foreign_keys=[source_scene_id], back_populates="hotspots")