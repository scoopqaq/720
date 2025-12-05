from pydantic import BaseModel
from typing import List, Optional

# --- Hotspot Schemas (保持不变) ---
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

# --- Scene Schemas (关键修改) ---
class Scene(BaseModel):
    id: int
    name: str
    image_url: str
    project_id: int
    # [修复] 这一行之前弄丢了，导致前端拿不到热点数据列表，必须加回来！
    hotspots: List[Hotspot] = [] 
    
    class Config:
        from_attributes = True

# --- Project Schemas (保持不变) ---
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