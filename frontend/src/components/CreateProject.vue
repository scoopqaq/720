<template>
    <div class="create-wrapper">
      <transition name="toast-fade">
        <div v-if="toast.visible" class="toast-message" :class="toast.type">
          <span class="toast-icon">
            <span v-if="toast.type === 'success'">✔</span>
            <span v-else-if="toast.type === 'error'">✖</span>
            <span v-else>!</span>
          </span>
          {{ toast.msg }}
        </div>
      </transition>
  
      <div class="card-container">
        <div class="header-section">
          <h2>创建新项目</h2>
          <p class="subtitle">上传全景图，快速构建 VR 漫游</p>
        </div>
  
        <div 
          class="form-section upload-section"
          @dragover.prevent="isDragOver = true"
          @dragleave.prevent="isDragOver = false"
          @drop.prevent="handleDrop"
          :class="{ 'global-drag-over': isDragOver }"
        >
          <div class="section-header">
            <label>全景图上传 <span class="highlight">{{ fileList.length }}/10</span></label>
            <span class="tip-text" v-if="fileList.length > 0">已上传 {{ fileList.length }} 张，可继续拖入图片</span>
          </div>
          
          <input 
            type="file" 
            ref="fileInputRef" 
            multiple 
            accept="image/jpeg,image/png,image/jpg" 
            style="display: none"
            @change="handleFileChange"
          />
  
          <div 
            v-if="fileList.length === 0"
            class="upload-box big-drop-zone"
            @click="triggerFileInput"
          >
            <div class="icon-group">
              <svg class="cloud-icon" viewBox="0 0 24 24" width="48" height="48">
                <path fill="currentColor" d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z"/>
              </svg>
            </div>
            <p class="primary-text">点击或拖拽全景图到这里</p>
            <p class="sub-text">支持 JPG/PNG，单张限 20MB</p>
          </div>
  
          <div v-else class="preview-grid">
            <div v-for="(file, index) in fileList" :key="file.name" class="grid-item">
              <div class="img-wrapper">
                <img :src="getPreviewUrl(file)" />
                <div class="overlay">
                  <button class="del-btn" @click.stop="removeFile(index)">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="white"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
                  </button>
                </div>
              </div>
              <div class="file-name" :title="file.name">{{ file.name }}</div>
            </div>
  
            <div 
              v-if="fileList.length < 10" 
              class="grid-item add-more-btn"
              @click="triggerFileInput"
            >
              <span class="plus-sign">+</span>
              <span class="add-text">添加 / 拖拽</span>
            </div>
          </div>
  
          <div v-if="isDragOver" class="drag-overlay">
            <div class="drag-content">
              <svg class="bounce" width="40" height="40" viewBox="0 0 24 24" fill="white"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
              <p>释放鼠标添加图片</p>
            </div>
          </div>
        </div>
  
        <div class="form-section">
          <label>项目名称</label>
          <div class="input-wrapper">
            <input 
              v-model="projectName" 
              type="text" 
              placeholder="例如：万科金域蓝湾样板间" 
              maxlength="50" 
            />
            <span class="char-count">{{ projectName.length }}/50</span>
          </div>
        </div>
  
        <div class="form-section">
          <label>所属分类</label>
          <div class="category-list">
            <span 
              v-for="cat in categories" 
              :key="cat"
              class="chip"
              :class="{ selected: selectedCategory === cat }"
              @click="selectedCategory = cat"
            >
              {{ cat }}
            </span>
          </div>
        </div>
  
        <div class="footer-actions">
          <button class="submit-btn" :disabled="isSubmitting" @click="submitProject">
            <span v-if="isSubmitting" class="spinner"></span>
            {{ isSubmitting ? '正在合成...' : '立即合成项目' }}
          </button>
        </div>
      </div>
    </div>
  </template>
  
  <script setup>
  import { ref, reactive, onBeforeUnmount } from 'vue';
  
  const categories = [
    '家装', '商业空间', '样板房', '公共空间', 
    '室外建筑', '展览展厅', '别墅', '园林景观', 
    '酒店/民宿', '实景拍摄', '餐饮', '景区/风光', '其他'
  ];
  
  const projectName = ref('');
  const selectedCategory = ref('家装');
  const fileList = ref([]);
  const isDragOver = ref(false);
  const fileInputRef = ref(null); // 这个 ref 现在永远指向真实存在的 input 元素
  const isSubmitting = ref(false);
  const previewUrls = new Map();
  
  // --- Toast 逻辑 ---
  const toast = reactive({ visible: false, msg: '', type: 'info' });
  let toastTimer = null;
  const showToast = (msg, type = 'info') => {
    if (toastTimer) clearTimeout(toastTimer);
    toast.msg = msg; toast.type = type; toast.visible = true;
    toastTimer = setTimeout(() => { toast.visible = false; }, 3000);
  };
  
  // 触发文件选择
  const triggerFileInput = () => {
    // 因为 input 移到了 v-if 外面，所以这里永远能获取到 value
    if (fileInputRef.value) {
      fileInputRef.value.click();
    }
  };
  
  const processFiles = (files) => {
    const newFiles = Array.from(files);
    let duplicateNames = [];
    let errorCount = 0;
  
    for (const file of newFiles) {
      if (fileList.value.length >= 10) {
        showToast('最多只能上传 10 张图片', 'warning');
        break;
      }
      if (!['image/jpeg', 'image/jpg', 'image/png'].includes(file.type)) {
        showToast(`文件 ${file.name} 格式不支持`, 'error');
        errorCount++;
        continue;
      }
      if (file.size > 20 * 1024 * 1024) {
        showToast(`文件 ${file.name} 超过 20MB`, 'error');
        errorCount++;
        continue;
      }
      const isExist = fileList.value.some(f => f.name === file.name);
      if (isExist) {
        duplicateNames.push(file.name);
        continue;
      }
      fileList.value.push(file);
    }
  
    if (duplicateNames.length > 0) {
      showToast(`${duplicateNames.length} 张图片已存在，自动忽略`, 'warning');
    } else if (errorCount === 0 && newFiles.length > 0) {
      showToast(`成功添加 ${newFiles.length} 张图片`, 'success');
    }
  };
  
  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      processFiles(e.target.files);
    }
    e.target.value = ''; // 允许重复选择同一文件
  };
  
  const handleDrop = (e) => {
    isDragOver.value = false;
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processFiles(e.dataTransfer.files);
    }
  };
  
  const getPreviewUrl = (file) => {
    if (!previewUrls.has(file)) {
      previewUrls.set(file, URL.createObjectURL(file));
    }
    return previewUrls.get(file);
  };
  
  const removeFile = (index) => {
    const file = fileList.value[index];
    if (previewUrls.has(file)) {
      URL.revokeObjectURL(previewUrls.get(file));
      previewUrls.delete(file);
    }
    fileList.value.splice(index, 1);
  };
  
  const submitProject = async () => {
    if (fileList.value.length === 0) {
      showToast('请至少上传一张全景图', 'error');
      return;
    }
    if (!projectName.value.trim()) {
      showToast('请输入项目名称', 'error');
      return;
    }
  
    isSubmitting.value = true;
  
    try {
      const formData = new FormData();
      formData.append('name', projectName.value);
      formData.append('category', selectedCategory.value);
      fileList.value.forEach(file => {
        formData.append('files', file);
      });
  
      const response = await fetch('http://127.0.0.1:8000/projects/create_full/', {
        method: 'POST',
        body: formData,
      });
  
      if (!response.ok) throw new Error('上传失败');
  
      const data = await response.json();
      showToast(`项目 "${data.name}" 创建成功！`, 'success');
      
      setTimeout(() => {
        fileList.value = [];
        projectName.value = '';
        previewUrls.forEach(url => URL.revokeObjectURL(url));
        previewUrls.clear();
        // 这里可以 emit 事件通知父组件跳转页面
        // emit('created', data.id);
      }, 1500);
      
    } catch (err) {
      console.error(err);
      showToast('网络请求失败，请检查后端服务', 'error');
    } finally {
      isSubmitting.value = false;
    }
  };
  
  onBeforeUnmount(() => {
    previewUrls.forEach(url => URL.revokeObjectURL(url));
  });
  </script>
  
  <style scoped>
  /* 样式与之前保持一致，可直接复用 */
  .create-wrapper {
    min-height: 100vh;
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 40px 20px;
    font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
  }
  
  .card-container {
    background: white;
    width: 100%;
    max-width: 900px;
    border-radius: 16px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.08);
    padding: 40px;
    display: flex;
    flex-direction: column;
    gap: 30px;
    position: relative;
  }
  
  .toast-message {
    position: absolute;
    top: 20px;
    left: 50%;
    transform: translateX(-50%);
    padding: 10px 20px;
    border-radius: 50px;
    font-size: 14px;
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 8px;
    z-index: 100;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    min-width: 200px;
    justify-content: center;
  }
  .toast-message.success { background-color: #f0f9eb; color: #67c23a; border: 1px solid #e1f3d8; }
  .toast-message.error { background-color: #fef0f0; color: #f56c6c; border: 1px solid #fde2e2; }
  .toast-message.warning { background-color: #fdf6ec; color: #e6a23c; border: 1px solid #faecd8; }
  
  .toast-fade-enter-active, .toast-fade-leave-active { transition: all 0.3s ease; }
  .toast-fade-enter-from, .toast-fade-leave-to { opacity: 0; transform: translate(-50%, -20px); }
  
  .header-section { text-align: center; margin-bottom: 10px; }
  .header-section h2 { font-size: 28px; color: #2c3e50; margin: 0 0 8px; }
  .subtitle { color: #7f8c8d; font-size: 14px; margin: 0; }
  
  .form-section label {
    display: flex; justify-content: space-between; align-items: center;
    font-size: 16px; font-weight: 600; color: #2c3e50; margin-bottom: 12px;
  }
  .highlight { color: #3498db; font-size: 14px; }
  .tip-text { font-size: 12px; color: #95a5a6; font-weight: normal; }
  
  .upload-section {
    position: relative;
    transition: all 0.3s;
    border-radius: 12px;
    padding: 5px;
  }
  .global-drag-over { background-color: #ecf0f1; box-shadow: inset 0 0 0 2px #3498db; }
  
  .drag-overlay {
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(52, 152, 219, 0.8);
    border-radius: 12px;
    display: flex; justify-content: center; align-items: center; z-index: 10;
    pointer-events: none;
  }
  .drag-content { color: white; text-align: center; font-weight: bold; }
  .bounce { animation: bounce 1s infinite; }
  @keyframes bounce { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
  
  .upload-box {
    border: 2px dashed #dce4ec; border-radius: 12px; height: 200px;
    display: flex; flex-direction: column; justify-content: center; align-items: center;
    cursor: pointer; background-color: #fafbfc;
  }
  .upload-box:hover { border-color: #3498db; background-color: #f0f8ff; }
  .cloud-icon { color: #bdc3c7; }
  .primary-text { font-size: 16px; color: #34495e; margin: 10px 0 5px; }
  .sub-text { font-size: 12px; color: #95a5a6; }
  
  .preview-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 16px;
  }
  .grid-item {
    aspect-ratio: 1; border-radius: 8px; overflow: hidden; position: relative;
    background: #fff; border: 1px solid #eee; display: flex; flex-direction: column;
  }
  .img-wrapper { flex: 1; position: relative; overflow: hidden; }
  .img-wrapper img { width: 100%; height: 100%; object-fit: cover; }
  .overlay {
    position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    background: rgba(0,0,0,0.3); display: flex; justify-content: flex-end;
    padding: 5px; opacity: 0; transition: opacity 0.2s;
  }
  .grid-item:hover .overlay { opacity: 1; }
  .del-btn {
    background: #e74c3c; border: none; width: 24px; height: 24px;
    border-radius: 4px; cursor: pointer; display: flex; justify-content: center; align-items: center;
  }
  .file-name {
    height: 24px; line-height: 24px; font-size: 12px; color: #555;
    background: #f8f9fa; padding: 0 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-align: center;
  }
  
  .add-more-btn {
    border: 2px dashed #dce4ec; background: #fafbfc; cursor: pointer;
    display: flex; flex-direction: column; justify-content: center; align-items: center;
  }
  .add-more-btn:hover { border-color: #3498db; color: #3498db; }
  .plus-sign { font-size: 32px; color: #bdc3c7; margin-bottom: 5px; }
  .add-more-btn:hover .plus-sign { color: #3498db; }
  .add-text { font-size: 12px; color: #7f8c8d; }
  
  .input-wrapper { position: relative; }
  input[type="text"] {
    width: 100%; padding: 14px 16px; border: 1px solid #dce4ec;
    border-radius: 8px; font-size: 15px; outline: none; transition: border-color 0.3s;
  }
  input[type="text"]:focus { border-color: #3498db; box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.1); }
  .char-count { position: absolute; right: 12px; top: 50%; transform: translateY(-50%); color: #bdc3c7; font-size: 12px; }
  
  .category-list { display: flex; flex-wrap: wrap; gap: 10px; }
  .chip {
    padding: 8px 16px; background: #f0f2f5; color: #555; border-radius: 20px;
    font-size: 13px; cursor: pointer; transition: all 0.2s; border: 1px solid transparent;
  }
  .chip:hover { background: #e1e4e8; }
  .chip.selected { background: #3498db; color: white; box-shadow: 0 4px 10px rgba(52, 152, 219, 0.3); }
  
  .footer-actions { margin-top: 10px; display: flex; justify-content: center; }
  .submit-btn {
    background: #2c3e50; color: white; padding: 14px 60px;
    border: none; border-radius: 8px; font-size: 16px; font-weight: 600;
    cursor: pointer; transition: all 0.3s; display: flex; align-items: center; gap: 10px;
  }
  .submit-btn:hover { background: #34495e; transform: translateY(-1px); box-shadow: 0 5px 15px rgba(44, 62, 80, 0.2); }
  .submit-btn:disabled { background: #95a5a6; cursor: not-allowed; transform: none; }
  .spinner {
    width: 16px; height: 16px; border: 2px solid rgba(255,255,255,0.3);
    border-top-color: white; border-radius: 50%; animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  </style>