<template>
  <div class="app-layout">
    <header class="navbar" v-if="currentView !== 'viewer' && currentView !== 'editor'">
      <div class="logo">VR Panorama Editor</div>
      <div class="nav-links">
        <button 
          :class="{ active: currentView === 'upload' }" 
          @click="currentView = 'upload'"
        >
          上传作品
        </button>
        <button 
          :class="{ active: currentView === 'list' }" 
          @click="currentView = 'list'"
        >
          作品列表
        </button>
      </div>
    </header>

    <main class="main-content">
      
      <CreateProject 
        v-if="currentView === 'upload'" 
        @created="handleProjectCreated" 
      />

      <ProjectList 
        v-else-if="currentView === 'list'"
        @go-upload="currentView = 'upload'"
        @select-project="handleSelectProject"
        @enter-editor="handleEnterEditor"
      />

      <PanoramaViewer 
        v-else-if="currentView === 'viewer'"
        :project-id="activeProjectId"
        @back="currentView = 'list'"
      />

      <PanoramaEditor
        v-else-if="currentView === 'editor'"
        :project-id="activeProjectId"
        @back="currentView = 'list'"
      />

    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import CreateProject from './components/CreateProject.vue';
import ProjectList from './components/ProjectList.vue';
import PanoramaViewer from './components/PanoramaViewer.vue';
// [重要] 引入编辑器组件
import PanoramaEditor from './components/PanoramaEditor.vue';

// 视图状态: 'upload' | 'list' | 'viewer' | 'editor'
const currentView = ref('list'); 
const activeProjectId = ref(null);

// 上传成功 -> 去列表
const handleProjectCreated = () => {
  currentView.value = 'list';
};

// 点击列表卡片 -> 去查看器
const handleSelectProject = (id) => {
  activeProjectId.value = id;
  currentView.value = 'viewer';
};

// [关键] 点击右键编辑 -> 去编辑器
const handleEnterEditor = (id) => {
  activeProjectId.value = id;
  currentView.value = 'editor';
};
</script>

<style>
/* 全局样式 */
body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #f5f7fa; }
.app-layout { display: flex; flex-direction: column; height: 100vh; }

.navbar {
  height: 60px; background: white; border-bottom: 1px solid #eee;
  display: flex; justify-content: space-between; align-items: center;
  padding: 0 40px; flex-shrink: 0; z-index: 100;
}
.logo { font-weight: bold; font-size: 20px; color: #333; }

.nav-links button {
  background: none; border: none; padding: 0 20px; height: 60px;
  font-size: 16px; cursor: pointer; color: #666; position: relative;
}
.nav-links button:hover { color: #3498db; }
.nav-links button.active { color: #3498db; font-weight: 600; }
.nav-links button.active::after {
  content: ''; position: absolute; bottom: 0; left: 0; width: 100%; height: 3px; background: #3498db;
}

.main-content { flex: 1; position: relative; overflow-y: auto; overflow-x: hidden; }
</style>