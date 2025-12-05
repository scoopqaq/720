<template>
  <div class="viewer-wrapper">
    <div 
      ref="containerRef" 
      class="three-container" 
      @dblclick="resetCamera"
      @pointerdown="onPointerDown"
    ></div>

    <div class="tip">
      当前位置: {{ currentRoomId }} | 鼠标左键拖拽 · 滚轮缩放 · 点击红色热点跳转
    </div>

    <div v-if="isLoading" class="loading-mask">
      场景切换中...
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
import { ref, onMounted, onBeforeUnmount, reactive } from 'vue';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

// ==========================================
// [新增] 1. 房间配置数据
// 定义每个房间的图片路径和通往其他房间的热点位置
// 位置坐标 (x, y, z) 大概在 300-450 之间比较合适，因为球半径是 500
// ==========================================
const roomsConfig = {
  room1: {
    texture: '/room1.jpg',
    // room1 可以去 2, 3, 4
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

// --- 响应式数据 ---
const containerRef = ref(null);
const menuVisible = ref(false);
const menuPos = ref({ x: 0, y: 0 });
const isRotating = ref(true);
const isFullscreen = ref(false);
// [新增] 当前房间 ID
const currentRoomId = ref('room1');
// [新增] 加载状态
const isLoading = ref(false);

// --- Three.js 变量 ---
let scene, camera, renderer, controls, animationId;
let sphereMesh; // [修改] 全景球体 Mesh 需要提取出来，方便后续换图
let textureLoader;
// [新增] 存放所有热点 Mesh 的数组，用于射线检测和清理
let hotspotMeshes = []; 
// [新增] 射线检测器和鼠标向量
const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();


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

  // 创建全景球体几何体
  const geometry = new THREE.SphereGeometry(500, 60, 40);
  geometry.scale(-1, 1, 1);

  // 初始化纹理加载器
  textureLoader = new THREE.TextureLoader();
  
  // 创建基础材质（初始为空贴图，稍后在 loadRoom 中加载）
  const material = new THREE.MeshBasicMaterial({ map: null });
  sphereMesh = new THREE.Mesh(geometry, material);
  scene.add(sphereMesh);

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.05;
  controls.autoRotate = true;
  controls.autoRotateSpeed = 0.5; // 转慢点方便点热点
  controls.enableZoom = false;

  // [新增] 初始加载第一个房间
  loadRoom(currentRoomId.value);

  animate();

  window.addEventListener('resize', onWindowResize);
  window.addEventListener('contextmenu', onContextMenu);
  window.addEventListener('click', closeMenu);
  containerRef.value.addEventListener('wheel', onMouseWheel, { passive: false });
};

// ==========================================
// [新增] 2. 加载房间的核心函数
// 负责：清理旧热点 -> 加载新图片 -> 替换材质 -> 创建新热点
// ==========================================
const loadRoom = (roomId) => {
  const roomData = roomsConfig[roomId];
  if (!roomData) return;

  isLoading.value = true; // 显示加载提示

  // 2.1 清理当前场景中旧的热点
  hotspotMeshes.forEach(mesh => {
    scene.remove(mesh);
    mesh.geometry.dispose(); // 释放内存
    mesh.material.dispose();
  });
  hotspotMeshes = []; // 清空数组

  // 2.2 加载新房间的图片纹理
  textureLoader.load(
    roomData.texture,
    // onLoad 回调：图片加载完成时触发
    (loadedTexture) => {
      loadedTexture.colorSpace = THREE.SRGBColorSpace;
      
      // 替换全景球的贴图
      sphereMesh.material.map = loadedTexture;
      // 告诉 Three.js 材质需要更新
      sphereMesh.material.needsUpdate = true;

      // 2.3 创建新房间的热点
      if (roomData.hotspots) {
        roomData.hotspots.forEach(hsConfig => {
          createHotspot(hsConfig);
        });
      }

      // 更新当前状态
      currentRoomId.value = roomId;
      isLoading.value = false; // 隐藏加载提示
    },
    undefined, // onProgress
    // onError 回调
    (err) => {
      console.error('图片加载失败:', err);
      isLoading.value = false;
      alert(`加载 ${roomId} 失败，请检查图片路径`);
    }
  );
};

// ==========================================
// [新增] 3. 创建单个热点的辅助函数
// ==========================================
const createHotspot = (hsConfig) => {
  // 这里用一个简单的红色球体作为热点
  // 你以后可以换成 Sprite (精灵图) 或者更复杂的模型
  const geometry = new THREE.SphereGeometry(15, 32, 16);
  // 设置为红色半透明，且不受光照影响
  const material = new THREE.MeshBasicMaterial({ 
    color: 0xff0000,
    transparent: true,
    opacity: 0.8
  });
  const hotspotMesh = new THREE.Mesh(geometry, material);
  
  // 设置位置 (解构数组)
  hotspotMesh.position.set(...hsConfig.position);

  // [关键] 将目标房间信息绑定到 mesh 的 userData 属性上
  // 这样在点击检测时，我们就能知道这个 mesh 指向哪里
  hotspotMesh.userData = { targetRoom: hsConfig.target, text: hsConfig.text };

  scene.add(hotspotMesh);
  // 加入到数组中，方便统一管理和检测
  hotspotMeshes.push(hotspotMesh);
};

// ==========================================
// [新增] 4. 点击交互检测 (射线拾取)
// ==========================================
const onPointerDown = (event) => {
  if (!containerRef.value) return;

  // 1. 将鼠标位置归一化为设备坐标 (NDC)，范围是 -1 到 +1
  const rect = containerRef.value.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

  // 2. 通过摄像机和鼠标位置更新射线
  raycaster.setFromCamera(pointer, camera);

  // 3. 计算物体和射线的交点 (只检测热点数组数组)
  const intersects = raycaster.intersectObjects(hotspotMeshes);

  if (intersects.length > 0) {
    // 取第一个交点（最近的那个）
    const targetObject = intersects[0].object;
    const targetRoomId = targetObject.userData.targetRoom;
    
    console.log('点击了热点，前往:', targetRoomId);
    
    // 执行切换房间
    loadRoom(targetRoomId);
  }
};

// --- 其他原有函数 (保持不变) ---
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
  if (renderer) {
    renderer.dispose();
  }
  // [新增] 清理热点内存
  hotspotMeshes.forEach(mesh => {
    mesh.geometry.dispose();
    mesh.material.dispose();
  });
});
</script>

<style scoped>
/* ...原有的样式... */
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
  /* 设置鼠标样式，提示可以点击 */
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
  white-space: nowrap;
  z-index: 10;
}

/* [新增] 加载遮罩层样式 */
.loading-mask {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0,0,0,0.7);
  color: white;
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 24px;
  z-index: 20;
}

/* ...原有的右键菜单样式... */
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