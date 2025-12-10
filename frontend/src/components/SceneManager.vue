<template>
    <div class="scene-manager">
      <div class="groups-bar">
        <div 
          v-for="group in groups" 
          :key="group.id"
          class="group-tab"
          :class="{ active: currentGroupId === group.id }"
          @click="switchGroup(group.id)"
          @contextmenu.prevent="onContextMenu($event, 'group', group)"
        >
          {{ group.name }} ({{ group.scenes.length }})
        </div>
        <div class="add-group-btn" @click="addNewGroup" title="新建分组">+</div>
      </div>
  
      <div class="scenes-list">
        <div class="scenes-scroll-area">
          <div 
            v-for="scene in currentGroupScenes" 
            :key="scene.id" 
            class="scene-card"
            :class="{ active: currentSceneId === scene.id }"
            @click="$emit('change-scene', scene.id)"
            @contextmenu.prevent="onContextMenu($event, 'scene', scene)"
          >
            <img :src="getThumb(scene)" loading="lazy" />
            <div class="scene-name" :title="scene.name">{{ scene.name }}</div>
          </div>
  
          <div class="add-scene-card" @click="triggerUpload">
            <input 
              type="file" 
              ref="fileInput" 
              accept="image/jpeg,image/png,image/jpg" 
              style="display: none"
              @change="handleUpload"
            />
            <div class="icon">+</div>
            <div class="text">添加场景</div>
          </div>
        </div>
      </div>
  
      <transition name="fade-fast">
        <div v-if="contextMenu.visible" class="context-menu" :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }" @mousedown.stop>
          
          <template v-if="contextMenu.type === 'group'">
            <div class="item" @click="handleRenameGroup">✏️ 重命名分组</div>
            <div class="item danger" @click="handleDeleteGroupClick">🗑️ 删除分组</div>
          </template>
  
          <template v-if="contextMenu.type === 'scene'">
            <div class="item" @click="handleRenameScene">✏️ 重命名场景</div>
            <div class="item danger" @click="handleDeleteSceneClick">🗑️ 删除场景</div>
          </template>
  
        </div>
      </transition>
  
      <transition name="fade">
        <div v-if="modalState.visible" class="custom-modal-overlay" @click.self="closeModal">
          <div class="custom-modal">
            <div class="modal-title">{{ modalState.title }}</div>
            <div class="modal-body">{{ modalState.message }}</div>
            <div class="modal-footer">
              <button v-if="modalState.type === 'alert'" class="btn-primary" @click="closeModal">知道了</button>
              <template v-else>
                <button class="btn-text" @click="closeModal">取消</button>
                <button class="btn-danger" @click="modalState.confirmCallback">确认删除</button>
              </template>
            </div>
          </div>
        </div>
      </transition>
  
    </div>
  </template>
  
  <script setup>
  import { ref, computed, reactive, onMounted, onBeforeUnmount } from 'vue';
  
  const props = defineProps({
    projectData: { type: Object, required: true },
    currentSceneId: { type: Number }
  });
  
  const emit = defineEmits(['change-scene', 'refresh-data']);
  
  const currentGroupId = ref(null);
  const fileInput = ref(null);
  
  const contextMenu = reactive({ visible: false, x: 0, y: 0, type: null, target: null });
  const modalState = reactive({ visible: false, type: 'confirm', title: '', message: '', confirmCallback: null });
  
  const groups = computed(() => props.projectData.groups || []);
  
  const currentGroupScenes = computed(() => {
    const group = groups.value.find(g => g.id === currentGroupId.value);
    return group ? group.scenes : [];
  });
  
  const initSelection = () => {
    if (groups.value.length === 0) return;
    if (props.currentSceneId) {
      const foundGroup = groups.value.find(g => g.scenes.some(s => s.id === props.currentSceneId));
      if (foundGroup) {
        currentGroupId.value = foundGroup.id;
        return;
      }
    }
    if (!currentGroupId.value || !groups.value.find(g => g.id === currentGroupId.value)) {
      currentGroupId.value = groups.value[0].id;
    }
  };
  
  const switchGroup = (id) => { currentGroupId.value = id; };
  
  const getThumb = (scene) => {
    const url = scene.cover_url || scene.image_url;
    return `http://127.0.0.1:8000${url}?t=${new Date().getTime()}`;
  };
  
  const onContextMenu = (e, type, target) => {
    contextMenu.visible = true;
    const menuHeight = 80; 
    contextMenu.x = e.clientX;
    contextMenu.y = e.clientY - menuHeight; 
    contextMenu.type = type;
    contextMenu.target = target;
  };
  
  const closeMenu = () => contextMenu.visible = false;
  
  // --- 分组管理 ---
  
  const addNewGroup = async () => {
    const name = prompt("请输入新分组名称", "新区域");
    if (!name) return;
    try {
      const res = await fetch('http://127.0.0.1:8000/groups/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, project_id: props.projectData.id })
      });
      if (res.ok) emit('refresh-data');
    } catch (e) { alert("添加失败"); }
  };
  
  const handleRenameGroup = async () => {
    const group = contextMenu.target;
    closeMenu();
    const newName = prompt("重命名分组", group.name);
    if (!newName || newName === group.name) return;
    await fetch(`http://127.0.0.1:8000/groups/${group.id}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: newName })
    });
    emit('refresh-data');
  };
  
  // [修改] 删除分组逻辑
  const handleDeleteGroupClick = () => {
    const groupToDelete = contextMenu.target;
    closeMenu();
  
    // 1. 如果只剩这一个分组，绝对不能删（项目结构必须完整）
    if (groups.value.length <= 1) {
      showModal('alert', '无法删除', '项目必须至少保留一个分组。');
      return;
    }
  
    // 2. [核心修复] 计算如果不算这个组，项目里还剩多少张图？
    // 我们遍历所有组，把除了当前要删的组之外的场景数加起来
    const scenesInOtherGroups = groups.value.reduce((total, g) => {
      if (g.id === groupToDelete.id) return total; // 跳过要删除的组
      return total + (g.scenes ? g.scenes.length : 0);
    }, 0);
  
    // 如果其他组全是空的，总数为0，说明删了这个组项目就没图了 -> 拦截！
    if (scenesInOtherGroups === 0) {
      showModal('alert', '无法删除', 
        '删除该分组后，项目将没有任何场景图片。\n请先在其他分组上传图片，或保留此分组。'
      );
      return;
    }
  
    // 3. 正常逻辑：如果有内容则警告，没内容则直接删
    if (groupToDelete.scenes.length > 0) {
      showModal('confirm', '删除确认', 
        `分组“${groupToDelete.name}”内包含 ${groupToDelete.scenes.length} 个场景。\n删除分组将永久删除这些场景，确定吗？`, 
        () => executeDeleteGroup(groupToDelete.id)
      );
    } else {
      executeDeleteGroup(groupToDelete.id);
    }
  };
  
  const executeDeleteGroup = async (id) => {
    closeModal();
    await fetch(`http://127.0.0.1:8000/groups/${id}`, { method: 'DELETE' });
    emit('refresh-data');
  };
  
  // --- 场景管理 ---
  
  const handleRenameScene = async () => {
    const scene = contextMenu.target;
    closeMenu();
    const newName = prompt("重命名场景", scene.name);
    if (!newName || newName === scene.name) return;
    await fetch(`http://127.0.0.1:8000/scenes/${scene.id}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: newName })
    });
    emit('refresh-data');
  };
  
  // [修改] 删除场景逻辑
  const handleDeleteSceneClick = () => {
    const scene = contextMenu.target;
    closeMenu();
    
    // 1. [核心修复] 计算全项目总场景数
    const totalScenes = groups.value.reduce((total, g) => total + (g.scenes ? g.scenes.length : 0), 0);
  
    // 如果全项目只剩这一张图，不管在哪个分组，都不能删
    if (totalScenes <= 1) {
      showModal('alert', '无法删除', '项目必须至少保留一张场景图片。');
      return;
    }
  
    // 2. 正常确认
    showModal('confirm', '删除场景', 
      `确定要删除场景“${scene.name}”吗？\n此操作不可撤销。`,
      () => executeDeleteScene(scene.id)
    );
  };
  
  const executeDeleteScene = async (id) => {
    closeModal();
    await fetch(`http://127.0.0.1:8000/scenes/${id}`, { method: 'DELETE' });
    emit('refresh-data');
  };
  
  // --- 通用 ---
  const showModal = (type, title, message, callback) => {
    modalState.type = type;
    modalState.title = title;
    modalState.message = message;
    modalState.confirmCallback = callback;
    modalState.visible = true;
  };
  const closeModal = () => { modalState.visible = false; };
  
  const triggerUpload = () => { fileInput.value.click(); };
  const handleUpload = async (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    const formData = new FormData();
    formData.append('files', files[0]);
    try {
      const res = await fetch(`http://127.0.0.1:8000/groups/${currentGroupId.value}/upload_scene`, {
        method: 'POST', body: formData
      });
      if (res.ok) emit('refresh-data');
    } catch (e) { alert("上传失败"); } 
    finally { e.target.value = ''; }
  };
  
  onMounted(() => {
    window.addEventListener('click', closeMenu);
    setTimeout(initSelection, 500); 
  });
  onBeforeUnmount(() => window.removeEventListener('click', closeMenu));
  
  defineExpose({ initSelection });
  </script>
  
  <style scoped>
  .scene-manager {
    position: absolute; bottom: 0; left: 0; width: 100%; height: 140px;
    background: rgba(30,30,30,0.95); border-top: 1px solid #444;
    display: flex; flex-direction: column; z-index: 50; user-select: none;
  }
  
  .groups-bar {
    height: 36px; background: #252525; display: flex; align-items: center; padding: 0 10px; border-bottom: 1px solid #333;
  }
  .group-tab {
    padding: 0 15px; height: 36px; line-height: 36px; font-size: 13px; color: #aaa; cursor: pointer;
    border-right: 1px solid #333; transition: all 0.2s;
  }
  .group-tab:hover { background: #333; color: #eee; }
  .group-tab.active { background: #333; color: #3498db; font-weight: bold; border-top: 2px solid #3498db; }
  .add-group-btn {
    width: 36px; height: 36px; display: flex; align-items: center; justify-content: center;
    font-size: 18px; color: #666; cursor: pointer;
  }
  .add-group-btn:hover { color: #fff; background: #444; }
  
  .scenes-list { flex: 1; overflow-x: auto; overflow-y: hidden; padding: 10px; }
  .scenes-scroll-area { display: flex; gap: 10px; height: 100%; }
  
  .scene-card {
    width: 120px; height: 100%; background: #222; border-radius: 4px; overflow: hidden;
    position: relative; cursor: pointer; border: 2px solid transparent; flex-shrink: 0;
  }
  .scene-card img { width: 100%; height: 100%; object-fit: cover; opacity: 0.7; transition: opacity 0.2s; }
  .scene-card:hover img { opacity: 1; }
  .scene-card.active { border-color: #3498db; }
  .scene-card.active img { opacity: 1; }
  
  .scene-name {
    position: absolute; bottom: 0; left: 0; width: 100%; background: rgba(0,0,0,0.6);
    color: white; font-size: 12px; padding: 2px 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    text-align: center;
  }
  
  .add-scene-card {
    width: 80px; height: 100%; border: 1px dashed #555; border-radius: 4px;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    cursor: pointer; color: #777; flex-shrink: 0;
  }
  .add-scene-card:hover { border-color: #777; color: #ccc; }
  .add-scene-card .icon { font-size: 24px; margin-bottom: 5px; }
  .add-scene-card .text { font-size: 12px; }
  
  .context-menu {
    position: fixed; z-index: 9999; background: #333; border: 1px solid #444; border-radius: 4px; padding: 5px 0; min-width: 120px;
  }
  .context-menu .item { padding: 8px 15px; font-size: 13px; color: #ddd; cursor: pointer; }
  .context-menu .item:hover { background: #444; }
  .context-menu .item.danger { color: #e74c3c; }
  
  .custom-modal-overlay {
    position: fixed; top: 0; left: 0; width: 100%; height: 100%;
    background: rgba(0,0,0,0.5); z-index: 10000;
    display: flex; justify-content: center; align-items: center;
    backdrop-filter: blur(2px);
  }
  .custom-modal {
    background: #2c2c2c; width: 360px; padding: 24px; border-radius: 8px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.5); border: 1px solid #444; color: #eee;
    transform: translateY(0); transition: all 0.3s;
  }
  .modal-title { font-size: 16px; font-weight: bold; margin-bottom: 12px; color: #fff; }
  .modal-body { font-size: 14px; color: #bbb; margin-bottom: 24px; line-height: 1.5; white-space: pre-wrap; }
  .modal-footer { display: flex; justify-content: flex-end; gap: 10px; }
  
  .btn-text { background: transparent; border: 1px solid #555; color: #ccc; padding: 6px 16px; border-radius: 4px; cursor: pointer; font-size: 13px; }
  .btn-text:hover { background: #333; color: white; }
  .btn-danger { background: #e74c3c; border: none; color: white; padding: 6px 16px; border-radius: 4px; cursor: pointer; font-size: 13px; font-weight: bold; }
  .btn-danger:hover { background: #c0392b; }
  .btn-primary { background: #3498db; border: none; color: white; padding: 6px 16px; border-radius: 4px; cursor: pointer; font-size: 13px; font-weight: bold; }
  .btn-primary:hover { background: #2980b9; }
  
  .fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
  .fade-enter-from, .fade-leave-to { opacity: 0; }
  .fade-fast-enter-active, .fade-fast-leave-active { transition: opacity 0.1s; }
  .fade-fast-enter-from, .fade-fast-leave-to { opacity: 0; transform: scale(0.95); }
  </style>