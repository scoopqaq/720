from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# Hotspot & Scene 保持不变...
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
    class Config: from_attributes = True

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
    class Config: from_attributes = True

class SceneUpdate(BaseModel):
    initial_heading: Optional[float] = None
    initial_pitch: Optional[float] = None
    fov_min: Optional[float] = None
    fov_max: Optional[float] = None
    fov_default: Optional[float] = None
    limit_h_min: Optional[float] = None
    limit_h_max: Optional[float] = None
    limit_v_min: Optional[float] = None
    limit_v_max: Optional[float] = None
    cover_url: Optional[str] = None

# Project 相关修改
class ProjectBase(BaseModel):
    name: str
    category: str

class ProjectCreate(ProjectBase):
    pass

class Project(ProjectBase):
    id: int
    cover_url: Optional[str] = None
    scenes: List[Scene] = []
    
    # [新增]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    cover_url: Optional[str] = None