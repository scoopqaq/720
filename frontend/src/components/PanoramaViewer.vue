<template>
    <div class="viewer-wrapper">
      <div 
        ref="containerRef" 
        class="three-container" 
        @dblclick="resetCamera"
      ></div>
  
      <div class="tip">鼠标左键拖拽 · 滚轮缩放 · 右键打开菜单 · 双击复位</div>
  
      <div 
        v-if="menuVisible" 
        class="context-menu" 
        :style="{ left: menuPos.x + 'px', top: menuPos.y + 'px' }"
      >
        <div class="item" @click="toggleRotate">
          {{ isRotating ? '⏸ 暂停旋转' : '▶ 继续旋转' }}
        </div>
        <div class="item" @click="resetCamera">↺ 视角复位</div>
        <div class="item" @click="toggleFullscreen">
          {{ isFullscreen ? '⛶ 退出全屏' : '⛶ 全屏模式' }}
        </div>
      </div>
    </div>
  </template>
  
  <script setup>
  import { ref, onMounted, onBeforeUnmount } from 'vue';
  import * as THREE from 'three';
  // 确保你已经运行 npm install three
  import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
  
  // --- 响应式数据 ---
  const containerRef = ref(null);
  const menuVisible = ref(false);
  const menuPos = ref({ x: 0, y: 0 });
  const isRotating = ref(true);
  const isFullscreen = ref(false);
  
  // --- Three.js 对象 (不放进 ref，避免性能问题) ---
  let scene, camera, renderer, controls, animationId;
  
  // --- 初始化逻辑 ---
  const initThree = () => {
    if (!containerRef.value) return;
  
    const width = containerRef.value.clientWidth;
    const height = containerRef.value.clientHeight;
  
    // 1. 场景
    scene = new THREE.Scene();
  
    // 2. 相机 (FOV 默认 75)
    camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
    camera.position.set(0, 0, 0.1); // 位于球心
  
    // 3. 渲染器
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(window.devicePixelRatio); // 优化清晰度
    containerRef.value.appendChild(renderer.domElement);
  
    // 4. 创建球体
    const geometry = new THREE.SphereGeometry(500, 60, 40);
    geometry.scale(-1, 1, 1); // 翻转，让贴图在内部显示
  
    // 5. 加载纹理
    const textureLoader = new THREE.TextureLoader();
    const texture = textureLoader.load('/room.jpg'); // 确保 public 目录下有 room.jpg
    // 颜色空间校正（让图片颜色更鲜艳还原）
    texture.colorSpace = THREE.SRGBColorSpace; 
    
    const material = new THREE.MeshBasicMaterial({ map: texture });
    const sphere = new THREE.Mesh(geometry, material);
    
    // [修正] 旋转球体，调整初始视角 (负数向右转，正数向左转)
    sphere.rotation.y = -Math.PI / 2; 
  
    scene.add(sphere);
  
    // 6. 控制器
    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true; // 开启阻尼惯性
    controls.dampingFactor = 0.05;
    controls.autoRotate = true;    // 开启自动旋转
    controls.autoRotateSpeed = 1.0;
    
    // [重点] 禁用 OrbitControls 自带的“移动相机”式缩放
    controls.enableZoom = false; 
  
    // 7. 开始动画
    animate();
  
    // 8. 绑定事件
    window.addEventListener('resize', onWindowResize);
    window.addEventListener('contextmenu', onContextMenu);
    window.addEventListener('click', closeMenu);
    
    // [重点] 手动绑定滚轮事件来实现 FOV 缩放
    containerRef.value.addEventListener('wheel', onMouseWheel, { passive: false });
  };
  
  // --- 滚轮缩放逻辑 (FOV 变焦) ---
  const onMouseWheel = (event) => {
    event.preventDefault(); // 阻止页面滚动
  
    // 计算新的 FOV
    // deltaY > 0 向下滚(缩小)，FOV变大
    // deltaY < 0 向上滚(放大)，FOV变小
    let newFov = camera.fov + event.deltaY * 0.05;
  
    // 限制缩放范围 (30度特写 ~ 100度广角)
    newFov = Math.max(30, Math.min(100, newFov));
  
    camera.fov = newFov;
    camera.updateProjectionMatrix(); // 必须调用，否则画面不更新
  };
  
  // --- 动画循环 ---
  const animate = () => {
    animationId = requestAnimationFrame(animate);
    controls.update(); // 必须调用
    renderer.render(scene, camera);
  };
  
  // --- 窗口自适应 ---
  const onWindowResize = () => {
    if (!containerRef.value) return;
    const width = containerRef.value.clientWidth;
    const height = containerRef.value.clientHeight;
    
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
  };
  
  // --- 右键菜单 ---
  const onContextMenu = (e) => {
    e.preventDefault();
    menuPos.value = { x: e.clientX, y: e.clientY };
    menuVisible.value = true;
  };
  
  const closeMenu = () => {
    menuVisible.value = false;
  };
  
  // --- 菜单功能 ---
  const toggleRotate = () => {
    isRotating.value = !isRotating.value;
    controls.autoRotate = isRotating.value;
  };
  
  const resetCamera = () => {
    controls.reset();
    // 复位时把 FOV 也还原
    camera.fov = 75; 
    camera.updateProjectionMatrix();
    // 恢复之前的旋转状态
    controls.autoRotate = isRotating.value;
  };
  
  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      isFullscreen.value = true;
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
        isFullscreen.value = false;
      }
    }
  };
  
  // --- 生命周期 ---
  onMounted(() => {
    initThree();
  });
  
  onBeforeUnmount(() => {
    cancelAnimationFrame(animationId);
    window.removeEventListener('resize', onWindowResize);
    window.removeEventListener('contextmenu', onContextMenu);
    window.removeEventListener('click', closeMenu);
    
    if (containerRef.value) {
      containerRef.value.removeEventListener('wheel', onMouseWheel);
    }
    
    if (renderer) {
      renderer.dispose();
    }
  });
  </script>
  
  <style scoped>
  /* 容器占满父级 */
  .viewer-wrapper {
    position: relative;
    width: 100%;
    height: 100%;
    overflow: hidden;
    background-color: #000;
  }
  
  .three-container {
    width: 100%;
    height: 100%;
    display: block;
  }
  
  /* 提示文字 */
  .tip {
    position: absolute;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    color: rgba(255, 255, 255, 0.8);
    background: rgba(0, 0, 0, 0.6);
    padding: 8px 16px;
    border-radius: 20px;
    font-size: 14px;
    pointer-events: none;
    user-select: none;
    white-space: nowrap;
  }
  
  /* 右键菜单 */
  .context-menu {
    position: absolute;
    z-index: 999;
    background: rgba(255, 255, 255, 0.95);
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    padding: 6px 0;
    min-width: 140px;
    user-select: none;
    backdrop-filter: blur(5px);
  }
  
  .context-menu .item {
    padding: 12px 20px;
    cursor: pointer;
    font-size: 14px;
    color: #333;
    transition: all 0.2s;
    display: flex;
    align-items: center;
  }
  
  .context-menu .item:hover {
    background-color: #f0f7ff;
    color: #007bff;
  }
  </style>