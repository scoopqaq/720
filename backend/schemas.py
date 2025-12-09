from pydantic import BaseModel
from typing import List, Optional

# Hotspot 保持不变...
class HotspotBase(BaseModel):
    text: str
    x: float
    y: float
    z: float
    target_scene_id: int

class HotspotCreate(HotspotBase):
    source_scene_id: int

class Hotspot(HotspotBase):
    id: int
    class Config:
        from_attributes = True

# [修改] Scene 完整参数
class Scene(BaseModel):
    id: int
    name: str
    image_url: str
    cover_url: Optional[str] = None
    project_id: int
    hotspots: List[Hotspot] = []
    
    initial_heading: float
    initial_pitch: float
    
    fov_min: float
    fov_max: float
    fov_default: float
    
    limit_h_min: float
    limit_h_max: float
    limit_v_min: float
    limit_v_max: float

    class Config:
        from_attributes = True

# [修改] 更新模型
class SceneUpdate(BaseModel):
    # 允许更新所有参数
    initial_heading: Optional[float] = None
    initial_pitch: Optional[float] = None
    fov_min: Optional[float] = None
    fov_max: Optional[float] = None
    fov_default: Optional[float] = None
    limit_h_min: Optional[float] = None
    limit_h_max: Optional[float] = None
    limit_v_min: Optional[float] = None
    limit_v_max: Optional[float] = None
    cover_url: Optional[str] = None # 用于更新截图封面

# Project 保持不变...
class ProjectBase(BaseModel):
    name: str
    category: str

class ProjectCreate(ProjectBase):
    pass

class Project(ProjectBase):
    id: int
    cover_url: Optional[str] = None
    scenes: List[Scene] = []
    class Config:
        from_attributes = True

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    cover_url: Optional[str] = None