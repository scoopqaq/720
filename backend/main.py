import os
import shutil
from typing import List # 必须引入 List
from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import engine, Base, get_db
import models, schemas

# 1. 自动创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI()

# 2. 解决跨域 (CORS)
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

# [旧接口] 创建空项目 (保留备用)
@app.post("/projects/", response_model=schemas.Project)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db)):
    db_project = models.Project(name=project.name, category=project.category)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

# [新增] 核心接口：创建项目并批量上传场景
# 注意：前端访问的 URL 必须完全匹配，建议带上结尾的斜杠 /
@app.post("/projects/create_full/", response_model=schemas.Project)
def create_project_full(
    name: str = Form(...),
    category: str = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    # 1. 先创建 Project
    db_project = models.Project(name=name, category=category)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    # 2. 循环处理上传的图片文件
    for file in files:
        filename = file.filename
        # 简单处理：如果文件名重复，会覆盖本地文件，建议生产环境加 uuid
        file_location = f"static/uploads/{filename}"
        
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 创建 Scene 记录
        scene_name = os.path.splitext(filename)[0]
        
        db_scene = models.Scene(
            name=scene_name,
            image_url=f"/{file_location}",
            project_id=db_project.id
        )
        db.add(db_scene)

    db.commit()
    db.refresh(db_project)
    return db_project
# [新增] 获取所有项目列表
@app.get("/projects/", response_model=List[schemas.Project])
def get_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    # 按 ID 倒序排列（最新的在前面）
    projects = db.query(models.Project).order_by(models.Project.id.desc()).offset(skip).limit(limit).all()
    return projects
# 获取项目详情
@app.get("/projects/{project_id}", response_model=schemas.Project)
def read_project(project_id: int, db: Session = Depends(get_db)):
    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_project

# 添加热点
@app.post("/hotspots/", response_model=schemas.Hotspot)
def create_hotspot(hotspot: schemas.HotspotCreate, db: Session = Depends(get_db)):
    db_hotspot = models.Hotspot(**hotspot.dict())
    db.add(db_hotspot)
    db.commit()
    db.refresh(db_hotspot)
    return db_hotspot

# 删除热点
@app.delete("/hotspots/{hotspot_id}")
def delete_hotspot(hotspot_id: int, db: Session = Depends(get_db)):
    db_hotspot = db.query(models.Hotspot).filter(models.Hotspot.id == hotspot_id).first()
    if db_hotspot:
        db.delete(db_hotspot)
        db.commit()
    return {"ok": True}