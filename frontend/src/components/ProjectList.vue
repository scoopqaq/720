<template>
  <div 
    class="list-wrapper" 
    @mousedown="onMouseDown"
    @contextmenu.prevent="onBgContextMenu"
  >
    <div class="content-container">
      <div class="toolbar">
        <div class="left-tools">
          <h2>作品库</h2>
          <div class="category-tabs">
             <span 
              :class="{active: filterCategory === ''}" 
              @click="filterCategory = ''"
            >全部</span>
            <span 
              v-for="cat in availableCategories" 
              :key="cat"
              :class="{active: filterCategory === cat}"
              @click="filterCategory = cat"
            >
              {{ cat }}
            </span>
          </div>
        </div>

        <div class="right-tools">
           <transition name="fade">
             <div v-if="isSelectionMode || selectedIds.length > 0" class="selection-tools">
               <span class="selected-count">已选 {{ selectedIds.length }} 项</span>
               <button class="btn btn-danger" @click="confirmBatchDelete" :disabled="selectedIds.length === 0">删除选中</button>
               <button class="btn btn-text" @click="exitSelectionMode">取消多选</button>
             </div>
           </transition>
           
           <button v-if="!isSelectionMode" class="btn btn-primary" @click="$emit('go-upload')">+ 新建作品</button>
        </div>
      </div>

      <div v-if="loading" class="loading-state">加载中...</div>
      
      <div v-else class="project-grid" ref="gridRef">
        <div 
          v-for="p in filteredProjects" 
          :key="p.id" 
          class="project-card"
          :class="{ selected: selectedIds.includes(p.id) }"
          :data-id="p.id"
          @click.stop="onCardClick(p, $event)"
          @contextmenu.prevent.stop="onCardContextMenu($event, p)"
        >
          <div class="checkbox-indicator" v-if="isSelectionMode || selectedIds.includes(p.id)">
            <div class="check-circle"></div>
          </div>

          <div class="cover-wrapper">
            <img :src="getCoverImage(p)" loading="lazy" />
            <div class="hover-overlay" v-if="!isSelectionMode">
              <span>点击进入</span>
            </div>
          </div>
          
          <div class="card-info">
            <h3 class="project-name">{{ p.name }}</h3>
            <span class="category-tag">{{ p.category }}</span>
          </div>
        </div>
      </div>
    </div>

    <div 
      v-if="dragBox.visible" 
      class="drag-selection-box"
      :style="{
        left: dragBox.left + 'px',
        top: dragBox.top + 'px',
        width: dragBox.width + 'px',
        height: dragBox.height + 'px'
      }"
    ></div>

    <transition name="fade-fast">
      <div 
        v-if="contextMenu.visible" 
        class="context-menu"
        :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
        @mousedown.stop
      >
        <template v-if="contextMenu.targetId">
          <div class="menu-item" @click="handleMenuAction('enter')">👀 进入查看器</div>
          <div class="menu-item" @click="handleMenuAction('edit')">🛠️ 编辑全景图</div>
          <div class="divider"></div>
          <div class="menu-item" @click="handleMenuAction('rename')">✏️ 重命名 / 分类</div>
          <div class="divider"></div>
          <div class="menu-item danger" @click="handleMenuAction('delete')">🗑️ 删除此作品</div>
        </template>
        
        <template v-else>
          <div class="menu-item" @click="selectAll">✅ 全选 ({{ filteredProjects.length }})</div>
          
          <div 
            v-if="selectedIds.length > 0" 
            class="menu-item danger" 
            @click="confirmBatchDelete"
          >
            🗑️ 删除选中 ({{ selectedIds.length }})
          </div>
          
          <div class="divider"></div>
          
          <div class="menu-item" @click="fetchProjects">🔄 刷新列表</div>
          
          <div v-if="!isSelectionMode" class="menu-item" @click="enterSelectionMode">☑️ 开启多选模式</div>
          <div v-else class="menu-item" @click="exitSelectionMode">❌ 退出多选模式</div>
          
          <div class="divider"></div>
          <div class="menu-item" @click="$emit('go-upload')">➕ 新建作品</div>
        </template>
      </div>
    </transition>

    <div v-if="modals.delete.visible" class="modal-overlay" @click.self="modals.delete.visible = false">
      <div class="modal-card">
        <h3>确认删除</h3>
        <p>确定要删除选中的 {{ modals.delete.ids.length }} 个作品吗？此操作无法撤销。</p>
        <div class="modal-actions">
          <button class="btn btn-text" @click="modals.delete.visible = false">取消</button>
          <button class="btn btn-danger" @click="executeDelete">确认删除</button>
        </div>
      </div>
    </div>

    <div v-if="modals.rename.visible" class="modal-overlay" @click.self="modals.rename.visible = false">
      <div class="modal-card">
        <h3>编辑信息</h3>
        <div class="form-group">
          <label>作品名称</label>
          <input type="text" v-model="modals.rename.tempName" class="form-input" placeholder="请输入名称">
        </div>
        <div class="form-group">
          <label>分类</label>
          <select v-model="modals.rename.tempCategory" class="form-select">
            <option v-for="cat in allCategories" :key="cat" :value="cat">{{ cat }}</option>
          </select>
        </div>
        <div class="modal-actions">
          <button class="btn btn-text" @click="modals.rename.visible = false">取消</button>
          <button class="btn btn-primary" @click="executeRename">保存修改</button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted, onBeforeUnmount } from 'vue';

const emit = defineEmits(['select-project', 'go-upload', 'enter-editor']);
const gridRef = ref(null);
const projects = ref([]);
const loading = ref(true);
const filterCategory = ref("");

// --- 状态管理 ---
const isSelectionMode = ref(false); 
const selectedIds = ref([]); 

// 菜单状态
const contextMenu = reactive({
  visible: false,
  x: 0,
  y: 0,
  targetId: null, 
  targetProject: null 
});

// 模态框状态
const modals = reactive({
  delete: { visible: false, ids: [] },
  rename: { visible: false, project: null, tempName: '', tempCategory: '' }
});

// 框选逻辑状态
const dragBox = reactive({
  visible: false,
  startX: 0, startY: 0,
  currentX: 0, currentY: 0,
  left: 0, top: 0, width: 0, height: 0
});
let isDragging = false;

// 固定分类列表
const allCategories = [
  '家装', '商业空间', '样板房', '公共空间', '室外建筑', 
  '展览展厅', '别墅', '园林景观', '酒店/民宿', '实景拍摄', 
  '餐饮', '景区/风光', '其他'
];

const availableCategories = computed(() => {
  const cats = new Set(projects.value.map(p => p.category));
  return Array.from(cats);
});

const filteredProjects = computed(() => {
  if (!filterCategory.value) return projects.value;
  return projects.value.filter(p => p.category === filterCategory.value);
});

// --- 数据获取 ---
const fetchProjects = async () => {
  loading.value = true;
  try {
    const res = await fetch('http://127.0.0.1:8000/projects/');
    if (res.ok) projects.value = await res.json();
  } finally {
    loading.value = false;
    contextMenu.visible = false; 
  }
};

const getCoverImage = (project) => {
  if (project.scenes && project.scenes.length > 0) {
    return `http://127.0.0.1:8000${project.scenes[0].image_url}`;
  }
  return 'https://via.placeholder.com/300x200?text=No+Scene';
};

// ==========================================
// 交互逻辑
// ==========================================

const onCardClick = (project, event) => {
  if (contextMenu.visible) {
    contextMenu.visible = false;
    return;
  }
  if (isSelectionMode.value) {
    toggleSelection(project.id);
  } else {
    emit('select-project', project.id);
  }
};

const toggleSelection = (id) => {
  const index = selectedIds.value.indexOf(id);
  if (index === -1) selectedIds.value.push(id);
  else selectedIds.value.splice(index, 1);
};

const enterSelectionMode = () => {
  isSelectionMode.value = true;
  contextMenu.visible = false;
};

const exitSelectionMode = () => {
  isSelectionMode.value = false;
  selectedIds.value = [];
  contextMenu.visible = false;
};

// [新增] 全选功能
const selectAll = () => {
  // 只全选当前筛选结果下的项目
  selectedIds.value = filteredProjects.value.map(p => p.id);
  isSelectionMode.value = true;
  contextMenu.visible = false;
};

// ==========================================
// 右键菜单系统
// ==========================================

const onBgContextMenu = (e) => {
  showMenu(e, null);
};

const onCardContextMenu = (e, project) => {
  // 如果当前没选中这个卡片，且不是多选模式，则只选中这一个
  if (!selectedIds.value.includes(project.id)) {
     // 如果已经在多选模式，我们通常保留其他选中项，只把当前这个也加上
     // 或者为了简单，右键未选中的项目时，就单选它
     if (!isSelectionMode.value) selectedIds.value = [];
     if (!selectedIds.value.includes(project.id)) selectedIds.value.push(project.id);
  }
  showMenu(e, project);
};

const showMenu = (e, target) => {
  contextMenu.visible = true;
  contextMenu.x = e.clientX;
  contextMenu.y = e.clientY;
  contextMenu.targetId = target ? target.id : null;
  contextMenu.targetProject = target;
};

const closeMenu = () => {
  contextMenu.visible = false;
};

const handleMenuAction = (action) => {
  const project = contextMenu.targetProject;
  contextMenu.visible = false;

  switch (action) {
    case 'enter':
      emit('select-project', project.id);
      break;
    case 'edit':
      emit('enter-editor', project.id);
      break;
    case 'delete':
      confirmBatchDelete();
      break;
    case 'rename':
      openRenameModal(project);
      break;
  }
};

// ==========================================
// 框选逻辑 (Windows 风格)
// ==========================================

const onMouseDown = (e) => {
  if (e.button !== 0) return; 
  closeMenu();
  if (e.target.closest('.project-card')) return;

  isDragging = true;
  dragBox.startX = e.clientX;
  dragBox.startY = e.clientY;
  dragBox.visible = true;
  dragBox.width = 0; dragBox.height = 0;

  if (!e.ctrlKey && !e.metaKey && !isSelectionMode.value) {
    selectedIds.value = [];
  }

  window.addEventListener('mousemove', onMouseMove);
  window.addEventListener('mouseup', onMouseUp);
};

const onMouseMove = (e) => {
  if (!isDragging) return;
  const currentX = e.clientX;
  const currentY = e.clientY;

  dragBox.left = Math.min(dragBox.startX, currentX);
  dragBox.top = Math.min(dragBox.startY, currentY);
  dragBox.width = Math.abs(currentX - dragBox.startX);
  dragBox.height = Math.abs(currentY - dragBox.startY);

  if (dragBox.width < 5 && dragBox.height < 5) return;
  checkSelectionIntersection();
};

const checkSelectionIntersection = () => {
  if (!gridRef.value) return;
  const cards = gridRef.value.querySelectorAll('.project-card');
  const selectionRect = {
    left: dragBox.left, top: dragBox.top,
    right: dragBox.left + dragBox.width, bottom: dragBox.top + dragBox.height
  };

  cards.forEach(card => {
    const rect = card.getBoundingClientRect();
    const intersect = !(rect.right < selectionRect.left || 
                        rect.left > selectionRect.right || 
                        rect.bottom < selectionRect.top || 
                        rect.top > selectionRect.bottom);
    
    const id = parseInt(card.getAttribute('data-id'));
    if (intersect) {
      if (!selectedIds.value.includes(id)) selectedIds.value.push(id);
    }
  });
};

const onMouseUp = () => {
  isDragging = false;
  dragBox.visible = false;
  window.removeEventListener('mousemove', onMouseMove);
  window.removeEventListener('mouseup', onMouseUp);
};


// ==========================================
// 模态框操作
// ==========================================

const confirmBatchDelete = () => {
  if (selectedIds.value.length === 0) return;
  contextMenu.visible = false;
  modals.delete.ids = [...selectedIds.value];
  modals.delete.visible = true;
};

const executeDelete = async () => {
  try {
    const res = await fetch('http://127.0.0.1:8000/projects/batch_delete/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(modals.delete.ids)
    });

    if (res.ok) {
      projects.value = projects.value.filter(p => !modals.delete.ids.includes(p.id));
      selectedIds.value = [];
      modals.delete.visible = false;
      if (projects.value.length === 0) exitSelectionMode();
    }
  } catch (err) {
    alert("删除失败");
  }
};

const openRenameModal = (project) => {
  modals.rename.project = project;
  modals.rename.tempName = project.name;
  modals.rename.tempCategory = project.category;
  modals.rename.visible = true;
};

const executeRename = async () => {
  const p = modals.rename.project;
  try {
    const res = await fetch(`http://127.0.0.1:8000/projects/${p.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: modals.rename.tempName,
        category: modals.rename.tempCategory
      })
    });
    
    if (res.ok) {
      p.name = modals.rename.tempName;
      p.category = modals.rename.tempCategory;
      modals.rename.visible = false;
    }
  } catch (err) {
    alert("修改失败");
  }
};

onMounted(() => {
  fetchProjects();
  window.addEventListener('click', closeMenu);
});

onBeforeUnmount(() => {
  window.removeEventListener('click', closeMenu);
});
</script>

<style scoped>
.list-wrapper {
  min-height: 100vh;
  background-color: #f5f7fa;
  padding: 20px;
  font-family: 'PingFang SC', sans-serif;
  user-select: none;
  position: relative;
}

.content-container { max-width: 1400px; margin: 0 auto; }

.toolbar {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 20px; height: 50px;
}

.left-tools { display: flex; align-items: center; gap: 30px; }
.left-tools h2 { margin: 0; font-size: 24px; color: #333; }

.category-tabs { display: flex; gap: 10px; }
.category-tabs span {
  font-size: 14px; color: #666; cursor: pointer; padding: 4px 12px;
  border-radius: 20px; transition: all 0.2s;
}
.category-tabs span:hover { background: #e6e6e6; }
.category-tabs span.active { background: #333; color: white; font-weight: bold; }

.right-tools { display: flex; align-items: center; gap: 10px; }
.selection-tools { display: flex; align-items: center; gap: 10px; margin-right: 10px; }
.selected-count { font-size: 14px; color: #666; font-weight: bold; }

.btn { border: none; padding: 8px 20px; border-radius: 6px; cursor: pointer; font-size: 14px; transition: all 0.2s; font-weight: 500; }
.btn-primary { background: #333; color: white; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
.btn-primary:hover { background: #000; transform: translateY(-1px); }
.btn-danger { background: #fee; color: #e74c3c; }
.btn-danger:hover { background: #fdd; }
.btn-text { background: transparent; color: #666; }
.btn-text:hover { color: #333; background: #eee; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }

.project-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 24px;
  padding-bottom: 100px;
}

.project-card {
  background: white; border-radius: 12px; overflow: hidden;
  box-shadow: 0 2px 10px rgba(0,0,0,0.03); position: relative;
  transition: all 0.2s; cursor: pointer; border: 2px solid transparent;
}
.project-card:hover { transform: translateY(-4px); box-shadow: 0 10px 20px rgba(0,0,0,0.08); }

.project-card.selected {
  border-color: #3498db;
  background: #f0f9ff;
}

.checkbox-indicator {
  position: absolute; top: 12px; left: 12px; z-index: 10;
  width: 24px; height: 24px; border-radius: 50%;
  background: white; border: 2px solid #ddd;
  display: flex; justify-content: center; align-items: center;
}
.project-card.selected .checkbox-indicator {
  background: #3498db; border-color: #3498db;
}
.project-card.selected .checkbox-indicator .check-circle {
  width: 10px; height: 10px; background: white; border-radius: 50%;
}

.cover-wrapper {
  height: 160px; background: #eee; position: relative;
}
.cover-wrapper img { width: 100%; height: 100%; object-fit: cover; }

.hover-overlay {
  position: absolute; top:0; left:0; width:100%; height:100%;
  background: rgba(0,0,0,0.2); display: flex; justify-content: center; align-items: center;
  opacity: 0; transition: opacity 0.2s;
}
.project-card:hover .hover-overlay { opacity: 1; }
.hover-overlay span {
  color: white; border: 1px solid rgba(255,255,255,0.8); 
  padding: 6px 16px; border-radius: 20px; font-size: 13px; backdrop-filter: blur(4px);
}

.card-info { padding: 16px; }
.project-name {
  margin: 0 0 6px; font-size: 15px; color: #333;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.category-tag {
  font-size: 12px; color: #888; background: #f5f5f5; padding: 2px 8px; border-radius: 4px;
}

.drag-selection-box {
  position: fixed; 
  border: 1px solid #3498db;
  background-color: rgba(52, 152, 219, 0.2);
  z-index: 9999;
  pointer-events: none; 
}

.context-menu {
  position: fixed; z-index: 10000;
  background: white; border-radius: 8px;
  box-shadow: 0 5px 20px rgba(0,0,0,0.15);
  padding: 6px 0; min-width: 160px;
  border: 1px solid #eee;
}
.menu-item {
  padding: 10px 20px; font-size: 14px; color: #333; cursor: pointer;
  display: flex; align-items: center; gap: 8px;
}
.menu-item:hover { background: #f5f7fa; color: #3498db; }
.menu-item.danger { color: #e74c3c; }
.menu-item.danger:hover { background: #fff5f5; }
.divider { height: 1px; background: #eee; margin: 4px 0; }

.modal-overlay {
  position: fixed; top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(0,0,0,0.4); z-index: 2000;
  display: flex; justify-content: center; align-items: center;
  backdrop-filter: blur(2px);
}
.modal-card {
  background: white; width: 400px; padding: 30px; border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.1);
  animation: modal-pop 0.3s cubic-bezier(0.18, 0.89, 0.32, 1.28);
}
.modal-card h3 { margin-top: 0; margin-bottom: 20px; font-size: 18px; color: #333; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 25px; }

.form-group { margin-bottom: 15px; }
.form-group label { display: block; font-size: 14px; font-weight: bold; margin-bottom: 8px; color: #555; }
.form-input, .form-select {
  width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; outline: none;
}
.form-input:focus, .form-select:focus { border-color: #3498db; }

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.fade-fast-enter-active, .fade-fast-leave-active { transition: opacity 0.1s; }
.fade-fast-enter-from, .fade-fast-leave-to { opacity: 0; transform: scale(0.95); }

@keyframes modal-pop {
  from { opacity: 0; transform: scale(0.9) translateY(20px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}
</style>