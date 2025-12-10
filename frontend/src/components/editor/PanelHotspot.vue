<template>
    <div class="panel-content">
      <div v-if="selectedHotspot" class="hotspot-form">
        <div class="section-block">
          <h3>编辑热点</h3>
          
          <div class="form-group">
            <label>显示标题</label>
            <input type="text" v-model="selectedHotspot.text" class="form-input">
          </div>
  
          <div class="form-group">
            <label>跳转目标场景</label>
            <select v-model="selectedHotspot.target_scene_id" class="form-select">
              <option disabled value="">请选择...</option>
              <option v-for="s in otherScenes" :key="s.id" :value="s.id">
                {{ s.name }}
              </option>
            </select>
          </div>
  
          <div class="btn-row">
            <button class="btn-danger" @click="$emit('delete', selectedHotspot)">删除</button>
            <button class="btn-primary" @click="$emit('save', selectedHotspot)">保存</button>
          </div>
          
          <button class="btn-text" style="margin-top:10px; width:100%" @click="$emit('cancel')">取消选中</button>
        </div>
      </div>
  
      <div v-else class="empty-tip">
        <p>👋 操作指南：</p>
        <ul>
          <li><strong>双击画面</strong>：添加热点</li>
          <li><strong>点击红球</strong>：编辑热点</li>
        </ul>
        <hr class="divider">
        <div class="hotspot-list">
          <h4>当前场景热点 ({{ list.length }})</h4>
          <div 
            v-for="h in list" 
            :key="h.id" 
            class="hotspot-item"
            @click="$emit('select', h)"
          >
            <span class="icon">📍</span>
            <span class="name">{{ h.text }}</span>
            <span class="arrow">→</span>
          </div>
        </div>
      </div>
    </div>
  </template>
  
  <script setup>
  const props = defineProps(['list', 'selectedHotspot', 'otherScenes']);
  const emit = defineEmits(['save', 'delete', 'select', 'cancel']);
  </script>
  
  <style scoped>
  .panel-content { padding: 20px; color: #ccc; }
  .section-block h3 { font-size: 13px; color: #3498db; margin-bottom: 15px; font-weight: bold; }
  .form-group { margin-bottom: 15px; }
  .form-group label { display: block; font-size: 12px; margin-bottom: 5px; color: #aaa; }
  .form-input, .form-select { width: 100%; padding: 8px; background: #333; border: 1px solid #444; color: white; border-radius: 4px; outline: none; }
  .form-input:focus { border-color: #3498db; }
  .btn-row { display: flex; gap: 10px; margin-top: 20px; }
  .btn-danger { flex: 1; padding: 8px; background: #c0392b; border: none; color: white; border-radius: 4px; cursor: pointer; }
  .btn-primary { flex: 1; padding: 8px; background: #3498db; border: none; color: white; border-radius: 4px; cursor: pointer; }
  .btn-text { background: none; border: none; color: #666; cursor: pointer; font-size: 12px; }
  .btn-text:hover { color: #999; }
  
  .divider { border: 0; border-top: 1px solid #333; margin: 20px 0; }
  .hotspot-list h4 { font-size: 12px; color: #888; margin-bottom: 10px; }
  .hotspot-item { display: flex; align-items: center; gap: 10px; padding: 8px; background: #333; border-radius: 4px; margin-bottom: 5px; cursor: pointer; transition: background 0.2s; }
  .hotspot-item:hover { background: #444; }
  .hotspot-item .name { flex: 1; font-size: 13px; }
  .hotspot-item .arrow { color: #666; font-size: 12px; }
  .empty-tip { color: #888; font-size: 13px; line-height: 1.6; }
  .empty-tip ul { padding-left: 20px; }
  </style>