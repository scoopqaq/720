from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category = Column(String, default="其他")
    cover_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Project 关联 Groups
    groups = relationship("SceneGroup", back_populates="project", cascade="all, delete-orphan")
    # 也可以通过 group 间接关联 scenes，或者保留 direct 关联方便查询
    # 这里我们主要通过 groups 来管理 scenes

class SceneGroup(Base):
    __tablename__ = "scene_groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String) # 例如：一楼、二楼
    project_id = Column(Integer, ForeignKey("projects.id"))
    
    project = relationship("Project", back_populates="groups")
    scenes = relationship("Scene", back_populates="group", cascade="all, delete-orphan")

class Scene(Base):
    __tablename__ = "scenes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    image_url = Column(String)
    cover_url = Column(String, nullable=True)
    
    # [修改] 关联到 Group 而不是直接关联 Project (虽然逻辑上属于Project)
    group_id = Column(Integer, ForeignKey("scene_groups.id"))
    
    # 视角配置 (保持不变)
    initial_heading = Column(Float, default=0.0)
    initial_pitch = Column(Float, default=0.0)
    fov_min = Column(Float, default=70.0)
    fov_max = Column(Float, default=120.0)
    fov_default = Column(Float, default=95.0)
    limit_h_min = Column(Float, default=-180.0)
    limit_h_max = Column(Float, default=180.0)
    limit_v_min = Column(Float, default=-90.0)
    limit_v_max = Column(Float, default=90.0)
    
    group = relationship("SceneGroup", back_populates="scenes")
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