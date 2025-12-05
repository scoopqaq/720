import os
import shutil
from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import engine, Base, get_db
import models, schemas

# 1. 自动创建数据库表 (如果不存在)
Base.metadata.create_all(bind=engine)

app = FastAPI()

# 2. 解决跨域 (CORS) - 允许前端 5173 访问 后端 8000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 开发阶段允许所有来源，生产环境改为 ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. 挂载静态文件目录 (让前端能通过 URL 访问图片)
# 确保目录存在
os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- 接口 API ---

# 1. 创建项目
@app.post("/projects/", response_model=schemas.Project)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db)):
    db_project = models.Project(name=project.name)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

# 2. 获取项目详情 (前端初始化用这个，一次拿回所有数据)
@app.get("/projects/{project_id}", response_model=schemas.Project)
def read_project(project_id: int, db: Session = Depends(get_db)):
    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_project

# 3. 上传图片并创建场景 (Scene)
@app.post("/scenes/", response_model=schemas.Scene)
def create_scene(
    project_id: int = Form(...),
    name: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 保存文件到磁盘
    file_location = f"static/uploads/{file.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # 写入数据库
    # 注意：前端访问的 URL 是 /static/uploads/文件名
    db_scene = models.Scene(
        name=name,
        image_url=f"/{file_location}", 
        project_id=project_id
    )
    db.add(db_scene)
    db.commit()
    db.refresh(db_scene)
    return db_scene

# 4. 添加热点
@app.post("/hotspots/", response_model=schemas.Hotspot)
def create_hotspot(hotspot: schemas.HotspotCreate, db: Session = Depends(get_db)):
    db_hotspot = models.Hotspot(**hotspot.dict())
    db.add(db_hotspot)
    db.commit()
    db.refresh(db_hotspot)
    return db_hotspot

# 5. 删除热点 (编辑时如果要撤销)
@app.delete("/hotspots/{hotspot_id}")
def delete_hotspot(hotspot_id: int, db: Session = Depends(get_db)):
    db_hotspot = db.query(models.Hotspot).filter(models.Hotspot.id == hotspot_id).first()
    if db_hotspot:
        db.delete(db_hotspot)
        db.commit()
    return {"ok": True}