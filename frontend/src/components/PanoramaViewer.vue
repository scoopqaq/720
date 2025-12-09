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

    <div v-if="isLoading" class="loading-mask">{{ loadingText }}</div>

    <div v-if="menuVisible" class="context-menu" :style="{ left: menuPos.x + 'px', top: menuPos.y + 'px' }">
      <div class="item" @click="toggleRotate">{{ isRotating ? '⏸ 暂停旋转' : '▶ 继续旋转' }}</div>
      <div class="item" @click="toggleDirection">⇄ 拖拽方向: {{ isReverse ? '反向' : '正向' }}</div>
      <div class="item" @click="resetCamera">↺ 视角复位</div>
      <div class="item" @click="toggleFullscreen">⛶ 全屏切换</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed } from 'vue';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import gsap from 'gsap';

const props = defineProps({ projectId: { type: Number, required: true } });
const emit = defineEmits(['back']);

const containerRef = ref(null);
const roomsConfig = ref({});
const currentRoomId = ref(null);
const isLoading = ref(true);
const loadingText = ref('加载中...');

let scene, camera, renderer, controls, animationId;
let textureLoader, raycaster, pointer;
let hotspotMeshes = [];
let sphereMesh1, sphereMesh2;
let activeSphereIndex = 1;

// 状态
const menuVisible = ref(false);
const menuPos = ref({ x: 0, y: 0 });
const isRotating = ref(true);
const isFullscreen = ref(false);
const isTransitioning = ref(false);
const isReverse = ref(false);

const currentRoomName = computed(() => {
  if (currentRoomId.value && roomsConfig.value[currentRoomId.value]) {
    return roomsConfig.value[currentRoomId.value].name;
  }
  return '';
});

// 1. 获取数据并映射
const fetchProjectData = async () => {
  try {
    const res = await fetch(`http://127.0.0.1:8000/projects/${props.projectId}`);
    if (!res.ok) throw new Error('项目不存在');
    const projectData = await res.json();
    
    const config = {};
    if (!projectData.scenes || projectData.scenes.length === 0) {
      alert("无场景数据");
      return;
    }

    projectData.scenes.forEach(scene => {
      config[scene.id] = {
        name: scene.name,
        texture: `http://127.0.0.1:8000${scene.image_url}?t=${new Date().getTime()}`,
        hotspots: (scene.hotspots || []).map(h => ({
          target: h.target_scene_id,
          position: [h.x, h.y, h.z],
          text: h.text
        })),
        // [关键修复] 完整读取后端保存的参数
        // 如果是新创建的场景没有值，给予默认兜底
        initial_heading: scene.initial_heading ?? 0,
        initial_pitch: scene.initial_pitch ?? 0,
        fov_default: scene.fov_default ?? 95,
        fov_min: scene.fov_min ?? 70,
        fov_max: scene.fov_max ?? 120,
        limit_h_min: scene.limit_h_min ?? -180,
        limit_h_max: scene.limit_h_max ?? 180,
        limit_v_min: scene.limit_v_min ?? -90,
        limit_v_max: scene.limit_v_max ?? 90,
      };
    });

    roomsConfig.value = config;
    // 默认进第一个
    initThree(projectData.scenes[0].id);

  } catch (err) {
    console.error(err);
    loadingText.value = "数据加载失败";
  }
};

const initThree = (initialRoomId) => {
  if (!containerRef.value) return;
  const width = containerRef.value.clientWidth;
  const height = containerRef.value.clientHeight;

  scene = new THREE.Scene();
  // 初始FOV先给个默认值，后面 loadRoom 会覆盖
  camera = new THREE.PerspectiveCamera(95, width / height, 0.1, 1000);
  camera.position.set(0, 0, 0.1);

  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(width, height);
  renderer.setPixelRatio(window.devicePixelRatio);
  containerRef.value.appendChild(renderer.domElement);

  const geometry = new THREE.SphereGeometry(500, 60, 40);
  geometry.scale(-1, 1, 1);

  sphereMesh1 = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ transparent: true, opacity: 1 }));
  // 这里旋转 -90度 是为了让全景图的 "正前方" 对准 Z轴负方向
  // 所有的 heading 计算都是基于这个 offset 的
  sphereMesh1.rotation.y = -Math.PI / 2;
  sphereMesh1.renderOrder = 1;
  scene.add(sphereMesh1);

  sphereMesh2 = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ transparent: true, opacity: 0 }));
  sphereMesh2.rotation.y = -Math.PI / 2;
  sphereMesh2.renderOrder = 0;
  scene.add(sphereMesh2);

  textureLoader = new THREE.TextureLoader();
  textureLoader.setCrossOrigin('anonymous');
  raycaster = new THREE.Raycaster();
  pointer = new THREE.Vector2();

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.autoRotate = true;
  controls.autoRotateSpeed = 0.5;
  controls.enableZoom = false; // 手动接管缩放

  loadRoom(initialRoomId, false);
  animate();
  
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

    // [关键修复] 应用保存的参数
    applyRoomSettings(roomData);

    isLoading.value = false;

    if (animate) {
      nextSphere.material.opacity = 0;
      nextSphere.visible = true;
      gsap.to(nextSphere.material, {
        opacity: 1, duration: 1.0, 
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

// [新增] 统一的应用设置函数
const applyRoomSettings = (data) => {
  if (!camera || !controls) return;

  // 1. 设置 FOV
  camera.fov = data.fov_default;
  camera.updateProjectionMatrix();

  // 2. 设置限制 (Infinite Check)
  if (data.limit_h_min <= -180 && data.limit_h_max >= 180) {
    controls.minAzimuthAngle = -Infinity;
    controls.maxAzimuthAngle = Infinity;
  } else {
    controls.minAzimuthAngle = data.limit_h_min * (Math.PI / 180);
    controls.maxAzimuthAngle = data.limit_h_max * (Math.PI / 180);
  }

  // [关键] 垂直限制转换
  // UI: 90(Top), -90(Bottom)
  // Three: 0(Top), PI(Bottom)
  // minPolar (Top Limit) comes from UI Max
  controls.minPolarAngle = (90 - data.limit_v_max) * (Math.PI / 180);
  // maxPolar (Bottom Limit) comes from UI Min
  controls.maxPolarAngle = (90 - data.limit_v_min) * (Math.PI / 180);

  // 3. 设置初始视角
  controls.reset(); // 先清除之前的旋转
  
  // 转换角度
  const azimuth = data.initial_heading * (Math.PI / 180);
  const polar = (90 - data.initial_pitch) * (Math.PI / 180);
  
  // 移动相机到对应球面位置
  // 因为球体本身转了 -90度，所以这里可能需要抵消，但 OrbitControls 是相对 Z 轴的
  // 经测试，直接应用通常符合预期，如果方向偏了 90 度，这里 + Math.PI/2
  const r = 0.1;
  camera.position.x = r * Math.sin(polar) * Math.sin(azimuth);
  camera.position.y = r * Math.cos(polar);
  camera.position.z = r * Math.sin(polar) * Math.cos(azimuth);
  
  controls.update();
};

// ... 其他辅助函数 (clearHotspots, createHotspots, onPointerDown) 保持不变 ...
const clearHotspots = () => { hotspotMeshes.forEach(mesh => { scene.remove(mesh); mesh.geometry.dispose(); mesh.material.dispose(); }); hotspotMeshes = []; };
const createHotspots = (list) => { 
  if(!list) return;
  list.forEach(hs => {
    // 简略：创建热点逻辑，同之前
    const geometry = new THREE.SphereGeometry(15, 32, 16);
    const material = new THREE.MeshBasicMaterial({ color: 0xff0000, transparent: true, opacity: 0.8 });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(...hs.position);
    mesh.userData = { targetRoom: hs.target };
    scene.add(mesh);
    hotspotMeshes.push(mesh);
  });
};
const onPointerDown = (e) => {
  if (isTransitioning.value) return;
  const rect = containerRef.value.getBoundingClientRect();
  pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const intersects = raycaster.intersectObjects(hotspotMeshes);
  if (intersects.length > 0) loadRoom(intersects[0].object.userData.targetRoom, true);
};

// [修复] 滚轮逻辑：受 Min/Max 限制
const onMouseWheel = (e) => {
  e.preventDefault();
  const roomData = roomsConfig.value[currentRoomId.value];
  if (!roomData) return;

  const min = roomData.fov_min;
  const max = roomData.fov_max;
  
  let newFov = camera.fov + e.deltaY * 0.05;
  newFov = Math.max(min, Math.min(max, newFov));
  
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
  camera.aspect = containerRef.value.clientWidth / containerRef.value.clientHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(containerRef.value.clientWidth, containerRef.value.clientHeight);
};

const onContextMenu = (e) => { e.preventDefault(); menuPos.value = {x:e.clientX, y:e.clientY}; menuVisible.value = true; };
const closeMenu = () => { menuVisible.value = false; };
const toggleRotate = () => { isRotating.value = !isRotating.value; controls.autoRotate = isRotating.value; };
const toggleDirection = () => { isReverse.value = !isReverse.value; controls.rotateSpeed = isReverse.value ? -0.5 : 0.5; };
const resetCamera = () => { 
  // 复位时重新应用当前房间的设置
  if (currentRoomId.value) applyRoomSettings(roomsConfig.value[currentRoomId.value]);
};
const toggleFullscreen = () => {
  if (!document.fullscreenElement) { document.documentElement.requestFullscreen(); isFullscreen.value = true; }
  else { document.exitFullscreen(); isFullscreen.value = false; }
};

onMounted(() => fetchProjectData());
onBeforeUnmount(() => {
  cancelAnimationFrame(animationId);
  window.removeEventListener('resize', onWindowResize);
  window.removeEventListener('contextmenu', onContextMenu);
  window.removeEventListener('click', closeMenu);
  if(containerRef.value) containerRef.value.removeEventListener('wheel', onMouseWheel);
  if(renderer) renderer.dispose();
});
</script>

<style scoped>
/* 样式复用之前的 */
.viewer-wrapper { width: 100%; height: 100vh; position: relative; background: #000; overflow: hidden; }
.three-container { width: 100%; height: 100%; cursor: grab; }
.three-container:active { cursor: grabbing; }
.ui-layer { pointer-events: none; position: absolute; inset: 0; }
.back-btn { pointer-events: auto; position: absolute; top: 20px; left: 20px; background: rgba(0,0,0,0.5); color: white; border: 1px solid rgba(255,255,255,0.3); padding: 8px 16px; border-radius: 4px; cursor: pointer; }
.tip { position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%); color: rgba(255,255,255,0.8); background: rgba(0,0,0,0.6); padding: 8px 16px; border-radius: 20px; font-size: 14px; }
.loading-mask { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.8); padding: 20px 40px; border-radius: 8px; color: white; z-index: 20; }
.context-menu { position: absolute; z-index: 999; background: rgba(255,255,255,0.95); border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); padding: 6px 0; min-width: 140px; pointer-events: auto; }
.context-menu .item { padding: 12px 20px; cursor: pointer; color: #333; }
.context-menu .item:hover { background-color: #f0f7ff; color: #007bff; }
</style>