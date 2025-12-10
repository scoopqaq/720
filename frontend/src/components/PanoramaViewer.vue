<template>
  <div class="viewer-wrapper">
    <div 
      ref="containerRef" 
      class="three-container" 
      @dblclick="resetCamera"
      @pointerdown="onPointerDown"
    ></div>

    <div class="ui-layer">
      <div class="top-bar">
        <button class="back-btn" @click="$emit('back')">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="white"><path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/></svg>
        </button>
        <div class="project-title" v-if="projectInfo">{{ projectInfo.name }}</div>
      </div>

      <div class="bottom-controls">
        <div class="scene-toggle-btn" @click="showSceneBar = !showSceneBar" :class="{ active: showSceneBar }">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M3 13h2v-2H3v2zm0 4h2v-2H3v2zm0-8h2V7H3v2zm4 4h14v-2H7v2zm0 4h14v-2H7v2zM7 7v2h14V7H7z"/></svg>
          <span>场景选择</span>
        </div>
      </div>

      <transition name="slide-up">
        <div v-if="showSceneBar" class="scene-bar-overlay">
          <div class="scene-bar-scroll">
            <div 
              v-for="scene in flatScenes" 
              :key="scene.id" 
              class="scene-thumb"
              :class="{ active: currentRoomId === scene.id }"
              @click="switchScene(scene.id)"
            >
              <div class="thumb-img-box">
                <img :src="getThumb(scene)" loading="lazy" />
                <div class="scene-name-tag">{{ scene.name }}</div>
              </div>
            </div>
          </div>
        </div>
      </transition>

      <transition name="fade">
        <div class="tip-toast" v-if="tipVisible">{{ tipMessage }}</div>
      </transition>
    </div>

    <div v-if="isLoading" class="loading-mask">
      <div class="spinner"></div>
      <p>场景加载中...</p>
    </div>

    <div v-if="menuVisible" class="context-menu" :style="{ left: menuPos.x + 'px', top: menuPos.y + 'px' }">
      <div class="item" @click="toggleRotate">{{ isRotating ? '⏸ 暂停旋转' : '▶ 继续旋转' }}</div>
      <div class="item" @click="toggleDirection">⇄ 拖拽方向: {{ isReverse ? '反向' : '正向' }}</div>
      <div class="item" @click="resetCamera">↺ 视角复位</div>
      <div class="item" @click="toggleFullscreen">⛶ 全屏切换</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed, watch } from 'vue';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import gsap from 'gsap';

const props = defineProps({ projectId: { type: Number, required: true } });
const emit = defineEmits(['back']);

const containerRef = ref(null);
const roomsConfig = ref({});
const currentRoomId = ref(null);
const isLoading = ref(true);
const showSceneBar = ref(false); // 控制底部栏显示
const projectInfo = ref(null);
const flatScenes = ref([]); // 扁平化的场景列表，用于底部栏显示

// 提示相关
const tipVisible = ref(false);
const tipMessage = ref('');
const showTip = (msg) => {
  tipMessage.value = msg;
  tipVisible.value = true;
  setTimeout(() => tipVisible.value = false, 2000);
};

// Three.js 变量
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

// 1. 获取并处理数据
const fetchProjectData = async () => {
  try {
    const res = await fetch(`http://127.0.0.1:8000/projects/${props.projectId}`);
    if (!res.ok) throw new Error('项目不存在');
    const data = await res.json();
    projectInfo.value = data;

    const config = {};
    const sceneList = [];

    if (!data.groups || data.groups.length === 0) {
      alert("该项目没有任何场景");
      return;
    }

    // 遍历所有分组和场景
    data.groups.forEach(group => {
      if (group.scenes) {
        group.scenes.forEach(scene => {
          sceneList.push(scene); // 加入列表给底部栏用
          
          config[scene.id] = {
            name: scene.name,
            texture: `http://127.0.0.1:8000${scene.image_url}?t=${new Date().getTime()}`,
            cover: scene.cover_url ? `http://127.0.0.1:8000${scene.cover_url}` : `http://127.0.0.1:8000${scene.image_url}`,
            hotspots: (scene.hotspots || []).map(h => ({
              target: h.target_scene_id,
              position: [h.x, h.y, h.z],
              text: h.text
            })),
            // 读取编辑器保存的设置
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
      }
    });

    flatScenes.value = sceneList;
    roomsConfig.value = config;

    if (sceneList.length > 0) {
      initThree(sceneList[0].id);
    }

  } catch (err) {
    console.error(err);
    alert("数据加载失败");
  }
};

const getThumb = (scene) => {
  if (scene.cover_url) return `http://127.0.0.1:8000${scene.cover_url}?t=s`;
  return `http://127.0.0.1:8000${scene.image_url}?t=s`;
};

// 2. 初始化 Three.js
const initThree = (initialRoomId) => {
  if (!containerRef.value) return;
  const width = containerRef.value.clientWidth;
  const height = containerRef.value.clientHeight;

  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(95, width / height, 0.1, 1000);
  camera.position.set(0, 0, 0.1);

  renderer = new THREE.WebGLRenderer({ antialias: false });
  renderer.setSize(width, height);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  containerRef.value.appendChild(renderer.domElement);

  const geometry = new THREE.SphereGeometry(500, 60, 40);
  geometry.scale(-1, 1, 1);

  // 双球体交替加载
  sphereMesh1 = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ transparent: true, opacity: 1 }));
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
  controls.dampingFactor = 0.1;
  controls.autoRotate = true;
  controls.autoRotateSpeed = 0.5;
  controls.enableZoom = false; // 禁用自带缩放

  loadRoom(initialRoomId, false);
  animate();
  
  window.addEventListener('resize', onWindowResize);
  window.addEventListener('contextmenu', onContextMenu);
  window.addEventListener('click', closeMenu);
  containerRef.value.addEventListener('wheel', onMouseWheel, { passive: false });
};

// 3. 切换场景
const switchScene = (id) => {
  if (currentRoomId.value === id) return;
  loadRoom(id, true);
  showSceneBar.value = false; // 切换后自动收起
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

    applyRoomSettings(roomData); // 应用编辑器设置

    isLoading.value = false;
    currentRoomId.value = roomId;
    showTip(roomData.name);

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
          isTransitioning.value = false;
        }
      });
    } else {
      nextSphere.material.opacity = 1;
      nextSphere.visible = true;
      currentSphere.visible = false;
      activeSphereIndex = activeSphereIndex === 1 ? 2 : 1;
      createHotspots(roomData.hotspots);
      isLoading.value = false;
    }
  });
};

// [核心] 应用编辑器保存的参数
const applyRoomSettings = (data) => {
  if (!camera || !controls) return;

  // 1. FOV
  camera.fov = data.fov_default;
  camera.updateProjectionMatrix();

  // 2. 水平限制
  if (data.limit_h_min <= -180 && data.limit_h_max >= 180) {
    controls.minAzimuthAngle = -Infinity;
    controls.maxAzimuthAngle = Infinity;
  } else {
    controls.minAzimuthAngle = data.limit_h_min * (Math.PI / 180);
    controls.maxAzimuthAngle = data.limit_h_max * (Math.PI / 180);
  }

  // 3. 垂直限制 (Editor: -90 Bottom, 90 Top -> Three: PI Bottom, 0 Top)
  // Top Limit (UI Max) -> Three Min
  controls.minPolarAngle = (90 - data.limit_v_max) * (Math.PI / 180);
  // Bottom Limit (UI Min) -> Three Max
  controls.maxPolarAngle = (90 - data.limit_v_min) * (Math.PI / 180);

  // 4. 初始视角 (Editor: Heading -> Azimuth, Pitch -> Polar)
  // Pitch (UI -90~90) -> Polar (PI~0)
  // Formula: Polar = (90 - Pitch) * (PI/180)
  controls.reset();
  const azimuth = data.initial_heading * (Math.PI / 180);
  const polar = (90 - data.initial_pitch) * (Math.PI / 180);
  
  const r = 0.1;
  camera.position.x = r * Math.sin(polar) * Math.sin(azimuth);
  camera.position.y = r * Math.cos(polar);
  camera.position.z = r * Math.sin(polar) * Math.cos(azimuth);
  
  controls.update();
};

const clearHotspots = () => { hotspotMeshes.forEach(mesh => { scene.remove(mesh); mesh.geometry.dispose(); mesh.material.dispose(); }); hotspotMeshes = []; };
const createHotspots = (list) => { 
  if(!list) return;
  list.forEach(hs => {
    // 渲染热点
    const geometry = new THREE.SphereGeometry(15, 32, 16);
    const material = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.8 }); // 白色更通用
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(...hs.position);
    mesh.userData = { targetRoom: hs.target, text: hs.text };
    
    // 添加文字标签 (简单 Sprite)
    // 这里为了演示简单用颜色区分，实际项目可以用 SpriteText
    
    scene.add(mesh);
    hotspotMeshes.push(mesh);
    
    // 简单的入场动画
    mesh.scale.set(0,0,0);
    gsap.to(mesh.scale, { x:1, y:1, z:1, duration: 0.5, ease: "back.out(1.7)" });
  });
};

const onPointerDown = (e) => {
  if (isTransitioning.value) return;
  const rect = containerRef.value.getBoundingClientRect();
  pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const intersects = raycaster.intersectObjects(hotspotMeshes);
  if (intersects.length > 0) {
    const targetId = intersects[0].object.userData.targetRoom;
    if (roomsConfig.value[targetId]) {
      loadRoom(targetId, true);
    } else {
      showTip("目标场景未定义");
    }
  }
};

const onMouseWheel = (e) => {
  e.preventDefault();
  const roomData = roomsConfig.value[currentRoomId.value];
  if (!roomData) return;
  
  let newFov = camera.fov + e.deltaY * 0.05;
  newFov = Math.max(roomData.fov_min, Math.min(roomData.fov_max, newFov));
  
  camera.fov = newFov;
  camera.updateProjectionMatrix();
};

const animate = () => { requestAnimationFrame(animate); controls.update(); renderer.render(scene, camera); };
const onWindowResize = () => { if (!containerRef.value) return; camera.aspect = containerRef.value.clientWidth / containerRef.value.clientHeight; camera.updateProjectionMatrix(); renderer.setSize(containerRef.value.clientWidth, containerRef.value.clientHeight); };
const onContextMenu = (e) => { e.preventDefault(); menuPos.value = {x:e.clientX, y:e.clientY}; menuVisible.value = true; };
const closeMenu = () => { menuVisible.value = false; };
const toggleRotate = () => { isRotating.value = !isRotating.value; controls.autoRotate = isRotating.value; };
const toggleDirection = () => { isReverse.value = !isReverse.value; controls.rotateSpeed = isReverse.value ? -0.5 : 0.5; };
const resetCamera = () => { if (currentRoomId.value) applyRoomSettings(roomsConfig.value[currentRoomId.value]); };
const toggleFullscreen = () => { if (!document.fullscreenElement) { document.documentElement.requestFullscreen(); isFullscreen.value = true; } else { document.exitFullscreen(); isFullscreen.value = false; } };

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
.viewer-wrapper { width: 100%; height: 100vh; position: relative; background: #000; overflow: hidden; font-family: sans-serif; }
.three-container { width: 100%; height: 100%; cursor: grab; }
.three-container:active { cursor: grabbing; }

.ui-layer { pointer-events: none; position: absolute; inset: 0; display: flex; flex-direction: column; justify-content: space-between; }

/* 顶部栏 */
.top-bar {
  pointer-events: auto; background: linear-gradient(to bottom, rgba(0,0,0,0.6), transparent);
  padding: 15px 20px; display: flex; align-items: center; gap: 15px;
}
.back-btn { background: rgba(255,255,255,0.2); border: none; padding: 8px; border-radius: 50%; cursor: pointer; transition: background 0.2s; display: flex; }
.back-btn:hover { background: rgba(255,255,255,0.4); }
.project-title { color: white; font-size: 18px; font-weight: bold; text-shadow: 0 1px 3px rgba(0,0,0,0.8); }

/* 底部开关 */
.bottom-controls { pointer-events: auto; padding: 20px; display: flex; justify-content: center; }
.scene-toggle-btn {
  background: rgba(0,0,0,0.6); color: white; border: 1px solid rgba(255,255,255,0.3);
  padding: 8px 20px; border-radius: 30px; cursor: pointer; display: flex; align-items: center; gap: 8px;
  transition: all 0.3s; backdrop-filter: blur(5px);
}
.scene-toggle-btn:hover, .scene-toggle-btn.active { background: rgba(255,255,255,0.9); color: #333; }

/* 场景栏 (弹出) */
.scene-bar-overlay {
  pointer-events: auto; position: absolute; bottom: 80px; left: 0; right: 0;
  display: flex; justify-content: center; padding: 0 20px;
}
.scene-bar-scroll {
  background: rgba(0,0,0,0.8); backdrop-filter: blur(10px); padding: 10px; border-radius: 12px;
  display: flex; gap: 12px; overflow-x: auto; max-width: 100%; box-shadow: 0 5px 20px rgba(0,0,0,0.5);
}
.scene-thumb {
  width: 100px; height: 70px; border-radius: 6px; overflow: hidden; position: relative;
  cursor: pointer; border: 2px solid transparent; flex-shrink: 0; transition: transform 0.2s;
}
.scene-thumb img { width: 100%; height: 100%; object-fit: cover; opacity: 0.6; transition: opacity 0.2s; }
.scene-thumb:hover img { opacity: 1; }
.scene-thumb.active { border-color: #3498db; transform: translateY(-3px); }
.scene-thumb.active img { opacity: 1; }
.scene-name-tag {
  position: absolute; bottom: 0; left: 0; width: 100%; background: rgba(0,0,0,0.6);
  color: white; font-size: 10px; text-align: center; padding: 2px 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

/* 提示与加载 */
.tip-toast {
  position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
  background: rgba(0,0,0,0.7); color: white; padding: 10px 20px; border-radius: 30px; font-size: 16px;
}
.loading-mask { position: absolute; inset: 0; background: #000; z-index: 50; display: flex; flex-direction: column; justify-content: center; align-items: center; color: #888; }
.spinner { width: 40px; height: 40px; border: 4px solid #333; border-top-color: #fff; border-radius: 50%; animation: spin 1s infinite linear; margin-bottom: 15px; }
@keyframes spin { to { transform: rotate(360deg); } }

/* 菜单与动画 */
.context-menu { position: fixed; z-index: 999; background: rgba(255,255,255,0.95); border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); padding: 6px 0; min-width: 140px; pointer-events: auto; }
.context-menu .item { padding: 12px 20px; cursor: pointer; color: #333; font-size: 14px; }
.context-menu .item:hover { background-color: #f0f7ff; color: #007bff; }

.slide-up-enter-active, .slide-up-leave-active { transition: all 0.3s ease; }
.slide-up-enter-from, .slide-up-leave-to { transform: translateY(20px); opacity: 0; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>