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

# [修改] Scene 增加视角字段
class Scene(BaseModel):
    id: int
    name: str
    image_url: str
    project_id: int
    hotspots: List[Hotspot] = []
    
    # 新增字段
    initial_angle: float
    initial_fov: float
    min_polar_angle: float
    max_polar_angle: float

    class Config:
        from_attributes = True

# [新增] 用于更新 Scene 的模型
class SceneUpdate(BaseModel):
    initial_angle: Optional[float] = None
    initial_fov: Optional[float] = None
    min_polar_angle: Optional[float] = None
    max_polar_angle: Optional[float] = None

# Project 保持不变...
class ProjectBase(BaseModel):
    name: str
    category: str

class ProjectCreate(ProjectBase):
    pass

class Project(ProjectBase):
    id: int
    scenes: List[Scene] = []
    class Config:
        from_attributes = True

# [新增] 用于更新 Project 的模型
class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None