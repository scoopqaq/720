from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

# 1. 用户表 (登录功能基础)
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.now)

    # 关联
    projects = relationship("Project", back_populates="owner")
    icons = relationship("HotspotIcon", back_populates="owner")

# 2. 图标库表 (用户隔离)
class HotspotIcon(Base):
    __tablename__ = "hotspot_icons"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    url = Column(String)
    category = Column(String) # 'system' | 'custom'
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    owner = relationship("User", back_populates="icons")
    created_at = Column(DateTime, default=datetime.now)

# 3. 项目表 (带 owner_id)
class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category = Column(String, default="其他")
    cover_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 归属用户
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="projects")

    groups = relationship("SceneGroup", back_populates="project", cascade="all, delete-orphan")

# 4. 分组表
class SceneGroup(Base):
    __tablename__ = "scene_groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    project_id = Column(Integer, ForeignKey("projects.id"))
    
    project = relationship("Project", back_populates="groups")
    scenes = relationship("Scene", back_populates="group", cascade="all, delete-orphan")

# 5. 场景表 (含排序、视角参数)
class Scene(Base):
    __tablename__ = "scenes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    image_url = Column(String)
    cover_url = Column(String, nullable=True)
    group_id = Column(Integer, ForeignKey("scene_groups.id"))
    sort_order = Column(Integer, default=0, index=True)
    
    # 视角参数
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

# 6. 热点表 (包含详细样式与类型)
class Hotspot(Base):
    __tablename__ = "hotspots"
    id = Column(Integer, primary_key=True, index=True)
    
    x = Column(Float)
    y = Column(Float)
    z = Column(Float)
    
    text = Column(String, nullable=True)
    type = Column(String, default="scene") # scene, link, text, image, video
    content = Column(Text, nullable=True) 
    target_scene_id = Column(Integer, ForeignKey("scenes.id"), nullable=True)
    
    # 样式
    icon_type = Column(String, default="system")
    icon_url = Column(String, default="arrow_move") 
    scale = Column(Float, default=1.0)
    use_fixed_size = Column(Boolean, default=False)
    
    source_scene_id = Column(Integer, ForeignKey("scenes.id"))
    source_scene = relationship("Scene", foreign_keys=[source_scene_id], back_populates="hotspots")