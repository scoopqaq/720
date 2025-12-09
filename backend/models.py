from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category = Column(String, default="其他")
    # 项目封面图 (可能是某一个场景的截图)
    cover_url = Column(String, nullable=True)
    scenes = relationship("Scene", back_populates="project", cascade="all, delete-orphan")

class Scene(Base):
    __tablename__ = "scenes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    image_url = Column(String)
    # 场景专属封面 (如果不设置则用全景图缩略，设置了就用截图)
    cover_url = Column(String, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    
    # --- 核心全景参数 ---
    
    # 1. 初始视角 (Initial View)
    # 水平角度 (degrees, -180 ~ 180)
    initial_heading = Column(Float, default=0.0)
    # 垂直角度 (degrees, -90 ~ 90, 0是水平线)
    initial_pitch = Column(Float, default=0.0)
    
    # 2. FOV 设置 (Field of View)
    fov_min = Column(Float, default=70.0)  # 最近 (放大)
    fov_max = Column(Float, default=120.0) # 最远 (缩小)
    fov_default = Column(Float, default=95.0) # 初始 FOV
    
    # 3. 视角限制 (Limits)
    # 水平限制 (-180 ~ 180)
    limit_h_min = Column(Float, default=-180.0)
    limit_h_max = Column(Float, default=180.0)
    
    # 垂直限制 (90 ~ -90)
    # 注意：这里存用户视角的度数，90是天顶，-90是地底
    limit_v_min = Column(Float, default=-90.0) # 最低能看多低
    limit_v_max = Column(Float, default=90.0)  # 最高能看多高
    
    project = relationship("Project", back_populates="scenes")
    hotspots = relationship("Hotspot", back_populates="source_scene", foreign_keys="Hotspot.source_scene_id", cascade="all, delete-orphan")

# Hotspot 保持不变...
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