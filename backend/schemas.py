from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# 在 schemas.py 任意位置添加
class ImageBase64(BaseModel):
    image_data: str
# --- Hotspot 模型 (补全这里) ---
class HotspotBase(BaseModel):
    text: str
    x: float
    y: float
    z: float
    target_scene_id: Optional[int] = None # 允许为空，新建时可能未指定

class HotspotCreate(HotspotBase):
    source_scene_id: int

# [新增] 更新热点时的校验模型
class HotspotUpdate(BaseModel):
    text: Optional[str] = None
    target_scene_id: Optional[int] = None
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None

class Hotspot(HotspotBase):
    id: int
    class Config:
        from_attributes = True

# Scene 修改：包含 group_id
class Scene(BaseModel):
    id: int
    name: str
    image_url: str
    cover_url: Optional[str] = None
    group_id: int
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
    # 允许更新所有参数
    name: Optional[str] = None # 支持重命名场景
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

# [新增] SceneGroup Schema
class SceneGroupBase(BaseModel):
    name: str

class SceneGroupCreate(SceneGroupBase):
    project_id: int

class SceneGroupUpdate(BaseModel):
    name: str

class SceneGroup(SceneGroupBase):
    id: int
    project_id: int
    scenes: List[Scene] = [] # 分组下包含场景
    class Config: from_attributes = True

# Project 修改：scenes 变为 groups
class ProjectBase(BaseModel):
    name: str
    category: str

class ProjectCreate(ProjectBase):
    pass

class Project(ProjectBase):
    id: int
    cover_url: Optional[str] = None
    groups: List[SceneGroup] = [] # [修改] 这里变成了 groups
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    class Config: from_attributes = True

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    cover_url: Optional[str] = None
class HotspotUpdate(BaseModel):
    text: Optional[str] = None
    target_scene_id: Optional[int] = None
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
