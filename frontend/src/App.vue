<script setup>
import { ref } from 'vue';
import PanoramaViewer from './components/PanoramaViewer.vue';
import CreateProject from './components/CreateProject.vue';

// 简单的路由状态: 'create' 或 'view'
const currentView = ref('create'); 
// 暂存创建成功的项目 ID
const activeProjectId = ref(null);
</script>

<template>
  <div>
    <div style="position:fixed; top:0; right:0; z-index:9999; padding:10px;">
      <button @click="currentView = 'create'">新建项目</button>
      <button @click="currentView = 'view'">查看全景</button>
    </div>

    <CreateProject v-if="currentView === 'create'" />
    <PanoramaViewer v-else />
  </div>
</template>