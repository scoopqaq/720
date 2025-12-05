<template>
    <div class="list-wrapper">
      <div class="content-container">
        <div class="header">
          <h2>我的作品库</h2>
          <p>共 {{ projects.length }} 个全景项目</p>
        </div>
  
        <div v-if="loading" class="loading-state">加载中...</div>
  
        <div v-else-if="projects.length === 0" class="empty-state">
          <div class="empty-icon">📂</div>
          <p>还没有作品，快去上传吧！</p>
          <button class="go-upload-btn" @click="$emit('go-upload')">去上传</button>
        </div>
  
        <div v-else class="project-grid">
          <div 
            v-for="p in projects" 
            :key="p.id" 
            class="project-card"
            @click="enterProject(p.id)"
          >
            <div class="cover-wrapper">
              <img 
                :src="getCoverImage(p)" 
                loading="lazy" 
                alt="cover"
              />
              <div class="hover-overlay">
                <span class="enter-text">进入全景</span>
              </div>
              <div class="badge">{{ p.category }}</div>
            </div>
            
            <div class="card-info">
              <h3 class="project-name" :title="p.name">{{ p.name }}</h3>
              <div class="meta-info">
                <span>{{ p.scenes.length }} 个场景</span>
                <span>ID: {{ p.id }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </template>
  
  <script setup>
  import { ref, onMounted } from 'vue';
  
  const emit = defineEmits(['select-project', 'go-upload']);
  const projects = ref([]);
  const loading = ref(true);
  
  // 获取后端数据
  const fetchProjects = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/projects/');
      if (res.ok) {
        projects.value = await res.json();
      }
    } catch (err) {
      console.error("获取列表失败", err);
    } finally {
      loading.value = false;
    }
  };
  
  // 获取封面图逻辑
  const getCoverImage = (project) => {
    if (project.scenes && project.scenes.length > 0) {
      // 后端返回的 image_url 已经是 /static/... 格式
      // 记得加上后端域名
      return `http://127.0.0.1:8000${project.scenes[0].image_url}`;
    }
    return 'https://via.placeholder.com/300x200?text=No+Image'; // 占位图
  };
  
  const enterProject = (id) => {
    emit('select-project', id);
  };
  
  onMounted(() => {
    fetchProjects();
  });
  </script>
  
  <style scoped>
  .list-wrapper {
    min-height: 100vh;
    background-color: #f5f7fa;
    padding: 40px 20px;
    font-family: 'PingFang SC', sans-serif;
  }
  
  .content-container {
    max-width: 1200px;
    margin: 0 auto;
  }
  
  .header {
    margin-bottom: 30px;
    display: flex;
    justify-content: space-between;
    align-items: baseline;
  }
  .header h2 { font-size: 28px; color: #2c3e50; margin: 0; }
  .header p { color: #7f8c8d; margin: 0; }
  
  /* Grid */
  .project-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 24px;
  }
  
  /* Card */
  .project-card {
    background: white;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    cursor: pointer;
    transition: transform 0.3s, box-shadow 0.3s;
    display: flex;
    flex-direction: column;
  }
  
  .project-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 10px 20px rgba(0,0,0,0.1);
  }
  
  .cover-wrapper {
    height: 180px;
    background: #eee;
    position: relative;
    overflow: hidden;
  }
  
  .cover-wrapper img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: transform 0.5s;
  }
  
  .project-card:hover .cover-wrapper img {
    transform: scale(1.05);
  }
  
  .hover-overlay {
    position: absolute; top:0; left:0; width:100%; height:100%;
    background: rgba(0,0,0,0.3);
    display: flex; justify-content: center; align-items: center;
    opacity: 0; transition: opacity 0.3s;
  }
  .project-card:hover .hover-overlay { opacity: 1; }
  
  .enter-text {
    color: white; border: 1px solid white; padding: 6px 16px; border-radius: 20px; font-size: 14px;
  }
  
  .badge {
    position: absolute; top: 10px; right: 10px;
    background: rgba(0,0,0,0.6); color: white;
    padding: 4px 8px; border-radius: 4px; font-size: 12px;
  }
  
  .card-info {
    padding: 16px;
  }
  
  .project-name {
    margin: 0 0 8px; font-size: 16px; color: #333;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  
  .meta-info {
    display: flex; justify-content: space-between; color: #999; font-size: 12px;
  }
  
  /* Empty State */
  .empty-state {
    text-align: center; padding: 60px; color: #999;
  }
  .empty-icon { font-size: 48px; margin-bottom: 20px; }
  .go-upload-btn {
    margin-top: 15px; padding: 10px 25px; background: #3498db; color: white;
    border: none; border-radius: 6px; cursor: pointer;
  }
  </style>