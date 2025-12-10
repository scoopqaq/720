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

# 1. 自动创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI()

# 2. 解决跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. 挂载静态文件
os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ===========================
#         Project API
# ===========================

@app.get("/projects/", response_model=List[schemas.Project])
def get_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Project).order_by(models.Project.updated_at.desc()).offset(skip).limit(limit).all()

@app.get("/projects/{project_id}", response_model=schemas.Project)
def read_project(project_id: int, db: Session = Depends(get_db)):
    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_project

@app.post("/projects/create_full/", response_model=schemas.Project)
def create_project_full(
    name: str = Form(...),
    category: str = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    db_project = models.Project(name=name, category=category)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    # 创建默认分组
    default_group = models.SceneGroup(name="默认分组", project_id=db_project.id)
    db.add(default_group)
    db.commit()
    db.refresh(default_group)

    for file in files:
        filename = f"{int(time.time())}_{file.filename}"
        file_location = f"static/uploads/{filename}"
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        db_scene = models.Scene(
            name=os.path.splitext(file.filename)[0],
            image_url=f"/{file_location}",
            group_id=default_group.id
        )
        db.add(db_scene)

    db.commit()
    db.refresh(db_project)
    return db_project

@app.post("/projects/batch_delete/")
def delete_projects(project_ids: List[int], db: Session = Depends(get_db)):
    db.query(models.Project).filter(models.Project.id.in_(project_ids)).delete(synchronize_session=False)
    db.commit()
    return {"ok": True}

@app.put("/projects/{project_id}")
def update_project(project_id: int, project_update: schemas.ProjectUpdate, db: Session = Depends(get_db)):
    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project_update.name is not None:
        db_project.name = project_update.name
    if project_update.category is not None:
        db_project.category = project_update.category
    
    db_project.updated_at = datetime.now()
    db.commit()
    db.refresh(db_project)
    return db_project

# ===========================
#         Group API
# ===========================

@app.post("/groups/", response_model=schemas.SceneGroup)
def create_group(group: schemas.SceneGroupCreate, db: Session = Depends(get_db)):
    db_group = models.SceneGroup(**group.dict())
    db.add(db_group)
    
    # 更新项目时间
    project = db.query(models.Project).filter(models.Project.id == group.project_id).first()
    if project: project.updated_at = datetime.now()
    
    db.commit()
    db.refresh(db_group)
    return db_group

@app.put("/groups/{group_id}")
def update_group(group_id: int, group_update: schemas.SceneGroupUpdate, db: Session = Depends(get_db)):
    db_group = db.query(models.SceneGroup).filter(models.SceneGroup.id == group_id).first()
    if not db_group: raise HTTPException(status_code=404, detail="Group not found")
    db_group.name = group_update.name
    db.commit()
    return db_group

@app.delete("/groups/{group_id}")
def delete_group(group_id: int, db: Session = Depends(get_db)):
    db.query(models.SceneGroup).filter(models.SceneGroup.id == group_id).delete()
    db.commit()
    return {"ok": True}

@app.post("/groups/{group_id}/upload_scene", response_model=schemas.Scene)
def upload_scene_to_group(group_id: int, files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    file = files[0]
    filename = f"{int(time.time())}_{file.filename}"
    file_location = f"static/uploads/{filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    db_scene = models.Scene(
        name=os.path.splitext(file.filename)[0],
        image_url=f"/{file_location}",
        group_id=group_id
    )
    db.add(db_scene)
    
    group = db.query(models.SceneGroup).filter(models.SceneGroup.id == group_id).first()
    if group and group.project: group.project.updated_at = datetime.now()

    db.commit()
    db.refresh(db_scene)
    return db_scene

# ===========================
#         Scene API
# ===========================

@app.put("/scenes/{scene_id}")
def update_scene(scene_id: int, scene_update: schemas.SceneUpdate, db: Session = Depends(get_db)):
    db_scene = db.query(models.Scene).filter(models.Scene.id == scene_id).first()
    if not db_scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    
    update_data = scene_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_scene, key, value)
    
    if db_scene.group and db_scene.group.project:
        db_scene.group.project.updated_at = datetime.now()

    db.commit()
    return db_scene

@app.delete("/scenes/{scene_id}")
def delete_scene(scene_id: int, db: Session = Depends(get_db)):
    db_scene = db.query(models.Scene).filter(models.Scene.id == scene_id).first()
    if not db_scene: raise HTTPException(status_code=404, detail="Scene not found")
    
    if db_scene.group and db_scene.group.project:
        db_scene.group.project.updated_at = datetime.now()

    db.delete(db_scene)
    db.commit()
    return {"ok": True}

# ===========================
#      Hotspot API (补全)
# ===========================

# [新增] 创建热点
@app.post("/hotspots/", response_model=schemas.Hotspot)
def create_hotspot(hotspot: schemas.HotspotCreate, db: Session = Depends(get_db)):
    db_hotspot = models.Hotspot(**hotspot.dict())
    db.add(db_hotspot)
    db.commit()
    db.refresh(db_hotspot)
    
    # 尝试更新项目时间
    try:
        if db_hotspot.source_scene and db_hotspot.source_scene.group and db_hotspot.source_scene.group.project:
            db_hotspot.source_scene.group.project.updated_at = datetime.now()
            db.commit()
    except:
        pass # 如果关联太深查不到就算了，不影响热点创建
        
    return db_hotspot

# [新增] 更新热点
@app.put("/hotspots/{hotspot_id}")
def update_hotspot(hotspot_id: int, hotspot_update: schemas.HotspotUpdate, db: Session = Depends(get_db)):
    db_hotspot = db.query(models.Hotspot).filter(models.Hotspot.id == hotspot_id).first()
    if not db_hotspot:
        raise HTTPException(status_code=404, detail="Hotspot not found")
    
    update_data = hotspot_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_hotspot, key, value)
    
    db.commit()
    db.refresh(db_hotspot)
    return db_hotspot

# [新增] 删除热点
@app.delete("/hotspots/{hotspot_id}")
def delete_hotspot(hotspot_id: int, db: Session = Depends(get_db)):
    db_hotspot = db.query(models.Hotspot).filter(models.Hotspot.id == hotspot_id).first()
    if db_hotspot:
        db.delete(db_hotspot)
        db.commit()
    return {"ok": True}

# ===========================
#         Utils
# ===========================

@app.post("/upload_base64/")
def upload_base64(data: schemas.ImageBase64): # 注意这里引用 schemas
    try:
        header, encoded = data.image_data.split(",", 1)
        file_ext = header.split(";")[0].split("/")[1]
        if file_ext == "jpeg": file_ext = "jpg"
        
        image_bytes = base64.b64decode(encoded)
        filename = f"cover_{int(time.time())}.{file_ext}"
        file_path = f"static/uploads/{filename}"
        
        with open(file_path, "wb") as f:
            f.write(image_bytes)
            
        return {"url": f"/{file_path}"}
    except Exception as e:
        print(f"Upload Error: {e}")
        raise HTTPException(status_code=500, detail="Image upload failed")