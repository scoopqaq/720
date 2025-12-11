<template>
  <div class="panel-content">
    
    <div v-if="selectedHotspot" class="edit-mode">
      <div class="header-row">
        <button class="btn-icon" @click="$emit('cancel')">← 返回</button>
        <h3>编辑热点</h3>
      </div>

      <div class="scroll-area">
        <div class="section-block">
          <div class="form-group">
            <label>标题</label>
            <input type="text" v-model="localData.text" class="form-input" placeholder="未命名">
          </div>
          <div class="form-group">
            <label>类型</label>
            <select v-model="localData.type" class="form-select">
              <option value="scene">🏠 场景跳转</option>
              <option value="link">🔗 超链接</option>
              <option value="text">📝 文字提示</option>
              <option value="image">🖼️ 图片弹窗</option>
            </select>
          </div>
          
          <div v-if="localData.type === 'scene'" class="form-group">
            <label>目标场景</label>
            <select v-model="localData.target_scene_id" class="form-select">
              <option :value="null">请选择...</option>
              <option v-for="s in otherScenes" :key="s.id" :value="s.id">{{ s.name }}</option>
            </select>
          </div>

          <div v-if="localData.type === 'link' || localData.type === 'image'" class="form-group">
            <label>{{ localData.type === 'link' ? '链接地址' : '图片地址' }}</label>
            <input type="text" v-model="localData.content" class="form-input">
          </div>
          
          <div v-if="localData.type === 'text'" class="form-group">
            <label>内容</label>
            <textarea v-model="localData.content" class="form-input" rows="3"></textarea>
          </div>
        </div>

        <div class="section-block">
          <h3>图标外观</h3>
          <div class="tabs">
            <span :class="{active: iconTab==='system'}" @click="iconTab='system'">系统</span>
            <span :class="{active: iconTab==='custom'}" @click="iconTab='custom'">我的</span>
          </div>

          <div class="icon-grid-wrapper">
            <div class="icon-grid">
              <div 
                v-for="icon in currentIcons" 
                :key="icon.id"
                class="icon-item" 
                :class="{ active: localData.icon_url === icon.url }"
                @click="selectIcon(icon.url)"
              >
                <img :src="getImageUrl(icon.url)" class="icon-img" />
              </div>
              <div v-if="iconTab === 'custom'" class="icon-item upload" @click="triggerIconUpload">
                <input type="file" ref="iconInput" style="display:none" accept="image/*" @change="handleIconUpload">
                <span>+</span>
              </div>
            </div>
          </div>

          <div class="form-group" style="margin-top: 15px;">
            <label>大小 ({{ localData.scale }})</label>
            <input type="range" min="0.5" max="5.0" step="0.1" v-model.number="localData.scale">
          </div>
          <div class="form-group checkbox-row">
            <input type="checkbox" id="fs" v-model="localData.use_fixed_size">
            <label for="fs">固定屏幕大小</label>
          </div>
        </div>
      </div>

      <div class="footer-actions">
        <button class="btn-danger" @click="$emit('delete', selectedHotspot)">删除</button>
        <button class="btn-primary" @click="saveChanges">保存</button>
      </div>
    </div>

    <div v-else class="list-mode">
      <div class="action-bar">
        <button class="btn-block primary" @click="$emit('create')">➕ 添加热点 (画面中心)</button>
      </div>
      <div class="list-header">
        <span>列表 ({{ list.length }})</span>
        <button v-if="selectedIds.length>0" class="btn-text danger" @click="batchDelete">删选中</button>
      </div>
      <div class="hotspot-list">
        <div v-for="h in list" :key="h.id" class="list-item" @click.stop="$emit('select', h)">
          <input type="checkbox" :value="h.id" v-model="selectedIds" @click.stop>
          <img :src="getImageUrl(h.icon_url)" class="list-thumb" />
          <span class="name">{{ h.text || '未命名' }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, reactive, computed, onMounted } from 'vue';
import { authFetch, getImageUrl } from '../../utils/api';

const props = defineProps(['list', 'selectedHotspot', 'otherScenes']);
const emit = defineEmits(['create', 'save', 'delete', 'select', 'cancel', 'batch-delete']);

const localData = reactive({});
const iconInput = ref(null);
const selectedIds = ref([]);
const iconTab = ref('system'); 
const iconLibrary = ref([]);

// 加载图标库 (自动带 Token，后端会返回 system + 该用户的 custom)
const fetchIcons = async () => {
  try {
    const res = await authFetch('/icons/');
    if (res.ok) iconLibrary.value = await res.json();
  } catch(e) { console.error(e); }
};

const currentIcons = computed(() => iconLibrary.value.filter(icon => icon.category === iconTab.value));

watch(() => props.selectedHotspot, (val) => {
  if (val) Object.assign(localData, JSON.parse(JSON.stringify(val)));
}, { immediate: true });

onMounted(fetchIcons);

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
    // 修复上传文件时的 Content-Type 问题
    const res = await authFetch('/icons/', { 
      method: 'POST', 
      body: formData,
      // 不设置 Content-Type，让浏览器自动设置 multipart/form-data
      headers: {} 
    });
    if (res.ok) {
      const newIcon = await res.json();
      iconLibrary.value.push(newIcon);
      localData.icon_type = 'custom';
      localData.icon_url = newIcon.url;
    } else {
      // 添加更多错误信息帮助调试
      const errorText = await res.text();
      console.error('Upload failed with status:', res.status, 'Response:', errorText);
      alert(`上传失败: ${res.status} - ${errorText}`);
    }
  } catch (err) { 
    console.error('Upload error:', err);
    alert(`网络错误: ${err.message}`); 
  }
};

const batchDelete = () => {
  if(confirm(`删除 ${selectedIds.value.length} 个?`)) {
    emit('batch-delete', [...selectedIds.value]);
    selectedIds.value = [];
  }
};
</script>

<style scoped>
/* 样式保持不变 */
.panel-content { display: flex; flex-direction: column; height: 100%; color: #ccc; padding: 20px; }
.header-row { display: flex; align-items: center; gap: 10px; margin-bottom: 20px; }
.btn-icon { background: none; border: 1px solid #555; color: #ddd; padding: 4px 8px; border-radius: 4px; cursor: pointer; }
.section-block { margin-bottom: 20px; }
.form-group { margin-bottom: 15px; }
.form-group label { display: block; font-size: 12px; margin-bottom: 5px; color: #aaa; }
.form-input, .form-select { width: 100%; padding: 8px; background: #333; border: 1px solid #444; color: white; border-radius: 4px; outline: none; }
.form-input:focus { border-color: #3498db; }
.tabs { display: flex; border-bottom: 1px solid #444; margin-bottom: 15px; }
.tabs span { flex: 1; text-align: center; padding: 8px; font-size: 12px; cursor: pointer; color: #888; }
.tabs span.active { color: #3498db; border-bottom: 2px solid #3498db; font-weight: bold; }
.icon-grid-wrapper { max-height: 200px; overflow-y: auto; background: #222; padding: 10px; border-radius: 4px; }
.icon-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; }
.icon-item { aspect-ratio: 1; background: #333; border: 1px solid #444; display: flex; justify-content: center; align-items: center; cursor: pointer; border-radius: 4px; overflow: hidden; }
.icon-item.active { border-color: #3498db; background: rgba(52,152,219,0.2); }
.icon-item.upload { border-style: dashed; color: #888; font-size: 20px; }
.icon-img { width: 80%; height: 80%; object-fit: contain; }
.btn-row { display: flex; gap: 10px; margin-top: 20px; }
.btn-primary, .btn-danger { flex: 1; padding: 10px; border: none; border-radius: 4px; cursor: pointer; }
.btn-primary { background: #3498db; color: white; }
.btn-danger { background: #c0392b; color: white; }
.footer-actions { margin-top: auto; display: flex; gap: 10px; }
.list-mode .action-bar { margin-bottom: 20px; }
.list-header { display: flex; justify-content: space-between; font-size: 12px; color: #888; margin-bottom: 10px; }
.btn-text { background: none; border: none; cursor: pointer; }
.btn-text.danger { color: #e74c3c; }
.hotspot-list { flex: 1; overflow-y: auto; }
.list-item { display: flex; align-items: center; gap: 10px; padding: 10px; background: #2b2b2b; margin-bottom: 5px; border-radius: 4px; cursor: pointer; }
.list-item:hover { background: #333; }
.list-thumb { width: 24px; height: 24px; object-fit: contain; }
.name { font-size: 13px; color: #ddd; flex: 1; }
.btn-block { width: 100%; padding: 10px; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer; }
.checkbox-row { display: flex; align-items: center; gap: 8px; }
.checkbox-row input { margin: 0; }
</style>