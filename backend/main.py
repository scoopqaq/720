import os
import shutil
from typing import List
from datetime import datetime
import base64
import time

from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import engine, Base, get_db
import models, schemas
# 引入 Auth 逻辑
from auth import get_password_hash, verify_password, create_access_token, get_current_user

# 1. 初始化
Base.metadata.create_all(bind=engine)
app = FastAPI()

# 2. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. 静态文件
os.makedirs("static/uploads", exist_ok=True)
os.makedirs("static/icons/system", exist_ok=True)
os.makedirs("static/icons/custom", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- 4. 初始化默认图标 (可选) ---
def init_system_icons():
    # 简单示例，实际部署请手动放入图片
    pass 
init_system_icons()

# ===========================
#         Auth API
# ===========================

@app.post("/auth/register")
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_pw = get_password_hash(user.password)
    new_user = models.User(username=user.username, hashed_password=hashed_pw)
    db.add(new_user)
    db.commit()
    return {"msg": "Registration successful"}

@app.post("/auth/login", response_model=schemas.Token)
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    access_token = create_access_token(data={"sub": db_user.username})
    return {"access_token": access_token, "token_type": "bearer", "username": db_user.username}

# ===========================
#         Project API
# ===========================

# [保护] 获取项目列表 (只看自己的)
@app.get("/projects/", response_model=List[schemas.Project])
def get_projects(
    skip: int = 0, limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return db.query(models.Project).filter(models.Project.owner_id == current_user.id).order_by(models.Project.updated_at.desc()).offset(skip).limit(limit).all()

# 获取详情 (需鉴权，防止看别人的)
@app.get("/projects/{project_id}", response_model=schemas.Project)
def read_project(
    project_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.owner_id == current_user.id
    ).first()
    
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found or access denied")
    
    # 手动排序 scenes
    for group in db_project.groups:
        group.scenes.sort(key=lambda s: s.sort_order)
        
    return db_project

# [保护] 创建项目
@app.post("/projects/create_full/", response_model=schemas.Project)
def create_project_full(
    name: str = Form(...),
    category: str = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_project = models.Project(name=name, category=category, owner_id=current_user.id)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    default_group = models.SceneGroup(name="默认分组", project_id=db_project.id)
    db.add(default_group)
    db.commit()
    db.refresh(default_group)

    for file in files:
        filename = f"{int(time.time())}_{file.filename}"
        file_path = f"static/uploads/{filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        db_scene = models.Scene(
            name=os.path.splitext(file.filename)[0],
            image_url=f"/{file_path}",
            group_id=default_group.id
        )
        db.add(db_scene)

    db.commit()
    db.refresh(db_project)
    return db_project

@app.post("/projects/batch_delete/")
def delete_projects(
    project_ids: List[int], 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db.query(models.Project).filter(
        models.Project.id.in_(project_ids),
        models.Project.owner_id == current_user.id
    ).delete(synchronize_session=False)
    db.commit()
    return {"ok": True}

@app.put("/projects/{project_id}")
def update_project(
    project_id: int, 
    project_update: schemas.ProjectUpdate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_project = db.query(models.Project).filter(models.Project.id == project_id, models.Project.owner_id == current_user.id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Not found")
    
    if project_update.name: db_project.name = project_update.name
    if project_update.category: db_project.category = project_update.category
    
    db_project.updated_at = datetime.now()
    db.commit()
    db.refresh(db_project)
    return db_project

# ===========================
#      Group & Scene API 
# ===========================
# (为简化，这里暂不加严格的 owner 检查，因为这些操作通常在编辑器内，前提是已经获取了 Project 详情)

@app.post("/groups/", response_model=schemas.SceneGroup)
def create_group(group: schemas.SceneGroupCreate, db: Session = Depends(get_db)):
    db_group = models.SceneGroup(**group.dict())
    db.add(db_group)
    # 更新时间
    proj = db.query(models.Project).filter(models.Project.id == group.project_id).first()
    if proj: proj.updated_at = datetime.now()
    db.commit()
    db.refresh(db_group)
    return db_group

@app.put("/groups/{group_id}")
def update_group(group_id: int, u: schemas.SceneGroupUpdate, db: Session = Depends(get_db)):
    g = db.query(models.SceneGroup).filter(models.SceneGroup.id == group_id).first()
    if g:
        g.name = u.name
        db.commit()
    return g

@app.delete("/groups/{group_id}")
def delete_group(group_id: int, db: Session = Depends(get_db)):
    db.query(models.SceneGroup).filter(models.SceneGroup.id == group_id).delete()
    db.commit()
    return {"ok": True}

@app.post("/groups/{group_id}/upload_scene", response_model=schemas.Scene)
def upload_scene_to_group(group_id: int, files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    file = files[0]
    filename = f"{int(time.time())}_{file.filename}"
    file_path = f"static/uploads/{filename}"
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    db_scene = models.Scene(name=os.path.splitext(file.filename)[0], image_url=f"/{file_path}", group_id=group_id)
    db.add(db_scene)
    
    g = db.query(models.SceneGroup).filter(models.SceneGroup.id == group_id).first()
    if g and g.project: g.project.updated_at = datetime.now()
    
    db.commit()
    db.refresh(db_scene)
    return db_scene

@app.put("/scenes/{scene_id}")
def update_scene(scene_id: int, u: schemas.SceneUpdate, db: Session = Depends(get_db)):
    s = db.query(models.Scene).filter(models.Scene.id == scene_id).first()
    if not s: raise HTTPException(status_code=404)
    
    data = u.dict(exclude_unset=True)
    for k, v in data.items(): setattr(s, k, v)
    
    if s.group and s.group.project: s.group.project.updated_at = datetime.now()
    db.commit()
    return s

@app.delete("/scenes/{scene_id}")
def delete_scene(scene_id: int, db: Session = Depends(get_db)):
    s = db.query(models.Scene).filter(models.Scene.id == scene_id).first()
    if s:
        if s.group and s.group.project: s.group.project.updated_at = datetime.now()
        db.delete(s)
        db.commit()
    return {"ok": True}

@app.post("/groups/{group_id}/reorder_scenes")
def reorder_scenes(group_id: int, scene_ids: List[int], db: Session = Depends(get_db)):
    scenes = db.query(models.Scene).filter(models.Scene.group_id == group_id).all()
    s_map = {s.id: s for s in scenes}
    for idx, sid in enumerate(scene_ids):
        if sid in s_map: s_map[sid].sort_order = idx
    db.commit()
    return {"ok": True}

# ===========================
#        Hotspot API
# ===========================

@app.post("/hotspots/", response_model=schemas.Hotspot)
def create_hotspot(h: schemas.HotspotCreate, db: Session = Depends(get_db)):
    db_h = models.Hotspot(**h.dict())
    db.add(db_h)
    db.commit()
    db.refresh(db_h)
    return db_h

@app.put("/hotspots/{hotspot_id}")
def update_hotspot(hotspot_id: int, u: schemas.HotspotUpdate, db: Session = Depends(get_db)):
    h = db.query(models.Hotspot).filter(models.Hotspot.id == hotspot_id).first()
    if not h: raise HTTPException(status_code=404)
    
    data = u.dict(exclude_unset=True)
    for k, v in data.items(): setattr(h, k, v)
    
    db.commit()
    db.refresh(h)
    return h

@app.delete("/hotspots/{hotspot_id}")
def delete_hotspot(hotspot_id: int, db: Session = Depends(get_db)):
    db.query(models.Hotspot).filter(models.Hotspot.id == hotspot_id).delete()
    db.commit()
    return {"ok": True}

@app.post("/hotspots/batch_delete/")
def delete_hotspots_batch(hotspot_ids: List[int], db: Session = Depends(get_db)):
    db.query(models.Hotspot).filter(models.Hotspot.id.in_(hotspot_ids)).delete(synchronize_session=False)
    db.commit()
    return {"ok": True}

# ===========================
#        Icons & Utils
# ===========================

@app.get("/icons/", response_model=List[schemas.HotspotIcon])
def get_icons(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.HotspotIcon).filter(
        (models.HotspotIcon.category == "system") | 
        ((models.HotspotIcon.category == "custom") & (models.HotspotIcon.owner_id == current_user.id))
    ).all()

@app.post("/icons/", response_model=schemas.HotspotIcon)
def upload_icon(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    if file.content_type not in ["image/png", "image/jpeg", "image/gif", "image/svg+xml"]:
        raise HTTPException(status_code=400, detail="Invalid format")
    
    fname = f"icon_{int(time.time())}_{file.filename}"
    fpath = f"static/icons/custom/{fname}"
    with open(fpath, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    icon = models.HotspotIcon(name=file.filename, url=f"/{fpath}", category="custom", owner_id=current_user.id)
    db.add(icon)
    db.commit()
    db.refresh(icon)
    return icon

@app.post("/upload_base64/")
def upload_base64(data: schemas.ImageBase64):
    try:
        header, encoded = data.image_data.split(",", 1)
        ext = header.split(";")[0].split("/")[1]
        if ext == "jpeg": ext = "jpg"
        ibytes = base64.b64decode(encoded)
        fname = f"cover_{int(time.time())}.{ext}"
        fpath = f"static/uploads/{fname}"
        with open(fpath, "wb") as f: f.write(ibytes)
        return {"url": f"/{fpath}"}
    except:
        raise HTTPException(status_code=500, detail="Upload failed")