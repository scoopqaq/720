from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category = Column(String, default="其他")
    scenes = relationship("Scene", back_populates="project", cascade="all, delete-orphan")

class Scene(Base):
    __tablename__ = "scenes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    image_url = Column(String)
    project_id = Column(Integer, ForeignKey("projects.id"))
    
    # [新增] 视角配置
    # 初始视角 (Y轴旋转角度，弧度制)
    initial_angle = Column(Float, default=0.0)
    # 初始 FOV (视场角 30-100)
    initial_fov = Column(Float, default=75.0)
    # 垂直视角限制 (用于限制抬头低头，避免看到全景图顶底的极点瑕疵)
    # 0 = 也就是正上方，Math.PI = 正下方
    min_polar_angle = Column(Float, default=0.0)
    max_polar_angle = Column(Float, default=3.14159) # 默认 π (180度)
    
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