<template>
  <div 
    class="list-wrapper" 
    @mousedown="onMouseDown"
    @contextmenu.prevent="onBgContextMenu"
  >
    <div class="content-container">
      
      <div class="toolbar-container">
        <div class="toolbar-top">
          <div class="title-group">
            <h2>作品库</h2>
            <span class="count-badge">{{ filteredProjects.length }}</span>
          </div>
          
          <div class="actions-group">
            <div class="search-box">
              <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
              <input v-model="searchQuery" type="text" placeholder="搜索作品名称..." class="search-input">
              <button v-if="searchQuery" class="clear-btn" @click="searchQuery = ''">×</button>
            </div>

            <div class="sort-box">
              <span class="label">排序:</span>
              <select v-model="sortBy" class="sort-select">
                <option value="created_desc">📅 创建时间 (最新)</option>
                <option value="created_asc">📅 创建时间 (最早)</option>
                <option value="updated_desc">🕒 最后修改 (最近)</option>
                <option value="name_asc">🔤 名称 (A-Z)</option>
                <option value="category">📂 分类</option>
              </select>
            </div>

            <transition name="fade">
              <div v-if="isSelectionMode || selectedIds.length > 0" class="batch-actions">
                <span class="sel-count">选中 {{ selectedIds.length }}</span>
                <button class="btn btn-danger small" @click="confirmBatchDelete">删除</button>
                <button class="btn btn-text small" @click="exitSelectionMode">取消</button>
              </div>
            </transition>

            <button v-if="!isSelectionMode" class="btn btn-primary" @click="$emit('go-upload')">+ 新建</button>
          </div>
        </div>

        <div class="toolbar-bottom">
          <div class="category-tabs">
             <span :class="{active: filterCategory === ''}" @click="filterCategory = ''">全部</span>
            <span v-for="cat in availableCategories" :key="cat" :class="{active: filterCategory === cat}" @click="filterCategory = cat">{{ cat }}</span>
          </div>
        </div>
      </div>

      <div v-if="loading" class="loading-state"><div class="spinner"></div> 加载中...</div>
      
      <div v-else-if="filteredProjects.length === 0" class="empty-state">
        <p>🔍 没有找到匹配的作品</p>
        <button class="btn-text" @click="clearFilters">清除所有筛选</button>
      </div>
      
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
              <span>进入</span>
            </div>
            <div class="time-badge" v-if="p.updated_at">{{ formatTime(p.updated_at) }}</div>
          </div>
          
          <div class="card-info">
            <h3 class="project-name" v-html="highlightName(p.name)"></h3>
            <div class="meta-row">
              <span class="category-tag">{{ p.category }}</span>
              <span class="scene-count">{{ getSceneCount(p) }} 场景</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="dragBox.visible" class="drag-selection-box" :style="{ left: dragBox.left + 'px', top: dragBox.top + 'px', width: dragBox.width + 'px', height: dragBox.height + 'px' }"></div>

    <transition name="fade-fast">
      <div v-if="contextMenu.visible" class="context-menu" :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }" @mousedown.stop>
        <template v-if="contextMenu.targetId">
          <div class="menu-item" @click="handleMenuAction('enter')">👀 进入查看器</div>
          <div class="menu-item" @click="handleMenuAction('edit')">🛠️ 编辑全景图</div>
          <div class="divider"></div>
          <div class="menu-item" @click="handleMenuAction('rename')">✏️ 重命名 / 分类</div>
          <div class="divider"></div>
          <div class="menu-item danger" @click="handleMenuAction('delete')">🗑️ 删除此作品</div>
        </template>
        <template v-else>
          <div class="menu-item" @click="selectAll">✅ 全选本页</div>
          <div v-if="selectedIds.length > 0" class="menu-item danger" @click="confirmBatchDelete">🗑️ 删除选中 ({{ selectedIds.length }})</div>
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
import { authFetch, getImageUrl } from '../utils/api'; // [核心修正]

const emit = defineEmits(['select-project', 'go-upload', 'enter-editor']);
const gridRef = ref(null);
const projects = ref([]);
const loading = ref(true);

const filterCategory = ref("");
const searchQuery = ref("");
const sortBy = ref("created_desc");

const isSelectionMode = ref(false); 
const selectedIds = ref([]); 

const contextMenu = reactive({ visible: false, x: 0, y: 0, targetId: null, targetProject: null });
const modals = reactive({
  delete: { visible: false, ids: [] },
  rename: { visible: false, project: null, tempName: '', tempCategory: '' }
});
const dragBox = reactive({ visible: false, startX: 0, startY: 0, currentX: 0, currentY: 0, left: 0, top: 0, width: 0, height: 0 });
let isDragging = false;

const allCategories = ['家装', '商业空间', '样板房', '公共空间', '室外建筑', '展览展厅', '别墅', '园林景观', '酒店/民宿', '实景拍摄', '餐饮', '景区/风光', '其他'];

const availableCategories = computed(() => {
  const cats = new Set(projects.value.map(p => p.category));
  return Array.from(cats);
});

const filteredProjects = computed(() => {
  let result = projects.value;
  if (filterCategory.value) result = result.filter(p => p.category === filterCategory.value);
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase();
    result = result.filter(p => p.name.toLowerCase().includes(q));
  }
  return [...result].sort((a, b) => {
    switch (sortBy.value) {
      case 'created_desc': return new Date(b.created_at || 0) - new Date(a.created_at || 0);
      case 'created_asc': return new Date(a.created_at || 0) - new Date(b.created_at || 0);
      case 'updated_desc': return new Date(b.updated_at || 0) - new Date(a.updated_at || 0);
      case 'name_asc': return a.name.localeCompare(b.name, 'zh-CN');
      case 'category': return a.category.localeCompare(b.category, 'zh-CN');
      default: return 0;
    }
  });
});

const fetchProjects = async () => {
  loading.value = true;
  try {
    const res = await authFetch('/projects/'); // [修正] 使用 authFetch
    if (res.ok) projects.value = await res.json();
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
    contextMenu.visible = false; 
  }
};

const getSceneCount = (project) => {
  if (!project.groups) return 0;
  return project.groups.reduce((count, group) => count + (group.scenes ? group.scenes.length : 0), 0);
};

const getCoverImage = (project) => {
  if (project.cover_url) {
     return getImageUrl(`${project.cover_url}?t=${new Date(project.updated_at).getTime()}`);
  }
  
  if (project.groups && project.groups.length > 0) {
    for (const group of project.groups) {
      if (group.scenes && group.scenes.length > 0) {
        const s = group.scenes[0];
        const url = s.cover_url || s.image_url;
        return getImageUrl(url);
      }
    }
  }
  return 'https://via.placeholder.com/300x200?text=No+Scene';
};

const highlightName = (name) => {
  if (!searchQuery.value) return name;
  const reg = new RegExp(`(${searchQuery.value})`, 'gi');
  return name.replace(reg, '<span style="color:#3498db;font-weight:bold">$1</span>');
};

const formatTime = (isoString) => {
  if (!isoString) return '';
  const date = new Date(isoString);
  return `${date.getMonth()+1}-${date.getDate()} ${date.getHours()}:${date.getMinutes().toString().padStart(2,'0')}`;
};

const clearFilters = () => { searchQuery.value = ''; filterCategory.value = ''; };

const onCardClick = (project, event) => {
  if (contextMenu.visible) { contextMenu.visible = false; return; }
  if (isSelectionMode.value) toggleSelection(project.id);
  else emit('select-project', project.id);
};

const toggleSelection = (id) => { const index = selectedIds.value.indexOf(id); if (index === -1) selectedIds.value.push(id); else selectedIds.value.splice(index, 1); };
const enterSelectionMode = () => { isSelectionMode.value = true; contextMenu.visible = false; };
const exitSelectionMode = () => { isSelectionMode.value = false; selectedIds.value = []; contextMenu.visible = false; };
const selectAll = () => { selectedIds.value = filteredProjects.value.map(p => p.id); isSelectionMode.value = true; contextMenu.visible = false; };
const onBgContextMenu = (e) => showMenu(e, null);
const onCardContextMenu = (e, project) => { if (!selectedIds.value.includes(project.id)) { if (!isSelectionMode.value) selectedIds.value = []; if (!selectedIds.value.includes(project.id)) selectedIds.value.push(project.id); } showMenu(e, project); };
const showMenu = (e, target) => { contextMenu.visible = true; contextMenu.x = e.clientX; contextMenu.y = e.clientY; contextMenu.targetId = target ? target.id : null; contextMenu.targetProject = target; };
const closeMenu = () => { contextMenu.visible = false; };
const handleMenuAction = (action) => { const project = contextMenu.targetProject; contextMenu.visible = false; switch (action) { case 'enter': emit('select-project', project.id); break; case 'edit': emit('enter-editor', project.id); break; case 'delete': confirmBatchDelete(); break; case 'rename': openRenameModal(project); break; } };
const onMouseDown = (e) => { if (e.button !== 0) return; closeMenu(); if (e.target.closest('.project-card')) return; isDragging = true; dragBox.startX = e.clientX; dragBox.startY = e.clientY; dragBox.visible = true; dragBox.width = 0; dragBox.height = 0; if (!e.ctrlKey && !e.metaKey && !isSelectionMode.value) selectedIds.value = []; window.addEventListener('mousemove', onMouseMove); window.addEventListener('mouseup', onMouseUp); };
const onMouseMove = (e) => { if (!isDragging) return; const cx = e.clientX; const cy = e.clientY; dragBox.left = Math.min(dragBox.startX, cx); dragBox.top = Math.min(dragBox.startY, cy); dragBox.width = Math.abs(cx - dragBox.startX); dragBox.height = Math.abs(cy - dragBox.startY); if (dragBox.width < 5 && dragBox.height < 5) return; checkSelectionIntersection(); };
const checkSelectionIntersection = () => { if (!gridRef.value) return; const cards = gridRef.value.querySelectorAll('.project-card'); const sRect = { left: dragBox.left, top: dragBox.top, right: dragBox.left + dragBox.width, bottom: dragBox.top + dragBox.height }; cards.forEach(card => { const rect = card.getBoundingClientRect(); const intersect = !(rect.right < sRect.left || rect.left > sRect.right || rect.bottom < sRect.top || rect.top > sRect.bottom); const id = parseInt(card.getAttribute('data-id')); if (intersect) { if (!selectedIds.value.includes(id)) selectedIds.value.push(id); } }); };
const onMouseUp = () => { isDragging = false; dragBox.visible = false; window.removeEventListener('mousemove', onMouseMove); window.removeEventListener('mouseup', onMouseUp); };
const confirmBatchDelete = () => { if (selectedIds.value.length === 0) return; contextMenu.visible = false; modals.delete.ids = [...selectedIds.value]; modals.delete.visible = true; };

// [修正] authFetch
const executeDelete = async () => { 
  try { 
    const res = await authFetch('/projects/batch_delete/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(modals.delete.ids) }); 
    if (res.ok) { projects.value = projects.value.filter(p => !modals.delete.ids.includes(p.id)); selectedIds.value = []; modals.delete.visible = false; if (projects.value.length === 0) exitSelectionMode(); } 
  } catch (err) { alert("删除失败"); } 
};
const openRenameModal = (project) => { modals.rename.project = project; modals.rename.tempName = project.name; modals.rename.tempCategory = project.category; modals.rename.visible = true; };
// [修正] authFetch
const executeRename = async () => { 
  const p = modals.rename.project; 
  try { 
    const res = await authFetch(`/projects/${p.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: modals.rename.tempName, category: modals.rename.tempCategory }) }); 
    if (res.ok) { p.name = modals.rename.tempName; p.category = modals.rename.tempCategory; modals.rename.visible = false; } 
  } catch (err) { alert("修改失败"); } 
};

onMounted(() => { fetchProjects(); window.addEventListener('click', closeMenu); });
onBeforeUnmount(() => { window.removeEventListener('click', closeMenu); });
</script>

<style scoped>
/* 保持样式不变 */
.list-wrapper { min-height: 100vh; background-color: #f5f7fa; padding: 20px; font-family: 'PingFang SC', sans-serif; user-select: none; position: relative; }
.content-container { max-width: 1400px; margin: 0 auto; }
.toolbar-container { background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 24px; padding: 16px 24px; }
.toolbar-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.title-group { display: flex; align-items: center; gap: 10px; }
.title-group h2 { margin: 0; font-size: 20px; color: #2c3e50; }
.count-badge { background: #f0f2f5; color: #666; padding: 2px 8px; border-radius: 10px; font-size: 12px; }
.actions-group { display: flex; align-items: center; gap: 16px; }
.search-box { position: relative; display: flex; align-items: center; background: #f8f9fa; border: 1px solid #e1e4e8; border-radius: 6px; padding: 0 10px; width: 240px; transition: border-color 0.2s; }
.search-box:focus-within { border-color: #3498db; background: white; }
.search-icon { color: #999; }
.search-input { border: none; background: transparent; padding: 8px 5px; font-size: 14px; width: 100%; outline: none; }
.clear-btn { background: none; border: none; font-size: 18px; color: #999; cursor: pointer; padding: 0; line-height: 1; }
.clear-btn:hover { color: #666; }
.sort-box { display: flex; align-items: center; gap: 8px; font-size: 14px; color: #666; }
.sort-select { padding: 6px 10px; border: 1px solid #e1e4e8; border-radius: 4px; outline: none; background: white; font-size: 13px; cursor: pointer; }
.sort-select:hover { border-color: #bbb; }
.toolbar-bottom { border-top: 1px solid #eee; padding-top: 12px; }
.category-tabs { display: flex; gap: 15px; flex-wrap: wrap; }
.category-tabs span { font-size: 14px; color: #666; cursor: pointer; padding: 4px 12px; border-radius: 4px; transition: all 0.2s; }
.category-tabs span:hover { background: #f0f2f5; color: #333; }
.category-tabs span.active { background: #eef6fc; color: #3498db; font-weight: 600; }
.btn { border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 14px; transition: all 0.2s; font-weight: 500; }
.btn-primary { background: #333; color: white; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
.btn-primary:hover { background: #000; transform: translateY(-1px); }
.btn-danger { background: #fee; color: #e74c3c; }
.btn-danger:hover { background: #fdd; }
.btn.small { padding: 6px 12px; font-size: 13px; }
.btn-text { background: transparent; color: #666; padding: 5px 10px; }
.btn-text:hover { color: #333; background: #eee; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.project-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 24px; padding-bottom: 100px; }
.project-card { background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.03); position: relative; transition: all 0.2s; cursor: pointer; border: 2px solid transparent; }
.project-card:hover { transform: translateY(-4px); box-shadow: 0 10px 20px rgba(0,0,0,0.08); }
.project-card.selected { border-color: #3498db; background: #f0f9ff; }
.checkbox-indicator { position: absolute; top: 12px; left: 12px; z-index: 10; width: 24px; height: 24px; border-radius: 50%; background: white; border: 2px solid #ddd; display: flex; justify-content: center; align-items: center; }
.project-card.selected .checkbox-indicator { background: #3498db; border-color: #3498db; }
.project-card.selected .checkbox-indicator .check-circle { width: 10px; height: 10px; background: white; border-radius: 50%; }
.cover-wrapper { height: 160px; background: #f5f5f5; position: relative; overflow: hidden; }
.cover-wrapper img { width: 100%; height: 100%; object-fit: cover; transition: transform 0.3s; }
.project-card:hover img { transform: scale(1.05); }
.hover-overlay { position: absolute; top:0; left:0; width:100%; height:100%; background: rgba(0,0,0,0.2); display: flex; justify-content: center; align-items: center; opacity: 0; transition: opacity 0.2s; }
.project-card:hover .hover-overlay { opacity: 1; }
.hover-overlay span { color: white; border: 1px solid rgba(255,255,255,0.8); padding: 4px 12px; border-radius: 20px; font-size: 12px; backdrop-filter: blur(4px); }
.time-badge { position: absolute; bottom: 8px; right: 8px; background: rgba(0,0,0,0.6); color: rgba(255,255,255,0.9); font-size: 10px; padding: 2px 6px; border-radius: 4px; }
.card-info { padding: 14px; }
.project-name { margin: 0 0 8px; font-size: 15px; color: #333; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; line-height: 1.4; }
.meta-row { display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: #999; }
.category-tag { background: #f0f2f5; padding: 2px 8px; border-radius: 4px; color: #666; }
.loading-state { text-align: center; padding: 40px; color: #999; display: flex; flex-direction: column; align-items: center; }
.spinner { width: 30px; height: 30px; border: 3px solid #eee; border-top-color: #3498db; border-radius: 50%; animation: spin 1s infinite linear; margin-bottom: 10px; }
@keyframes spin { to { transform: rotate(360deg); } }
.empty-state { text-align: center; padding: 60px; color: #999; }
.drag-selection-box { position: fixed; border: 1px solid #3498db; background-color: rgba(52, 152, 219, 0.2); z-index: 9999; pointer-events: none; }
.context-menu { position: fixed; z-index: 10000; background: white; border-radius: 8px; box-shadow: 0 5px 20px rgba(0,0,0,0.15); padding: 6px 0; min-width: 160px; border: 1px solid #eee; }
.menu-item { padding: 10px 20px; font-size: 14px; color: #333; cursor: pointer; display: flex; align-items: center; gap: 8px; }
.menu-item:hover { background: #f5f7fa; color: #3498db; }
.menu-item.danger { color: #e74c3c; }
.menu-item.danger:hover { background: #fff5f5; }
.divider { height: 1px; background: #eee; margin: 4px 0; }
.modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.4); z-index: 2000; display: flex; justify-content: center; align-items: center; backdrop-filter: blur(2px); }
.modal-card { background: white; width: 400px; padding: 30px; border-radius: 12px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); animation: modal-pop 0.3s cubic-bezier(0.18, 0.89, 0.32, 1.28); }
.modal-card h3 { margin-top: 0; margin-bottom: 20px; font-size: 18px; color: #333; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 25px; }
.form-group { margin-bottom: 15px; }
.form-group label { display: block; font-size: 14px; font-weight: bold; margin-bottom: 8px; color: #555; }
.form-input, .form-select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; outline: none; }
.form-input:focus { border-color: #3498db; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.fade-fast-enter-active, .fade-fast-leave-active { transition: opacity 0.1s; }
.fade-fast-enter-from, .fade-fast-leave-to { opacity: 0; transform: scale(0.95); }
@keyframes modal-pop { from { opacity: 0; transform: scale(0.9) translateY(20px); } to { opacity: 1; transform: scale(1) translateY(0); } }
</style>