<template>
  <div class="viewer-wrapper">
    <div 
      ref="containerRef" 
      class="three-container" 
      @dblclick="resetCamera"
      @pointerdown="onPointerDown"
    ></div>

    <div class="tip">
      当前位置: {{ currentRoomId }} | 点击红色热点体验平滑穿梭
    </div>

    <div v-if="isLoading" class="loading-mask">
      加载资源中...
    </div>

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
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
// [新增] 引入 GSAP 动画库
import gsap from 'gsap';

// --- 房间配置 (保持不变，请根据你的图片调整) ---
const roomsConfig = {
  room1: {
    texture: '/room1.jpg',
    hotspots: [
      { target: 'room2', position: [400, 0, 0], text: '去房间2' },
      { target: 'room3', position: [0, 0, 400], text: '去房间3' },
      { target: 'room4', position: [-400, 0, 0], text: '去房间4' }
    ]
  },
  room2: {
    texture: '/room2.jpg',
    hotspots: [
      { target: 'room1', position: [-400, 0, 0], text: '返回房间1' },
      { target: 'room3', position: [400, 0, 200], text: '去房间3' }
    ]
  },
  room3: {
    texture: '/room3.jpg',
    hotspots: [
      { target: 'room1', position: [0, 0, -400], text: '返回房间1' },
      { target: 'room4', position: [300, 100, 300], text: '去房间4' }
    ]
  },
  room4: {
    texture: '/room4.jpg',
    hotspots: [
      { target: 'room1', position: [400, 0, 0], text: '返回房间1' }
    ]
  }
};

const containerRef = ref(null);
const menuVisible = ref(false);
const menuPos = ref({ x: 0, y: 0 });
const isRotating = ref(true);
const isFullscreen = ref(false);
const currentRoomId = ref('room1');
const isLoading = ref(false);
// [新增] 标记是否正在转场动画中，防止重复点击
const isTransitioning = ref(false);

let scene, camera, renderer, controls, animationId;
let textureLoader;
let raycaster = new THREE.Raycaster();
let pointer = new THREE.Vector2();
let hotspotMeshes = [];

// [新增] 双球体系统变量
let sphereMesh1, sphereMesh2;
let activeSphereIndex = 1; // 1 表示 mesh1 活跃，2 表示 mesh2 活跃

const initThree = () => {
  if (!containerRef.value) return;
  const width = containerRef.value.clientWidth;
  const height = containerRef.value.clientHeight;

  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
  camera.position.set(0, 0, 0.1);

  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(width, height);
  renderer.setPixelRatio(window.devicePixelRatio);
  containerRef.value.appendChild(renderer.domElement);

  // --- [关键修改] 创建两个球体 ---
  const geometry = new THREE.SphereGeometry(500, 60, 40);
  geometry.scale(-1, 1, 1);

  // 球体 1 (初始活跃)
  const mat1 = new THREE.MeshBasicMaterial({ map: null, transparent: true, opacity: 1 });
  sphereMesh1 = new THREE.Mesh(geometry, mat1);
  sphereMesh1.rotation.y = -Math.PI / 2; // 调整初始角度
  // renderOrder 控制渲染顺序，防止透明度混合错乱
  sphereMesh1.renderOrder = 1; 
  scene.add(sphereMesh1);

  // 球体 2 (初始隐藏)
  const mat2 = new THREE.MeshBasicMaterial({ map: null, transparent: true, opacity: 0 });
  sphereMesh2 = new THREE.Mesh(geometry, mat2);
  sphereMesh2.rotation.y = -Math.PI / 2;
  sphereMesh2.renderOrder = 0; // 放在后面
  scene.add(sphereMesh2);

  textureLoader = new THREE.TextureLoader();

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.05;
  controls.autoRotate = true;
  controls.autoRotateSpeed = 0.5;
  controls.enableZoom = false;

  // 初始加载，不带动画
  loadRoom(currentRoomId.value, false);

  animate();

  window.addEventListener('resize', onWindowResize);
  window.addEventListener('contextmenu', onContextMenu);
  window.addEventListener('click', closeMenu);
  containerRef.value.addEventListener('wheel', onMouseWheel, { passive: false });
};

// ==========================================
// [重写] 加载房间逻辑 (支持渐变动画)
// ==========================================
const loadRoom = (roomId, animate = true) => {
  if (isTransitioning.value && animate) return; // 防止狂点
  const roomData = roomsConfig[roomId];
  if (!roomData) return;

  isLoading.value = true;
  if (animate) isTransitioning.value = true;

  // 1. 确定我们要操作哪个球体
  // 如果当前是 sphere1 显示，那我们就把新图贴到 sphere2 上，然后淡入 sphere2
  const currentSphere = activeSphereIndex === 1 ? sphereMesh1 : sphereMesh2;
  const nextSphere = activeSphereIndex === 1 ? sphereMesh2 : sphereMesh1;

  // 2. 隐藏旧热点 (立即隐藏，避免看着热点飘在半空)
  clearHotspots();

  // 3. 加载图片
  textureLoader.load(
    roomData.texture,
    (texture) => {
      texture.colorSpace = THREE.SRGBColorSpace;
      
      // 把新图给“下一个球”
      nextSphere.material.map = texture;
      nextSphere.material.needsUpdate = true;
      // 确保它的渲染顺序在最前面，这样淡入时会盖住旧球
      nextSphere.renderOrder = 1;
      currentSphere.renderOrder = 0;

      isLoading.value = false;

      if (animate) {
        // === 动画模式 ===
        
        // 确保新球是透明的，然后显示出来
        nextSphere.material.opacity = 0;
        nextSphere.visible = true;

        // 使用 GSAP 执行交叉渐变
        // 1. 新球淡入 (Opacity 0 -> 1)
        gsap.to(nextSphere.material, {
          opacity: 1,
          duration: 1.0, // 动画时间 1秒
          ease: "power2.inOut",
          onComplete: () => {
            // 动画结束后的清理工作
            currentSphere.visible = false; // 隐藏旧球
            currentSphere.material.opacity = 0; // 重置旧球透明度
            
            // 切换状态索引
            activeSphereIndex = activeSphereIndex === 1 ? 2 : 1;
            
            // 创建新房间的热点
            createHotspots(roomData.hotspots);
            currentRoomId.value = roomId;
            isTransitioning.value = false;
          }
        });

      } else {
        // === 初始加载 (无动画) ===
        nextSphere.material.opacity = 1;
        nextSphere.visible = true;
        currentSphere.visible = false;
        
        activeSphereIndex = activeSphereIndex === 1 ? 2 : 1;
        createHotspots(roomData.hotspots);
        isLoading.value = false;
      }
    },
    undefined,
    (err) => {
      console.error(err);
      isLoading.value = false;
      isTransitioning.value = false;
    }
  );
};

// [修改] 清理热点
const clearHotspots = () => {
  hotspotMeshes.forEach(mesh => {
    // 使用 GSAP 让热点淡出消失（可选优化）
    scene.remove(mesh);
    mesh.geometry.dispose();
    mesh.material.dispose();
  });
  hotspotMeshes = [];
};

// [修改] 批量创建热点
const createHotspots = (hotspotsData) => {
  if (!hotspotsData) return;
  hotspotsData.forEach(hsConfig => {
    const geometry = new THREE.SphereGeometry(15, 32, 16);
    const material = new THREE.MeshBasicMaterial({ 
      color: 0xff0000,
      transparent: true,
      opacity: 0 // 初始透明，为了淡入效果
    });
    const hotspot = new THREE.Mesh(geometry, material);
    hotspot.position.set(...hsConfig.position);
    hotspot.userData = { targetRoom: hsConfig.target, text: hsConfig.text };
    
    scene.add(hotspot);
    hotspotMeshes.push(hotspot);

    // 热点淡入动画
    gsap.to(material, { opacity: 0.8, duration: 0.5, delay: 0.2 });
  });
};

const onPointerDown = (event) => {
  if (isTransitioning.value) return; // 转场时不许点击
  if (!containerRef.value) return;

  const rect = containerRef.value.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

  raycaster.setFromCamera(pointer, camera);
  const intersects = raycaster.intersectObjects(hotspotMeshes);

  if (intersects.length > 0) {
    const targetRoomId = intersects[0].object.userData.targetRoom;
    console.log('Jump to:', targetRoomId);
    loadRoom(targetRoomId, true); // true 表示启用动画
  }
};

const onMouseWheel = (event) => {
  event.preventDefault();
  let newFov = camera.fov + event.deltaY * 0.05;
  newFov = Math.max(30, Math.min(100, newFov));
  camera.fov = newFov;
  camera.updateProjectionMatrix();
};

const animate = () => {
  animationId = requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
};

const onWindowResize = () => {
  if (!containerRef.value) return;
  const width = containerRef.value.clientWidth;
  const height = containerRef.value.clientHeight;
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height);
};

const onContextMenu = (e) => {
  e.preventDefault();
  menuPos.value = { x: e.clientX, y: e.clientY };
  menuVisible.value = true;
};

const closeMenu = () => {
  menuVisible.value = false;
};

const toggleRotate = () => {
  isRotating.value = !isRotating.value;
  controls.autoRotate = isRotating.value;
};

const resetCamera = () => {
  controls.reset();
  camera.fov = 75;
  camera.updateProjectionMatrix();
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
  if (renderer) renderer.dispose();
  // 清理 GSAP 动画 (如果有正在运行的)
  gsap.globalTimeline.clear();
});
</script>

<style scoped>
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
  cursor: grab;
}
.three-container:active {
  cursor: grabbing;
}
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
  z-index: 10;
}
.loading-mask {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(0,0,0,0.8);
  padding: 20px 40px;
  border-radius: 8px;
  color: white;
  pointer-events: none;
  z-index: 20;
}
.context-menu {
  position: absolute;
  z-index: 999;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
  padding: 6px 0;
  min-width: 140px;
  user-select: none;
}
.context-menu .item {
  padding: 12px 20px;
  cursor: pointer;
  font-size: 14px;
  color: #333;
  transition: all 0.2s;
}
.context-menu .item:hover {
  background-color: #f0f7ff;
  color: #007bff;
}
</style>