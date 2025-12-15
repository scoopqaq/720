import os
import shutil
from typing import List
from datetime import datetime
import base64
import time

from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from database import engine, Base, get_db
import models, schemas

from auth import get_password_hash, verify_password, create_access_token, get_current_user
#标签栏，目的是为了区分不同API的功能
tags_metadata = [
    {
        "name": "users",
        "description": "用户相关操作，包括登录和注册功能。",
    },
    {
        "name": "project",
        "description": "项目管理相关代码，创建项目，删除项目，重命名项目名等",
    },
    {
        "name":"scene",
        "description":"场景以及场景组设置",
    },
    {
        "name": "view",
        "description": "查看器功能",
    },
    {
        "name":"editor",
        "description":"编辑器功能"
    }
]

Base.metadata.create_all(bind=engine)
app = FastAPI(openapi_tags=tags_metadata)

# 2. CORS
app.add_middleware(
    CORSMiddleware,
    # 使用正则匹配所有来源，解决 IP 变动问题
    allow_origin_regex="https?://.*", 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. 静态文件
os.makedirs("static/uploads", exist_ok=True)
os.makedirs("static/icons/system", exist_ok=True)
os.makedirs("static/icons/custom", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

def init_system_icons():
    print("正在全量同步系统图标...")
    db = next(get_db())
    system_dir = "static/icons/system"
    
    if not os.path.exists(system_dir):
        os.makedirs(system_dir)

    # 1. 获取【磁盘】上的真实文件集合
    try:
        disk_files = set([
            f for f in os.listdir(system_dir) 
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg'))
        ])
    except Exception as e:
        print(f"读取系统图标目录失败: {e}")
        return

    # 2. 获取【数据库】里的现有系统图标集合
    db_icons = db.query(models.HotspotIcon).filter(models.HotspotIcon.category == "system").all()
    # 建立 name -> icon对象 的映射，方便后面删除
    db_icon_map = {icon.name: icon for icon in db_icons}
    db_files = set(db_icon_map.keys())

    # 3. 计算差异
    to_add = disk_files - db_files      # 需要新增的
    to_delete = db_files - disk_files   # 需要删除的

    # 4. 执行新增
    for filename in to_add:
        icon = models.HotspotIcon(
            name=filename,
            url=f"/static/icons/system/{filename}",
            category="system",
            owner_id=None
        )
        db.add(icon)

    # 5. 执行删除
    for filename in to_delete:
        print(f"检测到文件缺失，正在从数据库移除: {filename}")
        db.delete(db_icon_map[filename])

    # 6. 提交更改
    if to_add or to_delete:
        db.commit()
        print(f"✅ 同步完成：新增 {len(to_add)} 个，删除 {len(to_delete)} 个")
    else:
        print("系统图标已是最新 (无变动)")

# 启动时运行初始化
init_system_icons()
# ===========================
#         Auth API
# ===========================

#用户注册
@app.post("/auth/register",tags=["users"])
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_pw = get_password_hash(user.password)
    new_user = models.User(username=user.username, hashed_password=hashed_pw)
    db.add(new_user)
    db.commit()
    return {"msg": "Registration successful"}

#用户登录
@app.post("/auth/login", response_model=schemas.Token,tags=["users"])
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    access_token = create_access_token(data={"sub": db_user.username})
    return {"access_token": access_token, "token_type": "bearer", "username": db_user.username}

#fastapi文档登录测试专用接口
@app.post("/auth/swagger_login", response_model=schemas.Token, include_in_schema=False)
def login_for_docs(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not db_user or not verify_password(form_data.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    access_token = create_access_token(data={"sub": db_user.username})
    return {"access_token": access_token, "token_type": "bearer", "username": db_user.username}


# ===========================
#         Project API
# ===========================
#获取作品列表
@app.get("/projects/", response_model=List[schemas.Project],tags=["project"])
def get_projects(
    skip: int = 0, limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    获得全部的作品资料，目的是载入用户的作品列表
    """
    return db.query(models.Project).filter(models.Project.owner_id == current_user.id).order_by(models.Project.updated_at.desc()).offset(skip).limit(limit).all()

# 获取详情
@app.get("/projects/{project_id}", response_model=schemas.Project,tags=["project"])
def read_project(
    project_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    通过作品id获得详细的作品内容
    """
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

# 创建项目
@app.post("/projects/create_full/", response_model=schemas.Project,tags=["project"])
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

@app.post("/projects/batch_delete/",tags=["project"])
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

@app.put("/projects/{project_id}",tags=["project"])
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
# 场景以及场景组

@app.post("/groups/", response_model=schemas.SceneGroup)
def create_group(group: schemas.SceneGroupCreate, db: Session = Depends(get_db)):
    """
    创建一个新的场景组
    """
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
    """
    更新组名
    """
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

@app.delete("/icons/{icon_id}")
def delete_icon(
    icon_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # 1. 查找图标 (必须是当前用户的 custom 图标)
    icon = db.query(models.HotspotIcon).filter(
        models.HotspotIcon.id == icon_id,
        models.HotspotIcon.owner_id == current_user.id, # 关键：只能删自己的
        models.HotspotIcon.category == "custom"          # 关键：不能删系统的
    ).first()
    
    if not icon:
        raise HTTPException(status_code=404, detail="图标不存在或无权删除")

    # 2. 删除物理文件 (尝试删除，忽略错误以免数据库删不掉)
    try:
        # icon.url 格式通常是 /static/icons/custom/xxx.png
        # 需要去掉开头的 /，转为相对路径
        file_path = icon.url.lstrip("/")
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"文件删除失败: {e}")

    # 3. 删除数据库记录
    db.delete(icon)
    db.commit()
    
    return {"ok": True}