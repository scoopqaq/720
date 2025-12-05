from pydantic import BaseModel
from typing import List, Optional

# --- Hotspot Schemas ---
class HotspotBase(BaseModel):
    text: str
    x: float
    y: float
    z: float
    target_scene_id: int

class HotspotCreate(HotspotBase):
    source_scene_id: int # 创建时需要知道属于哪个房间

class Hotspot(HotspotBase):
    id: int
    class Config:
        from_attributes = True

# --- Scene Schemas ---
class Scene(BaseModel):
    id: int
    name: str
    image_url: str
    project_id: int
    class Config:
        from_attributes = True

class ProjectBase(BaseModel):
    name: str
    category: str # [新增]

class ProjectCreate(ProjectBase):
    pass

class Project(ProjectBase):
    id: int
    scenes: List[Scene] = []
    class Config:
        from_attributes = True

# --- Project Schemas ---
class ProjectBase(BaseModel):
    name: str

class ProjectCreate(ProjectBase):
    pass

class Project(ProjectBase):
    id: int
    scenes: List[Scene] = [] # 嵌套返回场景
    class Config:
        from_attributes = True