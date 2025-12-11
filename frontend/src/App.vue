<template>
  <Login v-if="!isLoggedIn" @login-success="handleLoginSuccess" />
  
  <div v-else class="app-layout">
    <header class="navbar" v-if="currentView !== 'viewer' && currentView !== 'editor'">
      <div class="logo-area">
        <span class="logo-text">VR Editor</span>
        <span class="user-pill">{{ username }}</span>
      </div>
      
      <div class="nav-links">
        <button 
          :class="{ active: currentView === 'upload' }" 
          @click="currentView = 'upload'"
        >
          ☁️ 上传作品
        </button>
        <button 
          :class="{ active: currentView === 'list' }" 
          @click="currentView = 'list'"
        >
          📂 作品库
        </button>
        <div class="divider"></div>
        <button class="logout-btn" @click="logout">
          退出
        </button>
      </div>
    </header>

    <main class="main-content">
      <CreateProject v-if="currentView === 'upload'" @created="currentView = 'list'" />
      
      <ProjectList 
        v-else-if="currentView === 'list'"
        @go-upload="currentView = 'upload'"
        @select-project="(id) => { activeProjectId = id; currentView = 'viewer'; }"
        @enter-editor="(id) => { activeProjectId = id; currentView = 'editor'; }"
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
import { ref, onMounted } from 'vue';
import Login from './components/Login.vue';
import CreateProject from './components/CreateProject.vue';
import ProjectList from './components/ProjectList.vue';
import PanoramaViewer from './components/PanoramaViewer.vue';
import PanoramaEditor from './components/PanoramaEditor.vue';

const isLoggedIn = ref(false);
const username = ref('');
const currentView = ref('list');
const activeProjectId = ref(null);

const checkLogin = () => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    isLoggedIn.value = true;
    username.value = localStorage.getItem('username') || 'User';
  } else {
    isLoggedIn.value = false;
  }
};

const handleLoginSuccess = () => {
  // 重新检查登录状态
  checkLogin();
  currentView.value = 'list';
};

const logout = () => {
  localStorage.removeItem('auth_token');
  localStorage.removeItem('username');
  isLoggedIn.value = false;
  currentView.value = 'list';
};

onMounted(checkLogin);
</script>

<style>
/* 全局重置 */
html, body { margin: 0; padding: 0; height: 100%; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background-color: #f5f7fa; }

.app-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

/* --- 导航栏样式核心修复 --- */
.navbar {
  height: 60px;
  background: #ffffff;
  border-bottom: 1px solid #e0e0e0;
  display: flex;
  justify-content: space-between; /* 左右推开 */
  align-items: center;
  padding: 0 30px;
  flex-shrink: 0;
  box-shadow: 0 2px 4px rgba(0,0,0,0.02);
  z-index: 100;
}

.logo-area {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-text {
  font-size: 20px;
  font-weight: 800;
  color: #2c3e50;
  letter-spacing: -0.5px;
}

.user-pill {
  background: #f0f2f5;
  color: #666;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 12px;
  font-weight: 500;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 10px;
}

.nav-links button {
  background: transparent;
  border: none;
  padding: 0 16px;
  height: 60px; /* 撑满高度 */
  font-size: 15px;
  color: #666;
  cursor: pointer;
  position: relative;
  transition: color 0.2s;
  font-weight: 500;
}

.nav-links button:hover {
  color: #3498db;
  background-color: #f9f9f9;
}

/* 选中状态：底部加蓝条 */
.nav-links button.active {
  color: #3498db;
  font-weight: 600;
}
.nav-links button.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 3px;
  background: #3498db;
}

.divider {
  width: 1px;
  height: 20px;
  background: #ddd;
  margin: 0 5px;
}

.logout-btn {
  color: #e74c3c !important; /* 强制红色 */
}
.logout-btn:hover {
  background-color: #fff5f5 !important;
}

/* 内容区域 */
.main-content {
  flex: 1;
  position: relative;
  overflow: hidden; /* 防止出现双重滚动条 */
}
</style>