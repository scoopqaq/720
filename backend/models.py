from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    
    # 关联：一个项目包含多个场景
    scenes = relationship("Scene", back_populates="project", cascade="all, delete-orphan")

class Scene(Base):
    __tablename__ = "scenes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)       # 房间名，如“客厅”
    image_url = Column(String)  # 图片路径，如 "/static/uploads/xxx.jpg"
    project_id = Column(Integer, ForeignKey("projects.id"))
    
    # 关联：属于哪个项目
    project = relationship("Project", back_populates="scenes")
    # 关联：这个房间里的热点
    hotspots = relationship("Hotspot", back_populates="source_scene", foreign_keys="Hotspot.source_scene_id", cascade="all, delete-orphan")

class Hotspot(Base):
    __tablename__ = "hotspots"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String) # 热点显示的文字
    
    # 坐标 (Three.js 的 x, y, z)
    x = Column(Float)
    y = Column(Float)
    z = Column(Float)
    
    # 逻辑：从哪个房间(source) -> 去哪个房间(target)
    source_scene_id = Column(Integer, ForeignKey("scenes.id"))
    target_scene_id = Column(Integer, ForeignKey("scenes.id"))
    
    # 关联对象
    source_scene = relationship("Scene", foreign_keys=[source_scene_id], back_populates="hotspots")
    # 注意：这里不需要 target_scene 的反向关联，通常单向引用即可