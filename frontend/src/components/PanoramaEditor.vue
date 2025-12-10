<template>
  <div class="editor-root">
    
    <header class="top-header">
      
      <div class="header-left">
        <button class="back-btn" @click="handleBack">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/></svg>
          返回列表
        </button>
      </div>

      <div class="header-center" v-if="currentScene">
        <span class="scene-name">{{ currentScene.name }}</span>
        <span v-if="isModified" class="modified-dot" title="有未保存修改">•</span>
      </div>

      <div class="header-right">
        <button class="btn-text" @click="resetToDefaults">↺ 恢复默认</button>
        <button class="save-btn" :class="{ 'has-changes': isModified }" @click="saveAll" :disabled="saving">
          {{ saving ? '保存中...' : (isModified ? '💾 保存*' : '💾 已保存') }}
        </button>
      </div>
    </header>

    <div class="main-body">
      
      <aside class="left-toolbar">
        <div 
          class="tool-item" 
          :class="{ active: activeTab === 'view' }"
          @click="switchTab('view')"
          title="基础设置"
        >
          <div class="icon">👁️</div>
          <span class="label">视角</span>
        </div>
        <div 
          class="tool-item" 
          :class="{ active: activeTab === 'hotspot' }"
          @click="switchTab('hotspot')"
          title="热点编辑"
        >
          <div class="icon">📍</div>
          <span class="label">热点</span>
        </div>
      </aside>

      <div class="viewport-area">
        <div 
          ref="containerRef" 
          class="three-container"
          @contextmenu.prevent="onContextMenu" 
          @pointerdown="onViewportClick"
        ></div>
        
        <div v-if="activeTab === 'view'" class="center-cross">+</div>
        
        <transition name="fade">
          <div v-if="menuVisible" class="context-menu" :style="{ left: menuPos.x + 'px', top: menuPos.y + 'px' }">
            <div class="item" @click="toggleDirection">⇄ 方向: {{ isReverse ? '反向' : '正向' }}</div>
            <div class="item" @click="resetView">↺ 视角复位</div>
          </div>
        </transition>

        <SceneManager 
          v-if="projectData"
          ref="sceneManagerRef"
          :projectData="projectData"
          :currentSceneId="currentScene ? currentScene.id : null"
          @change-scene="switchScene"
          @refresh-data="fetchProject"
        />
      </div>

      <aside class="right-sidebar">
        <div class="panel-header">
          {{ activeTab === 'view' ? '视角参数配置' : '热点编辑管理' }}
        </div>
        
        <PanelBasic 
          v-if="activeTab === 'view'"
          :settings="settings"
          @update-camera="applyLimitsAndFOV"
          @capture-initial="captureInitialState"
          @capture-cover="captureCover"
          @preview-fov="onFovPreview"
          @preview-h-limit="onHLimitPreview"
          @preview-v-limit="onVLimitPreview"
        />

        <PanelHotspot 
          v-if="activeTab === 'hotspot'"
          :list="hotspotList"
          :selectedHotspot="selectedHotspot"
          :otherScenes="otherScenes"
          @select="selectHotspotByList"
          @save="saveSelectedHotspot"
          @delete="deleteSelectedHotspot"
          @cancel="cancelHotspotSelection"
        />
      </aside>

    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import SceneManager from './SceneManager.vue';
import PanelBasic from './editor/PanelBasic.vue';
import PanelHotspot from './editor/PanelHotspot.vue';

const props = defineProps(['projectId']);
const emit = defineEmits(['back']);

// --- 状态 ---
const activeTab = ref('view');
const projectData = ref(null);
const scenes = ref([]);
const currentScene = ref(null);
const containerRef = ref(null);
const sceneManagerRef = ref(null);
const saving = ref(false);

// 设置
const DEFAULT_SETTINGS = {
  initial_heading: 0, initial_pitch: 0,
  fov_min: 70, fov_max: 120, fov_default: 95,
  limit_h_min: -180, limit_h_max: 180,
  limit_v_min: -90, limit_v_max: 90,
};
const settings = reactive({ ...DEFAULT_SETTINGS });
const originalSettingsJson = ref(JSON.stringify(DEFAULT_SETTINGS));
const isModified = computed(() => JSON.stringify(settings) !== originalSettingsJson.value);

// 热点
const hotspotList = ref([]);
const selectedHotspot = ref(null);
const otherScenes = computed(() => currentScene.value ? scenes.value.filter(s => s.id !== currentScene.value.id) : []);

// Three.js
let scene, camera, renderer, controls, sphereMesh, textureLoader, raycaster, pointer;
let hotspotMeshes = [];
let animationId;
const menuVisible = ref(false);
const menuPos = ref({ x: 0, y: 0 });
const isReverse = ref(false);

// --- 初始化 ---
const fetchProject = async () => {
  try {
    const res = await fetch(`http://127.0.0.1:8000/projects/${props.projectId}`);
    const data = await res.json();
    projectData.value = data;
    const allScenes = [];
    if (data.groups) data.groups.forEach(g => { if (g.scenes) allScenes.push(...g.scenes); });
    scenes.value = allScenes;

    if (allScenes.length > 0) {
      if (!currentScene.value || !allScenes.find(s=>s.id===currentScene.value.id)) {
        loadScene(allScenes[0].id);
      } else {
        // 刷新当前场景数据
        const fresh = allScenes.find(s=>s.id===currentScene.value.id);
        if(fresh) currentScene.value = fresh;
      }
    }
    if(sceneManagerRef.value) sceneManagerRef.value.initSelection();
  } catch(e) { console.error(e); }
};

const loadScene = (sceneId) => {
  const target = scenes.value.find(s => s.id == sceneId);
  if (!target) return;
  currentScene.value = target;

  Object.keys(DEFAULT_SETTINGS).forEach(key => settings[key] = target[key] ?? DEFAULT_SETTINGS[key]);
  originalSettingsJson.value = JSON.stringify(settings);

  hotspotList.value = (target.hotspots || []).map(h => ({
    id: h.id, text: h.text, target_scene_id: h.target_scene_id, position: [h.x, h.y, h.z]
  }));
  selectedHotspot.value = null;

  if (!renderer) initThree();

  textureLoader.load(
    `http://127.0.0.1:8000${target.image_url}?t=${Date.now()}`,
    (tex) => {
      tex.colorSpace = THREE.SRGBColorSpace;
      sphereMesh.material.map = tex;
      sphereMesh.material.needsUpdate = true;
      rebuildHotspotMeshes();
      controls.reset();
      applyAllSettingsToThree();
    }
  );
};

const initThree = () => {
  const w = containerRef.value.clientWidth;
  const h = containerRef.value.clientHeight;
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(settings.fov_default, w/h, 0.1, 1000);
  camera.position.set(0,0,0.1);
  renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setSize(w, h);
  containerRef.value.appendChild(renderer.domElement);

  const geo = new THREE.SphereGeometry(500, 60, 40);
  geo.scale(-1, 1, 1);
  sphereMesh = new THREE.Mesh(geo, new THREE.MeshBasicMaterial());
  sphereMesh.rotation.y = -Math.PI / 2;
  scene.add(sphereMesh);

  textureLoader = new THREE.TextureLoader();
  textureLoader.setCrossOrigin('anonymous');
  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.1;
  controls.enableZoom = false; 
  controls.rotateSpeed = 0.5;

  raycaster = new THREE.Raycaster();
  pointer = new THREE.Vector2();

  containerRef.value.addEventListener('wheel', onMouseWheel, { passive: false });
  containerRef.value.addEventListener('dblclick', onDoubleClick);

  animate();
  window.addEventListener('resize', onResize);
  window.addEventListener('click', () => menuVisible.value = false);
};

// --- View Logic ---
const applyAllSettingsToThree = () => {
  if (!controls) return;
  camera.fov = settings.fov_default;
  camera.updateProjectionMatrix();
  const azimuth = settings.initial_heading * (Math.PI / 180);
  const polar = (settings.initial_pitch + 90) * (Math.PI / 180);
  const r = 0.1;
  camera.position.x = r * Math.sin(polar) * Math.sin(azimuth);
  camera.position.y = r * Math.cos(polar);
  camera.position.z = r * Math.sin(polar) * Math.cos(azimuth);
  controls.target.set(0,0,0);
  applyLimitsAndFOV();
  controls.update();
};

const applyLimitsAndFOV = () => {
  if(!controls || !camera) return;
  camera.fov = settings.fov_default;
  camera.updateProjectionMatrix();

  if (settings.limit_h_min <= -180 && settings.limit_h_max >= 180) {
    controls.minAzimuthAngle = -Infinity; controls.maxAzimuthAngle = Infinity;
  } else {
    controls.minAzimuthAngle = settings.limit_h_min * (Math.PI / 180);
    controls.maxAzimuthAngle = settings.limit_h_max * (Math.PI / 180);
  }
  controls.maxPolarAngle = (90 - settings.limit_v_min) * (Math.PI / 180);
  controls.minPolarAngle = (90 - settings.limit_v_max) * (Math.PI / 180);
  controls.update();
};

const onFovPreview = (val) => { camera.fov = val; camera.updateProjectionMatrix(); };
const onHLimitPreview = (val) => { 
  const rad = val * (Math.PI / 180); controls.minAzimuthAngle = -Infinity; controls.maxAzimuthAngle = Infinity;
  const pl = controls.getPolarAngle(); const r = 0.1;
  camera.position.x = r * Math.sin(pl) * Math.sin(rad); camera.position.z = r * Math.sin(pl) * Math.cos(rad); controls.update();
};
const onVLimitPreview = (val) => {
  const rad = (90 - val) * (Math.PI / 180); controls.minPolarAngle = 0; controls.maxPolarAngle = Math.PI;
  const az = controls.getAzimuthalAngle(); const r = 0.1;
  camera.position.x = r * Math.sin(rad) * Math.sin(az); camera.position.y = r * Math.cos(rad); camera.position.z = r * Math.sin(rad) * Math.cos(az); controls.update();
};

const captureInitialState = () => {
  const az = controls.getAzimuthalAngle(); const pl = controls.getPolarAngle();
  settings.initial_heading = az * (180 / Math.PI);
  settings.initial_pitch = (pl * (180 / Math.PI)) - 90;
  settings.fov_default = camera.fov;
};

const captureCover = async () => {
  renderer.render(scene, camera);
  const dataUrl = renderer.domElement.toDataURL('image/jpeg', 0.7);
  try {
    const r1 = await fetch('http://127.0.0.1:8000/upload_base64/', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({image_data:dataUrl})});
    const d1 = await r1.json();
    await fetch(`http://127.0.0.1:8000/scenes/${currentScene.value.id}`, {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({cover_url:d1.url})});
    alert("封面已更新"); fetchProject();
  } catch(e){}
};

// --- Hotspot Logic ---
const rebuildHotspotMeshes = () => {
  hotspotMeshes.forEach(mesh => scene.remove(mesh));
  hotspotMeshes = [];
  hotspotList.value.forEach(hData => {
    const mesh = createHotspotMesh(hData.position);
    mesh.userData = { id: hData.id }; 
    scene.add(mesh);
    hotspotMeshes.push(mesh);
    hData._mesh = mesh;
  });
};
const createHotspotMesh = (pos) => {
  const geo = new THREE.SphereGeometry(10, 32, 16);
  const mat = new THREE.MeshBasicMaterial({ color: 0xff0000, transparent: true, opacity: 0.8 });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.position.set(...pos);
  return mesh;
};
const onViewportClick = (event) => {
  if (activeTab.value !== 'hotspot') return;
  const rect = containerRef.value.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const intersects = raycaster.intersectObjects(hotspotMeshes);
  if (intersects.length > 0) {
    const hit = intersects[0].object;
    const hData = hotspotList.value.find(h => h.id === hit.userData.id) || hotspotList.value.find(h => h._mesh === hit);
    if (hData) selectHotspotByList(hData);
  } else {
    cancelHotspotSelection();
  }
};
const onDoubleClick = (event) => {
  if (activeTab.value !== 'hotspot') return;
  const rect = containerRef.value.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const intersects = raycaster.intersectObject(sphereMesh);
  if (intersects.length > 0) {
    const p = intersects[0].point.clone().normalize().multiplyScalar(450);
    addNewHotspot([p.x, p.y, p.z]);
  }
};
const addNewHotspot = async (pos) => {
  try {
    const res = await fetch('http://127.0.0.1:8000/hotspots/', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ text:'新热点', x:pos[0], y:pos[1], z:pos[2], source_scene_id:currentScene.value.id, target_scene_id:0 })
    });
    if(res.ok) {
      const saved = await res.json();
      const hData = { id:saved.id, text:saved.text, target_scene_id:saved.target_scene_id, position:pos };
      const mesh = createHotspotMesh(pos); mesh.userData={id:saved.id}; scene.add(mesh); hotspotMeshes.push(mesh); hData._mesh=mesh;
      hotspotList.value.push(hData); selectHotspotByList(hData);
    }
  } catch(e){alert("添加失败");}
};
const selectHotspotByList = (h) => {
  selectedHotspot.value = { ...h }; // 复制用于编辑
  hotspotMeshes.forEach(m => m.material.color.set(0xff0000));
  if(h._mesh) h._mesh.material.color.set(0x00ff00);
};
const cancelHotspotSelection = () => {
  selectedHotspot.value = null;
  hotspotMeshes.forEach(m => m.material.color.set(0xff0000));
};
const saveSelectedHotspot = async (h) => {
  try {
    const res = await fetch(`http://127.0.0.1:8000/hotspots/${h.id}`, {
      method: 'PUT', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ text:h.text, target_scene_id:h.target_scene_id })
    });
    if(res.ok) {
      const orig = hotspotList.value.find(i=>i.id===h.id);
      if(orig) { orig.text=h.text; orig.target_scene_id=h.target_scene_id; }
      alert("热点已保存");
    }
  } catch(e){alert("失败");}
};
const deleteSelectedHotspot = async (h) => {
  if(!confirm("删除?")) return;
  try {
    await fetch(`http://127.0.0.1:8000/hotspots/${h.id}`, { method:'DELETE' });
    const mesh = hotspotMeshes.find(m=>m.userData.id===h.id);
    if(mesh) { scene.remove(mesh); mesh.geometry.dispose(); mesh.material.dispose(); hotspotMeshes=hotspotMeshes.filter(m=>m!==mesh); }
    hotspotList.value = hotspotList.value.filter(i=>i.id!==h.id);
    selectedHotspot.value = null;
  } catch(e){alert("失败");}
};

// --- Common ---
const switchTab = (tab) => { activeTab.value = tab; cancelHotspotSelection(); };
const switchScene = (id) => { if(isModified.value && !confirm("未保存将丢失"))return; loadScene(id); };
const saveAll = async () => { saving.value=true; try{ const p={...settings}; const r=await fetch(`http://127.0.0.1:8000/scenes/${currentScene.value.id}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)}); if(r.ok){ originalSettingsJson.value=JSON.stringify(settings); } }catch(e){alert("Error");}finally{saving.value=false;} };
const resetToDefaults = () => { if(!confirm("恢复?"))return; Object.assign(settings, DEFAULT_SETTINGS); applyAllSettingsToThree(); };
const handleBack = () => { if(isModified.value && !confirm("有未保存修改，离开？"))return; emit('back'); };
const onContextMenu = (e) => { e.preventDefault(); menuPos.value = {x:e.clientX, y:e.clientY}; menuVisible.value = true; };
const toggleDirection = () => { isReverse.value = !isReverse.value; controls.rotateSpeed = isReverse.value ? -0.5 : 0.5; };
const resetView = () => applyAllSettingsToThree();
const onMouseWheel = (e) => { e.preventDefault(); let f=camera.fov+e.deltaY*0.05; f=Math.max(settings.fov_min, Math.min(settings.fov_max, f)); camera.fov=f; camera.updateProjectionMatrix(); };
const animate = () => { animationId=requestAnimationFrame(animate); controls.update(); renderer.render(scene,camera); };
const onResize = () => { if(containerRef.value){ camera.aspect=containerRef.value.clientWidth/containerRef.value.clientHeight; camera.updateProjectionMatrix(); renderer.setSize(containerRef.value.clientWidth,containerRef.value.clientHeight); } };
const onBeforeUnload = (e) => { if (isModified.value) { e.preventDefault(); e.returnValue = ''; } };

onMounted(() => { fetchProject(); window.addEventListener('beforeunload', onBeforeUnload); });
onBeforeUnmount(() => { cancelAnimationFrame(animationId); window.removeEventListener('beforeunload', onBeforeUnload); window.removeEventListener('resize', onResize); if(renderer) renderer.dispose(); });
</script>

<style scoped>
.editor-root { display: flex; flex-direction: column; height: 100vh; background: #1a1a1a; color: #ccc; }

/* 1. Header (Fixed Height) */
.top-header {
  height: 50px; 
  background: #2d2d2d; 
  border-bottom: 1px solid #111;
  display: flex; 
  justify-content: space-between; /* 左右推开 */
  align-items: center; 
  padding: 0 20px; 
  z-index: 50;
  position: relative; /* [关键] 为绝对定位提供基准 */
}
.header-left { display: flex; align-items: center; gap: 15px; }
.back-btn { background: none; border: none; color: #aaa; cursor: pointer; display: flex; align-items: center; gap: 5px; font-size: 13px; }
.back-btn:hover { color: white; }
.v-divider { width: 1px; height: 16px; background: #555; }
.scene-title { font-weight: bold; color: white; font-size: 14px; }
.modified-dot { color: #e74c3c; margin-left: 5px; }

.header-right { display: flex; align-items: center; gap: 15px; }
.btn-text { background: none; border: none; color: #888; cursor: pointer; font-size: 12px; }
.btn-text:hover { color: #ccc; }
.save-btn { background: #333; color: #888; border: 1px solid #444; padding: 6px 16px; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 13px; transition: all 0.3s; }
.save-btn.has-changes { background: #e67e22; color: white; border-color: #d35400; box-shadow: 0 0 8px rgba(230,126,34,0.4); }
.save-btn:hover { opacity: 0.9; }

/* 2. Main Body (Flex Row) */
.main-body { flex: 1; display: flex; overflow: hidden; position: relative; }

/* Left Toolbar */
.left-toolbar { width: 50px; background: #252526; border-right: 1px solid #111; display: flex; flex-direction: column; align-items: center; padding-top: 15px; }
.tool-item { width: 40px; height: 40px; margin-bottom: 15px; display: flex; flex-direction: column; align-items: center; justify-content: center; cursor: pointer; color: #888; border-radius: 6px; transition: all 0.2s; }
.tool-item:hover { background: #333; color: white; }
.tool-item.active { background: #3498db; color: white; }
.tool-item .icon { font-size: 18px; margin-bottom: 2px; }
.tool-item .label { font-size: 10px; }

/* Viewport (Middle) */
.viewport-area { flex: 1; position: relative; background: #000; overflow: hidden; }
.three-container { width: 100%; height: 100%; }
.center-cross { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: rgba(255,255,255,0.3); font-size: 20px; pointer-events: none; }
.toast-tip { position: absolute; top: 20px; left: 50%; transform: translateX(-50%); background: rgba(0,0,0,0.6); padding: 5px 15px; border-radius: 20px; font-size: 12px; pointer-events: none; }

/* Right Sidebar */
.right-sidebar { width: 320px; background: #252526; border-left: 1px solid #111; display: flex; flex-direction: column; box-shadow: -5px 0 15px rgba(0,0,0,0.2); }
.panel-header { height: 40px; line-height: 40px; padding: 0 15px; font-weight: bold; font-size: 13px; border-bottom: 1px solid #111; background: #2d2d2d; color: #ddd; }

/* Context Menu */
.context-menu { position: fixed; z-index: 9999; background: #333; border: 1px solid #444; border-radius: 4px; padding: 5px 0; min-width: 160px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
.context-menu .item { padding: 8px 15px; font-size: 13px; color: #ddd; cursor: pointer; }
.context-menu .item:hover { background: #444; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>