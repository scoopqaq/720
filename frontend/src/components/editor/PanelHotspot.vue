<template>
  <div class="panel-content">
    
    <div v-if="selectedHotspot" class="edit-mode">
      <div class="header-row">
        <button class="btn-icon" @click="$emit('cancel')">← 返回列表</button>
        <h3>编辑热点</h3>
      </div>

      <div class="scroll-area">
        <div class="section-block">
          <div class="form-group">
            <label>热点名称</label>
            <input type="text" v-model="localData.text" class="form-input" placeholder="请输入名称">
          </div>
          <div class="form-group checkbox-row">
             <input type="checkbox" id="showText" v-model="localData.show_text">
             <label for="showText">在场景中显示名称</label>
          </div>
          <div class="form-group">
            <label>交互类型</label>
            <select v-model="localData.type" class="form-select">
              <option value="scene">🏠 场景跳转</option>
              <option value="link">🔗 超链接 (新窗口)</option>
              <option value="text">📝 文字提示 (弹窗)</option>
              <option value="image">🖼️ 图片展示 (弹窗)</option>
              <option value="video">🎬 视频播放 (弹窗)</option>
            </select>
          </div>
          <div v-if="localData.type === 'scene'" class="form-group">
            <label>目标场景</label>
            <select v-model="localData.target_scene_id" class="form-select">
              <option :value="null">请选择目标场景...</option>
              <option v-for="s in otherScenes" :key="s.id" :value="s.id">{{ s.name }}</option>
            </select>
          </div>
          <div v-if="localData.type === 'link'" class="form-group">
            <label>链接地址 (URL)</label>
            <input type="text" v-model="localData.content" class="form-input" placeholder="https://...">
          </div>
          <div v-if="localData.type === 'image'" class="form-group">
             <label>图片地址 (URL)</label>
             <input type="text" v-model="localData.content" class="form-input">
          </div>
          <div v-if="localData.type === 'text'" class="form-group">
            <label>提示内容</label>
            <textarea v-model="localData.content" class="form-input" rows="3"></textarea>
          </div>
          <div v-if="localData.type === 'video'" class="form-group">
            <label>视频嵌入代码 (iframe)</label>
            <textarea v-model="localData.content" class="form-input" rows="4" placeholder='<iframe src="..."></iframe>'></textarea>
          </div>
        </div>

        <div class="section-block">
          <h3>图标样式</h3>
          <div class="tabs">
            <span :class="{active: iconTab==='system'}" @click="iconTab='system'">系统图标</span>
            <span :class="{active: iconTab==='custom'}" @click="iconTab='custom'">自定义</span>
          </div>
          <div class="icon-grid-wrapper">
            <div class="icon-grid">
              <div 
                v-for="icon in currentIcons" 
                :key="icon.id"
                class="icon-item" 
                :class="{ active: localData.icon_url === icon.url }"
                @click="selectIcon(icon.url)"
                @contextmenu.prevent="onIconContextMenu($event, icon)"
              >
                <img :src="getImageUrl(icon.url)" class="icon-img" />
              </div>
              <div v-if="iconTab === 'custom'" class="icon-item upload" @click="triggerIconUpload">
                <input type="file" ref="iconInput" style="display:none" accept="image/*" @change="handleIconUpload">
                <span>+</span>
              </div>
            </div>
          </div>
          <div v-if="iconTab === 'custom'" style="font-size:12px; color:#666; margin-top:5px;">
            提示：右键点击图标可删除
          </div>
          <div class="form-group" style="margin-top: 15px;">
            <label>图标大小 ({{ localData.scale }})</label>
            <input type="range" min="0.1" max="5.0" step="0.1" v-model.number="localData.scale">
          </div>
        </div>
      </div>

      <div class="footer-actions">
        <button class="btn-danger" @click="$emit('delete', selectedHotspot)">删除</button>
        <button class="btn-primary" @click="saveChanges">保存配置</button>
      </div>
    </div>

    <div v-else class="list-mode">
      <div class="action-bar">
        <button class="btn-block primary" @click="$emit('create')">➕ 新建热点 (画面中心)</button>
      </div>

      <div class="search-bar">
        <input type="text" v-model="searchQuery" placeholder="搜索热点名称..." class="search-input">
      </div>

      <div class="filter-tabs">
        <span :class="{active: filterType === 'all'}" @click="filterType = 'all'">全部</span>
        <span :class="{active: filterType === 'scene'}" @click="filterType = 'scene'">跳转</span>
        <span :class="{active: filterType === 'link'}" @click="filterType = 'link'">链接</span>
        <span :class="{active: filterType === 'text'}" @click="filterType = 'text'">文字</span>
        <span :class="{active: filterType === 'image'}" @click="filterType = 'image'">图片</span>
      </div>

      <div class="list-header">
        <span>共 {{ isFiltering ? filteredList.length : list.length }} 个热点</span>
        <button v-if="selectedIds.length>0" class="btn-text danger" @click="batchDelete">删除选中</button>
      </div>

      <div class="hotspot-list">
        <template v-if="isFiltering">
          <div v-if="filteredList.length === 0" class="empty-tip">无匹配热点</div>
          <div 
            v-for="h in filteredList" 
            :key="h.id" 
            class="list-item" 
            @click.stop="$emit('select', h)"
          >
            <input type="checkbox" :value="h.id" v-model="selectedIds" @click.stop>
            <img :src="getImageUrl(h.icon_url)" class="list-thumb" />
            <div class="list-info">
               <span class="name">{{ h.text || '未命名热点' }}</span>
               <span class="type-tag">{{ getTypeName(h.type) }}</span>
            </div>
          </div>
        </template>

        <template v-else>
          <draggable 
            v-model="proxyList" 
            item-key="id"
            handle=".drag-handle"
            ghost-class="ghost-item"
            animation="200"
          >
            <template #item="{ element: h }">
              <div class="list-item" @click.stop="$emit('select', h)">
                <div class="drag-handle" title="按住拖动排序">
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="#666"><path d="M9 3h2v18H9V3zm4 0h2v18h-2V3z"/></svg>
                </div>

                <input type="checkbox" :value="h.id" v-model="selectedIds" @click.stop>
                <img :src="getImageUrl(h.icon_url)" class="list-thumb" />
                <div class="list-info">
                   <span class="name">{{ h.text || '未命名热点' }}</span>
                   <span class="type-tag">{{ getTypeName(h.type) }}</span>
                </div>
              </div>
            </template>
          </draggable>
          <div v-if="list.length === 0" class="empty-tip">暂无热点，点击上方按钮创建</div>
        </template>
      </div>
    </div>

    <transition name="fade">
      <div 
        v-if="iconMenu.visible" 
        class="icon-context-menu" 
        :style="{ left: iconMenu.x + 'px', top: iconMenu.y + 'px' }"
      >
        <div class="menu-item danger" @click="deleteCustomIcon">🗑️ 删除此图标</div>
      </div>
    </transition>

  </div>
</template>

<script setup>
import { ref, watch, reactive, computed, onMounted, onBeforeUnmount } from 'vue';
import draggable from 'vuedraggable'; // [新增] 引入拖拽组件
import { getImageUrl, authFetch } from '../../utils/api';

const props = defineProps(['list', 'selectedHotspot', 'otherScenes', 'icons']);
const emit = defineEmits(['create', 'save', 'delete', 'select', 'cancel', 'batch-delete', 'refresh-icons', 'live-update', 'reorder']);

const localData = reactive({});
const iconTab = ref('system');
const iconInput = ref(null);
const selectedIds = ref([]);
const iconMenu = reactive({ visible: false, x: 0, y: 0, targetIcon: null });

const searchQuery = ref('');
const filterType = ref('all');

// 判断当前是否处于筛选状态
const isFiltering = computed(() => {
  return searchQuery.value.trim() !== '' || filterType.value !== 'all';
});

// 计算属性：用于 v-model 绑定拖拽组件
// 使用 get/set 来代理 props.list，当拖拽发生时，发射事件给父组件
const proxyList = computed({
  get: () => props.list,
  set: (newVal) => {
    emit('reorder', newVal); // 通知父组件更新列表顺序
  }
});

const filteredList = computed(() => {
  if (!props.list) return [];
  return props.list.filter(h => {
    const matchName = (h.text || '').toLowerCase().includes(searchQuery.value.toLowerCase());
    const matchType = filterType.value === 'all' || h.type === filterType.value;
    return matchName && matchType;
  });
});

const getTypeName = (type) => {
  const map = { scene: '跳转', link: '链接', text: '文字', image: '图片', video: '视频' };
  return map[type] || type;
};

const currentIcons = computed(() => {
  return (props.icons || []).filter(icon => icon.category === iconTab.value);
});

watch(localData, (newVal) => {
  if (!props.selectedHotspot) return;
  emit('live-update', { ...props.selectedHotspot, ...newVal });
}, { deep: true });

watch(() => props.selectedHotspot, (val) => {
  if (val) Object.assign(localData, JSON.parse(JSON.stringify(val)));
}, { immediate: true });

const saveChanges = () => emit('save', { ...props.selectedHotspot, ...localData });
const selectIcon = (url) => localData.icon_url = url;
const triggerIconUpload = () => iconInput.value.click();

const handleIconUpload = async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  if (file.size > 2 * 1024 * 1024) return alert("图片太大，请小于2MB");
  const formData = new FormData();
  formData.append('file', file);
  try {
    const res = await authFetch('/icons/', { method: 'POST', body: formData });
    if (res.ok) {
      const newIcon = await res.json();
      localData.icon_type = 'custom';
      localData.icon_url = newIcon.url; 
      emit('refresh-icons'); 
    } else { alert("上传失败"); }
  } catch (err) { alert("网络错误"); }
};

const onIconContextMenu = (e, icon) => {
  if (icon.category !== 'custom') return;
  e.preventDefault();
  iconMenu.x = e.clientX;
  iconMenu.y = e.clientY;
  iconMenu.targetIcon = icon;
  iconMenu.visible = true;
};

const deleteCustomIcon = async () => {
  if (!iconMenu.targetIcon) return;
  if (!confirm('确定要永久删除这个图标吗？')) return;
  try {
    const res = await authFetch(`/icons/${iconMenu.targetIcon.id}`, { method: 'DELETE' });
    if (res.ok) {
      emit('refresh-icons');
      if (localData.icon_url === iconMenu.targetIcon.url) {
        localData.icon_type = 'system';
        // 尝试找个默认的，或者不做处理让前端显示红块提醒用户
      }
    } else { alert("删除失败"); }
  } catch (e) { alert("网络错误"); } finally { iconMenu.visible = false; }
};

const batchDelete = () => {
    if(selectedIds.value.length === 0) return;
    if(confirm(`确定删除这 ${selectedIds.value.length} 个热点吗？`)) {
        emit('batch-delete', [...selectedIds.value]);
        selectedIds.value = [];
    }
};

const closeMenu = () => { iconMenu.visible = false; };
onMounted(() => window.addEventListener('click', closeMenu));
onBeforeUnmount(() => window.removeEventListener('click', closeMenu));
</script>

<style scoped>
/* 保持大部分原有样式，新增拖拽相关样式 */
.panel-content { display: flex; flex-direction: column; height: 100%; color: #ccc; padding: 20px; }
.header-row { display: flex; align-items: center; gap: 10px; margin-bottom: 20px; }
.btn-icon { background: none; border: 1px solid #555; color: #ddd; padding: 4px 8px; border-radius: 4px; cursor: pointer; }

.search-bar { margin-bottom: 10px; }
.search-input { width: 100%; padding: 8px; background: #333; border: 1px solid #444; color: white; border-radius: 4px; }
.filter-tabs { display: flex; gap: 5px; overflow-x: auto; padding-bottom: 10px; margin-bottom: 5px; border-bottom: 1px solid #333; }
.filter-tabs span { font-size: 11px; padding: 4px 8px; background: #222; border-radius: 10px; cursor: pointer; white-space: nowrap; color: #888; }
.filter-tabs span.active { background: #3498db; color: white; }
.empty-tip { text-align: center; color: #555; margin-top: 20px; font-size: 13px; }

/* 列表项样式调整 */
.list-item { display: flex; align-items: center; gap: 10px; padding: 10px; background: #2b2b2b; margin-bottom: 5px; border-radius: 4px; cursor: pointer; transition: background 0.2s; border: 1px solid transparent; }
.list-item:hover { background: #333; border-color: #444; }
.list-info { flex: 1; display: flex; flex-direction: column; }
.name { font-size: 13px; color: #eee; }
.type-tag { font-size: 10px; color: #888; margin-top: 2px; }
.list-thumb { width: 32px; height: 32px; object-fit: contain; background: rgba(0,0,0,0.3); border-radius: 4px; }

/* [新增] 拖拽手柄样式 */
.drag-handle { cursor: grab; padding: 0 4px; display: flex; align-items: center; opacity: 0.5; }
.drag-handle:hover { opacity: 1; }
.list-item:active .drag-handle { cursor: grabbing; }

/* [新增] 拖拽占位符样式 */
.ghost-item { opacity: 0.5; background: #3498db; border: 1px dashed #fff; }

/* 其他表单样式保持不变 */
.section-block { margin-bottom: 20px; }
.form-group { margin-bottom: 15px; }
.form-group label { display: block; font-size: 12px; margin-bottom: 5px; color: #aaa; }
.form-input, .form-select { width: 100%; padding: 8px; background: #333; border: 1px solid #444; color: white; border-radius: 4px; outline: none; }
.form-input:focus { border-color: #3498db; }
.checkbox-row { display: flex; align-items: center; gap: 8px; }
.checkbox-row input { margin: 0; }

.tabs { display: flex; border-bottom: 1px solid #444; margin-bottom: 15px; }
.tabs span { flex: 1; text-align: center; padding: 8px; font-size: 12px; cursor: pointer; color: #888; }
.tabs span.active { color: #3498db; border-bottom: 2px solid #3498db; font-weight: bold; }
.icon-grid-wrapper { max-height: 200px; overflow-y: auto; background: #222; padding: 10px; border-radius: 4px; }
.icon-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; }
.icon-item { aspect-ratio: 1; background: #333; border: 1px solid #444; display: flex; justify-content: center; align-items: center; cursor: pointer; border-radius: 4px; overflow: hidden; position: relative; }
.icon-item.active { border-color: #3498db; background: rgba(52,152,219,0.2); }
.icon-item.upload { border-style: dashed; color: #888; font-size: 20px; }
.icon-img { width: 80%; height: 80%; object-fit: contain; pointer-events: none; }

.btn-primary { width: 100%; padding: 10px; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer; }
.btn-danger { width: 100%; padding: 10px; background: #c0392b; color: white; border: none; border-radius: 4px; cursor: pointer; }
.btn-block { width: 100%; padding: 10px; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer; margin-bottom: 15px; }
.btn-text { background: none; border: none; cursor: pointer; }
.btn-text.danger { color: #e74c3c; }

.footer-actions { margin-top: auto; display: flex; gap: 10px; }
.list-header { display: flex; justify-content: space-between; font-size: 12px; color: #888; margin-bottom: 10px; }
.hotspot-list { flex: 1; overflow-y: auto; }

.icon-context-menu { position: fixed; z-index: 10000; background: white; border-radius: 4px; box-shadow: 0 4px 12px rgba(0,0,0,0.5); padding: 5px 0; min-width: 120px; }
.menu-item { padding: 8px 15px; font-size: 12px; color: #333; cursor: pointer; }
.menu-item:hover { background: #f0f0f0; }
.menu-item.danger { color: #e74c3c; }
</style>