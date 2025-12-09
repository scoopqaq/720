import os
import shutil
from typing import List
from datetime import datetime # [修复] 必须这样导入，否则 datetime.now() 会报错
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

# 2. 解决跨域 (CORS) - 必须放在最前面
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. 挂载静态文件目录
os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- 接口 API ---

# [新增] 上传 Base64 图片 (用于保存截图封面)
class ImageBase64(schemas.BaseModel):
    image_data: str

@app.post("/upload_base64/")
def upload_base64(data: ImageBase64):
    try:
        # 解析 Base64
        header, encoded = data.image_data.split(",", 1)
        file_ext = header.split(";")[0].split("/")[1]
        if file_ext == "jpeg": file_ext = "jpg"
        
        image_bytes = base64.b64decode(encoded)
        
        # 保存文件
        filename = f"cover_{int(time.time())}.{file_ext}"
        file_path = f"static/uploads/{filename}"
        
        with open(file_path, "wb") as f:
            f.write(image_bytes)
            
        return {"url": f"/{file_path}"}
    except Exception as e:
        print(f"Upload Error: {e}")
        raise HTTPException(status_code=500, detail="Image upload failed")

# 创建项目
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

    for file in files:
        filename = file.filename
        file_location = f"static/uploads/{filename}"
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        db_scene = models.Scene(
            name=os.path.splitext(filename)[0],
            image_url=f"/{file_location}",
            project_id=db_project.id
        )
        db.add(db_scene)

    db.commit()
    db.refresh(db_project)
    return db_project

# 获取项目列表
@app.get("/projects/", response_model=List[schemas.Project])
def get_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Project).order_by(models.Project.updated_at.desc()).offset(skip).limit(limit).all()

# 获取单个项目详情
@app.get("/projects/{project_id}", response_model=schemas.Project)
def read_project(project_id: int, db: Session = Depends(get_db)):
    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_project

# [关键修复] 更新场景设置
@app.put("/scenes/{scene_id}")
def update_scene(scene_id: int, scene_update: schemas.SceneUpdate, db: Session = Depends(get_db)):
    db_scene = db.query(models.Scene).filter(models.Scene.id == scene_id).first()
    if not db_scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    
    # 1. 更新场景数据
    update_data = scene_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_scene, key, value)
    
    # 2. 强制更新父级项目的 updated_at 时间 (用于排序置顶)
    if db_scene.project:
        db_scene.project.updated_at = datetime.now()

    db.commit()
    return db_scene

# 更新项目信息
@app.put("/projects/{project_id}")
def update_project(project_id: int, project_update: schemas.ProjectUpdate, db: Session = Depends(get_db)):
    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project_update.name is not None:
        db_project.name = project_update.name
    if project_update.category is not None:
        db_project.category = project_update.category
    
    # 更新时间
    db_project.updated_at = datetime.now()
        
    db.commit()
    db.refresh(db_project)
    return db_project

# 批量删除
@app.post("/projects/batch_delete/")
def delete_projects(project_ids: List[int], db: Session = Depends(get_db)):
    db.query(models.Project).filter(models.Project.id.in_(project_ids)).delete(synchronize_session=False)
    db.commit()
    return {"ok": True}