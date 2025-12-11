from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# --- Auth ---
class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str

# --- Icons ---
class HotspotIconBase(BaseModel):
    name: str
    url: str
    category: str

class HotspotIcon(HotspotIconBase):
    id: int
    owner_id: Optional[int] = None
    class Config: from_attributes = True

# --- Hotspot ---
class HotspotBase(BaseModel):
    x: float
    y: float
    z: float
    text: Optional[str] = None
    type: str = "scene"
    content: Optional[str] = None
    target_scene_id: Optional[int] = None
    icon_type: str = "system"
    icon_url: str = "arrow_move"
    scale: float = 1.0
    use_fixed_size: bool = False

class HotspotCreate(HotspotBase):
    source_scene_id: int

class HotspotUpdate(BaseModel):
    text: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    type: Optional[str] = None
    content: Optional[str] = None
    target_scene_id: Optional[int] = None
    icon_type: Optional[str] = None
    icon_url: Optional[str] = None
    scale: Optional[float] = None
    use_fixed_size: Optional[bool] = None

class Hotspot(HotspotBase):
    id: int
    class Config: from_attributes = True

# --- Scene ---
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
    sort_order: int = 0
    class Config: from_attributes = True

class SceneUpdate(BaseModel):
    name: Optional[str] = None
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

# --- Group ---
class SceneGroupBase(BaseModel):
    name: str
class SceneGroupCreate(SceneGroupBase):
    project_id: int
class SceneGroupUpdate(SceneGroupBase):
    pass
class SceneGroup(SceneGroupBase):
    id: int
    scenes: List[Scene] = []
    class Config: from_attributes = True

# --- Project ---
class ProjectBase(BaseModel):
    name: str
    category: str

class Project(ProjectBase):
    id: int
    cover_url: Optional[str] = None
    groups: List[SceneGroup] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    owner_id: Optional[int] = None
    class Config: from_attributes = True

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    cover_url: Optional[str] = None

# --- Utils ---
class ImageBase64(BaseModel):
    image_data: str