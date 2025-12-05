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
class SceneBase(BaseModel):
    name: str

class SceneCreate(SceneBase):
    pass # 创建时只需要名字，图片单独传

class Scene(SceneBase):
    id: int
    image_url: str
    project_id: int
    hotspots: List[Hotspot] = [] # 嵌套返回热点
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