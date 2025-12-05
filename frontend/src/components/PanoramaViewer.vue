<template>
  <div class="viewer-wrapper">
    <div 
      ref="containerRef" 
      class="three-container" 
      @dblclick="resetCamera"
      @pointerdown="onPointerDown"
    ></div>

    <div class="ui-layer">
      <button class="back-btn" @click="$emit('back')">← 返回列表</button>
      <div class="tip" v-if="currentRoomId">当前位置: {{ currentRoomName }}</div>
    </div>

    <div v-if="isLoading" class="loading-mask">
      {{ loadingText }}
    </div>

    <div v-if="menuVisible" class="context-menu" :style="{ left: menuPos.x + 'px', top: menuPos.y + 'px' }">
      <div class="item" @click="toggleRotate">{{ isRotating ? '⏸ 暂停旋转' : '▶ 继续旋转' }}</div>
      <div class="item" @click="resetCamera">↺ 视角复位</div>
      <div class="item" @click="toggleFullscreen">{{ isFullscreen ? '⛶ 退出全屏' : '⛶ 全屏模式' }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed } from 'vue';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import gsap from 'gsap';

// 接收外部传入的项目ID
const props = defineProps({
  projectId: {
    type: Number,
    required: true
  }
});

const emit = defineEmits(['back']);

// --- 数据状态 ---
const containerRef = ref(null);
const roomsConfig = ref({}); // 存放转换后的场景数据
const currentRoomId = ref(null); // 当前房间ID (数据库ID)
const isLoading = ref(true);
const loadingText = ref('正在读取项目数据...');

// --- Three.js 变量 ---
let scene, camera, renderer, controls, animationId;
let textureLoader, raycaster, pointer;
let hotspotMeshes = [];
let sphereMesh1, sphereMesh2;
let activeSphereIndex = 1;

// --- 菜单状态 ---
const menuVisible = ref(false);
const menuPos = ref({ x: 0, y: 0 });
const isRotating = ref(true);
const isFullscreen = ref(false);
const isTransitioning = ref(false);

const currentRoomName = computed(() => {
  if (currentRoomId.value && roomsConfig.value[currentRoomId.value]) {
    return roomsConfig.value[currentRoomId.value].name;
  }
  return '';
});

// =========================================
// 1. 初始化：从后端获取数据
// =========================================
const fetchProjectData = async () => {
  try {
    const res = await fetch(`http://127.0.0.1:8000/projects/${props.projectId}`);
    if (!res.ok) throw new Error('项目不存在');
    const projectData = await res.json();
    
    // [关键] 数据格式转换
    // 后端格式: scenes: [{id, name, image_url, hotspots: [...]}]
    // 前端需要: { [id]: { texture, hotspots: [...] } }
    
    const config = {};
    if (!projectData.scenes || projectData.scenes.length === 0) {
      alert("该项目没有场景！");
      return;
    }

    projectData.scenes.forEach(scene => {
      config[scene.id] = {
        name: scene.name,
        texture: `http://127.0.0.1:8000${scene.image_url}`,
        // [修改] 加一个 || [] 的判断
        // 意思是：如果 scene.hotspots 是 undefined，就用空数组 [] 代替，防止报错
        hotspots: (scene.hotspots || []).map(h => ({
          target: h.target_scene_id,
          position: [h.x, h.y, h.z],
          text: h.text
        }))
      };
    });

    roomsConfig.value = config;
    
    // 初始化 Three.js
    initThree(projectData.scenes[0].id); // 默认进入第一个场景

  } catch (err) {
    console.error(err);
    loadingText.value = "加载失败";
  }
};

// =========================================
// 2. Three.js 核心逻辑
// =========================================
const initThree = (initialRoomId) => {
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

  // 双球体设置
  const geometry = new THREE.SphereGeometry(500, 60, 40);
  geometry.scale(-1, 1, 1);

  sphereMesh1 = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ transparent: true, opacity: 1 }));
  sphereMesh1.rotation.y = -Math.PI / 2;
  sphereMesh1.renderOrder = 1;
  scene.add(sphereMesh1);

  sphereMesh2 = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ transparent: true, opacity: 0 }));
  sphereMesh2.rotation.y = -Math.PI / 2;
  sphereMesh2.renderOrder = 0;
  scene.add(sphereMesh2);

  textureLoader = new THREE.TextureLoader();
  raycaster = new THREE.Raycaster();
  pointer = new THREE.Vector2();

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.autoRotate = true;
  controls.autoRotateSpeed = 0.5;
  controls.enableZoom = false;

  // 加载初始房间
  loadRoom(initialRoomId, false);

  animate();
  
  // 事件绑定
  window.addEventListener('resize', onWindowResize);
  window.addEventListener('contextmenu', onContextMenu);
  window.addEventListener('click', closeMenu);
  containerRef.value.addEventListener('wheel', onMouseWheel, { passive: false });
};

const loadRoom = (roomId, animate = true) => {
  if (isTransitioning.value && animate) return;
  const roomData = roomsConfig.value[roomId];
  if (!roomData) return;

  isLoading.value = true;
  loadingText.value = "场景切换中...";
  if (animate) isTransitioning.value = true;

  const currentSphere = activeSphereIndex === 1 ? sphereMesh1 : sphereMesh2;
  const nextSphere = activeSphereIndex === 1 ? sphereMesh2 : sphereMesh1;

  clearHotspots();

  textureLoader.load(roomData.texture, (texture) => {
    texture.colorSpace = THREE.SRGBColorSpace;
    nextSphere.material.map = texture;
    nextSphere.material.needsUpdate = true;
    nextSphere.renderOrder = 1;
    currentSphere.renderOrder = 0;

    isLoading.value = false;

    if (animate) {
      nextSphere.material.opacity = 0;
      nextSphere.visible = true;
      
      gsap.to(nextSphere.material, {
        opacity: 1, duration: 1.0, ease: "power2.inOut",
        onComplete: () => {
          currentSphere.visible = false;
          currentSphere.material.opacity = 0;
          activeSphereIndex = activeSphereIndex === 1 ? 2 : 1;
          createHotspots(roomData.hotspots);
          currentRoomId.value = roomId;
          isTransitioning.value = false;
        }
      });
    } else {
      nextSphere.material.opacity = 1;
      nextSphere.visible = true;
      currentSphere.visible = false;
      activeSphereIndex = activeSphereIndex === 1 ? 2 : 1;
      createHotspots(roomData.hotspots);
      currentRoomId.value = roomId;
      isLoading.value = false;
    }
  });
};

const clearHotspots = () => {
  hotspotMeshes.forEach(mesh => {
    scene.remove(mesh);
    mesh.geometry.dispose();
    mesh.material.dispose();
  });
  hotspotMeshes = [];
};

const createHotspots = (hotspotsData) => {
  if (!hotspotsData) return;
  hotspotsData.forEach(hs => {
    // 检查目标房间是否存在
    if (!roomsConfig.value[hs.target]) return; 

    const geometry = new THREE.SphereGeometry(15, 32, 16);
    const material = new THREE.MeshBasicMaterial({ color: 0xff0000, transparent: true, opacity: 0 });
    const hotspot = new THREE.Mesh(geometry, material);
    hotspot.position.set(...hs.position);
    hotspot.userData = { targetRoom: hs.target, text: hs.text };
    scene.add(hotspot);
    hotspotMeshes.push(hotspot);
    gsap.to(material, { opacity: 0.8, duration: 0.5, delay: 0.5 });
  });
};

const onPointerDown = (event) => {
  if (isTransitioning.value || !containerRef.value) return;
  const rect = containerRef.value.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const intersects = raycaster.intersectObjects(hotspotMeshes);
  if (intersects.length > 0) {
    loadRoom(intersects[0].object.userData.targetRoom, true);
  }
};

const onMouseWheel = (e) => {
  e.preventDefault();
  camera.fov = Math.max(30, Math.min(100, camera.fov + e.deltaY * 0.05));
  camera.updateProjectionMatrix();
};

const animate = () => {
  animationId = requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
};

const onWindowResize = () => {
  if (!containerRef.value) return;
  camera.aspect = containerRef.value.clientWidth / containerRef.value.clientHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(containerRef.value.clientWidth, containerRef.value.clientHeight);
};

// ... 菜单逻辑保持不变 ...
const onContextMenu = (e) => { e.preventDefault(); menuPos.value = {x:e.clientX, y:e.clientY}; menuVisible.value = true; };
const closeMenu = () => { menuVisible.value = false; };
const toggleRotate = () => { isRotating.value = !isRotating.value; controls.autoRotate = isRotating.value; };
const resetCamera = () => { controls.reset(); camera.fov=75; camera.updateProjectionMatrix(); controls.autoRotate = isRotating.value; };
const toggleFullscreen = () => {
  if (!document.fullscreenElement) { document.documentElement.requestFullscreen(); isFullscreen.value = true; }
  else { document.exitFullscreen(); isFullscreen.value = false; }
};

onMounted(() => {
  fetchProjectData();
});

onBeforeUnmount(() => {
  cancelAnimationFrame(animationId);
  window.removeEventListener('resize', onWindowResize);
  window.removeEventListener('contextmenu', onContextMenu);
  window.removeEventListener('click', closeMenu);
  if (containerRef.value) containerRef.value.removeEventListener('wheel', onMouseWheel);
  if (renderer) renderer.dispose();
  gsap.globalTimeline.clear();
});
</script>

<style scoped>
/* 样式基本复用之前的，加一个返回按钮样式 */
.viewer-wrapper { width: 100%; height: 100vh; position: relative; background: #000; overflow: hidden; }
.three-container { width: 100%; height: 100%; cursor: grab; }
.three-container:active { cursor: grabbing; }

.ui-layer { pointer-events: none; position: absolute; top: 0; left: 0; width: 100%; height: 100%; }
.back-btn {
  pointer-events: auto; position: absolute; top: 20px; left: 20px;
  background: rgba(0,0,0,0.5); color: white; border: 1px solid rgba(255,255,255,0.3);
  padding: 8px 16px; border-radius: 4px; cursor: pointer; transition: background 0.2s;
}
.back-btn:hover { background: rgba(0,0,0,0.8); }

.tip { position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%); color: rgba(255,255,255,0.8); background: rgba(0,0,0,0.6); padding: 8px 16px; border-radius: 20px; font-size: 14px; }
.loading-mask { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.8); padding: 20px 40px; border-radius: 8px; color: white; z-index: 20; }
.context-menu { position: absolute; z-index: 999; background: rgba(255,255,255,0.95); border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); padding: 6px 0; min-width: 140px; user-select: none; pointer-events: auto; }
.context-menu .item { padding: 12px 20px; cursor: pointer; font-size: 14px; color: #333; }
.context-menu .item:hover { background-color: #f0f7ff; color: #007bff; }
</style>