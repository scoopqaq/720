<template>
  <div class="editor-layout" @keydown="onKeyDown" tabindex="0" ref="layoutRef">
    
    <header class="global-header">
      <div class="header-left">
        <button class="back-btn" @click="handleBack">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/></svg>
          <span>返回列表</span>
        </button>
        <div class="v-divider"></div>
        <div class="scene-title" v-if="currentScene">
          {{ currentScene.name }}
          <span v-if="isModified" class="modified-dot" title="有未保存修改">•</span>
        </div>
      </div>

      <div class="header-right">
        <button class="btn-text" @click="resetToDefaults">↺ 恢复默认</button>
        <button class="save-primary-btn" :class="{ 'has-changes': isModified }" @click="saveAll" :disabled="saving">
          {{ saving ? '保存中...' : (isModified ? '💾 保存*' : '💾 已保存') }}
        </button>
      </div>
    </header>

    <div class="workspace">
      <div class="left-toolbar">
        <div class="tool-btn" :class="{ active: activeTab === 'view' }" @click="switchTab('view')">
          <div>👁️</div><span class="tool-label">视角</span>
        </div>
        <div class="tool-btn" :class="{ active: activeTab === 'hotspot' }" @click="switchTab('hotspot')">
          <div>📍</div><span class="tool-label">热点</span>
        </div>
      </div>

      <div class="viewport">
        <div 
          ref="containerRef" 
          class="three-container" 
          :style="{ cursor: cursorStyle }"
          @contextmenu.prevent="onContextMenu" 
          @pointerdown="onPointerDown" 
          @pointermove="onPointerMove"
          @pointerup="onPointerUp"
          @pointerleave="onPointerUp" 
        ></div>
        
        <div v-if="activeTab === 'view'" class="center-cross">+</div>

        <div class="toast-tip" v-if="activeTab === 'hotspot'">
          提示：选中热点后，按住热点图标可拖动位置
        </div>

        <transition name="fade">
          <div v-if="menuVisible" class="context-menu" :style="{ left: menuPos.x + 'px', top: menuPos.y + 'px' }">
            <div class="item" @click="toggleDirection">⇄ 拖拽方向: {{ isReverse ? '反向' : '正向' }}</div>
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
          :icons="availableIcons" 
          @create="createHotspotAtCenter"
          @select="selectHotspotByList"
          @live-update="onHotspotLiveUpdate"
          @save="saveSelectedHotspot"
          @delete="deleteSelectedHotspot"
          @batch-delete="batchDeleteHotspots"
          @cancel="cancelHotspotSelection"
          @refresh-icons="fetchIcons"
        />
      </aside>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, markRaw, toRaw, watch } from 'vue';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import SceneManager from './SceneManager.vue';
import PanelBasic from './editor/PanelBasic.vue';
import PanelHotspot from './editor/PanelHotspot.vue';
import { authFetch, getImageUrl } from '../utils/api';
import { GifTexture } from '../utils/GifLoader';

const props = defineProps(['projectId']);
const emit = defineEmits(['back']);

const layoutRef = ref(null);
const containerRef = ref(null);
const iconTextures = {}; 
const activeGifTextures = new Set();

const activeTab = ref('hotspot'); 
const projectData = ref(null);
const scenes = ref([]);
const currentScene = ref(null);
const availableIcons = ref([]);
const saving = ref(false);

const DEFAULT_SETTINGS = { initial_heading: 0, initial_pitch: 0, fov_min: 70, fov_max: 120, fov_default: 95, limit_h_min: -180, limit_h_max: 180, limit_v_min: -90, limit_v_max: 90 };
const settings = reactive({ ...DEFAULT_SETTINGS });
const originalSettingsJson = ref(JSON.stringify(DEFAULT_SETTINGS));
const isModified = computed(() => JSON.stringify(settings) !== originalSettingsJson.value);

const hotspotList = ref([]);
const selectedHotspot = ref(null);
const otherScenes = computed(() => currentScene.value ? scenes.value.filter(s => s.id !== currentScene.value.id) : []);

let scene, camera, renderer, controls, sphereMesh, textureLoader, raycaster, pointer;
let hotspotMeshes = [];      
let labelMeshes = [];        
let animationId;
const menuVisible = ref(false);
const menuPos = ref({ x: 0, y: 0 });
const isReverse = ref(false);

const isDraggingHotspot = ref(false);
const dragTargetMesh = ref(null);
const isHoveringTarget = ref(false);
const dragTargetId = ref(null); // 新增：跟踪拖拽中的热点ID

const cursorStyle = computed(() => {
  if (isDraggingHotspot.value) return 'grabbing';
  if (isHoveringTarget.value) return 'grab';
  return 'default';
});

// --- API ---
const fetchIcons = async () => {
  try {
    const res = await authFetch('/icons/');
    if (res.ok) availableIcons.value = await res.json();
  } catch (e) { console.error(e); }
};

const fetchProject = async () => {
  try {
    const res = await authFetch(`/projects/${props.projectId}`);
    const data = await res.json();
    projectData.value = data;
    const all = [];
    if (data.groups) data.groups.forEach(g => { if (g.scenes) all.push(...g.scenes); });
    scenes.value = all;
    if (all.length > 0) {
      if (!currentScene.value || !all.find(s=>s.id===currentScene.value.id)) loadScene(all[0].id);
      else { const fresh = all.find(s=>s.id===currentScene.value.id); if(fresh) currentScene.value = fresh; }
    }
  } catch(e) { console.error(e); }
};

const loadScene = (sceneId) => {
  activeGifTextures.clear();

  const target = scenes.value.find(s => s.id == sceneId);
  if (!target) return;
  currentScene.value = target;

  Object.keys(DEFAULT_SETTINGS).forEach(key => settings[key] = target[key] ?? DEFAULT_SETTINGS[key]);
  originalSettingsJson.value = JSON.stringify(settings);

  hotspotList.value = (target.hotspots || []).map(h => ({
    id: h.id, text: h.text, type: h.type, content: h.content, 
    target_scene_id: h.target_scene_id, position: [h.x, h.y, h.z],
    icon_type: h.icon_type, icon_url: h.icon_url, 
    scale: h.scale || 1.0, 
    show_text: h.show_text || false 
  }));
  
  selectedHotspot.value = null;

  if (!renderer) initThree();

  textureLoader.load(
    getImageUrl(`${target.image_url}?t=${Date.now()}`),
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
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
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
  controls.dampingFactor = 0.05;
  controls.enableZoom = false; 
  controls.rotateSpeed = 0.5;

  raycaster = new THREE.Raycaster();
  pointer = new THREE.Vector2();

  containerRef.value.addEventListener('wheel', onMouseWheel, { passive: false });
  window.addEventListener('resize', onResize);
  window.addEventListener('click', closeMenu);
  
  window.addEventListener('blur', () => {
    isDraggingHotspot.value = false;
    dragTargetId.value = null;
    controls.enabled = true;
  });
  animate();
};

const getBaseScale = () => 30.0; 

const getIconTexture = (hData) => {
  let url = '';
  if (hData.icon_url) {
    url = getImageUrl(hData.icon_url);
  } else {
    const defaultIcon = availableIcons.value.find(i => i.category === 'system');
    url = defaultIcon ? getImageUrl(defaultIcon.url) : '';
  }

  if (!url) return { isError: true };

  if (iconTextures[url]) {
    if (url.toLowerCase().endsWith('.gif')) {
        activeGifTextures.add(iconTextures[url]);
    }
    return iconTextures[url];
  }

  if (url.toLowerCase().endsWith('.gif')) {
    const gifTexture = new GifTexture(url);
    iconTextures[url] = gifTexture;
    activeGifTextures.add(gifTexture);
    return gifTexture;
  }

  iconTextures[url] = textureLoader.load(url, (tex) => { 
      tex.colorSpace = THREE.SRGBColorSpace;
      const rawMesh = toRaw(hData._mesh);
      if(rawMesh) rawMesh.material.needsUpdate = true;
  }, undefined, () => {
      iconTextures[url].isError = true;
  });
  
  return iconTextures[url];
};

const createTextSprite = (message) => {
  const fontsize = 32;
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  ctx.font = `bold ${fontsize}px Arial`;
  const metrics = ctx.measureText(message);
  
  canvas.width = metrics.width + 20;
  canvas.height = fontsize + 20;
  
  ctx.fillStyle = "rgba(0, 0, 0, 0.5)";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  
  ctx.font = `bold ${fontsize}px Arial`;
  ctx.fillStyle = "white";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(message, canvas.width / 2, canvas.height / 2);
  
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  
  const sprite = markRaw(new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, depthTest: false, transparent: true })));
  const scaleFactor = 0.5; 
  sprite.scale.set(canvas.width / 10 * scaleFactor, canvas.height / 10 * scaleFactor, 1);
  sprite.center.set(0.5, 1.8);
  return sprite;
};

const rebuildHotspotMeshes = () => {
  hotspotMeshes.forEach(m => scene.remove(m));
  labelMeshes.forEach(m => scene.remove(m));
  hotspotMeshes = [];
  labelMeshes = [];

  hotspotList.value.forEach(hData => {
    let texture = getIconTexture(hData);
    
    const matParams = { 
      map: texture,
      transparent: true, 
      depthTest: false, 
      sizeAttenuation: true
    };
    if (texture.isError) matParams.color = 0xff0000;

    const sprite = markRaw(new THREE.Sprite(new THREE.SpriteMaterial(matParams)));
    sprite.position.set(...hData.position);
    sprite.userData = { id: hData.id, isHotspot: true };
    sprite.renderOrder = 999;
    
    const base = getBaseScale();
    const s = (hData.scale || 1.0) * base;
    sprite.scale.set(s, s, 1);

    scene.add(sprite);
    hotspotMeshes.push(sprite);
    hData._mesh = sprite;

    if (hData.show_text && hData.text) {
      const label = createTextSprite(hData.text);
      label.position.copy(sprite.position);
      scene.add(label);
      labelMeshes.push(label);
      hData._labelMesh = label;
    }
  });
  
  if (selectedHotspot.value) {
    updateVisualSelection(selectedHotspot.value.id);
  }
};

const updateVisualSelection = (id) => {
  hotspotMeshes.forEach(mesh => {
    const rawMesh = toRaw(mesh);
    if (rawMesh.userData.id === id) {
      rawMesh.material.opacity = 1.0;
    } else {
      rawMesh.material.opacity = 0.8; 
    }
  });
};

const onHotspotLiveUpdate = (updatedData) => {
  const idx = hotspotList.value.findIndex(h => h.id === updatedData.id);
  if (idx === -1) return;
  
  const item = hotspotList.value[idx];
  Object.assign(item, updatedData);
  
  if (selectedHotspot.value && selectedHotspot.value.id === updatedData.id) {
     Object.assign(selectedHotspot.value, updatedData);
  }
  
  if (updatedData.show_text !== undefined || updatedData.text !== undefined) {
    rebuildHotspotMeshes();
  } else {
    const rawMesh = toRaw(item._mesh);
    if (rawMesh) {
      if (updatedData.position) rawMesh.position.set(...updatedData.position);
      
      const currentUrl = rawMesh.material.map ? rawMesh.material.map.image.src : '';
      if (currentUrl && !currentUrl.includes(updatedData.icon_url)) {
         rawMesh.material.map = getIconTexture(updatedData);
         rawMesh.material.needsUpdate = true;
      }
      
      const base = getBaseScale();
      const s = (updatedData.scale || 1.0) * base;
      rawMesh.scale.set(s, s, 1);
      
      const rawLabel = toRaw(item._labelMesh);
      if (rawLabel) rawLabel.position.set(...updatedData.position);
    }
  }
  updateVisualSelection(updatedData.id);
};

// --- 关键修复：同步 Vue 数据源 ---
const updateHotspotPositionInData = (hotspotId, newPosition) => {
  // 更新 hotspotList 中的数据
  const listIdx = hotspotList.value.findIndex(h => h.id === hotspotId);
  if (listIdx !== -1) {
    hotspotList.value[listIdx].position = newPosition;
  }
  
  // 更新 selectedHotspot 中的数据
  if (selectedHotspot.value && selectedHotspot.value.id === hotspotId) {
    selectedHotspot.value = { ...selectedHotspot.value, position: newPosition };
  }
};

// --- 交互逻辑 ---

const getIntersects = (event, objects) => {
  const rect = containerRef.value.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const rawObjects = objects.map(o => toRaw(o));
  return raycaster.intersectObjects(rawObjects, false);
};

const onPointerDown = (event) => {
  if (activeTab.value !== 'hotspot') return;

  const allHits = getIntersects(event, hotspotMeshes);
  
  if (allHits.length > 0) {
    const hitMesh = allHits[0].object;
    const hitId = hitMesh.userData.id;
    const hitItem = hotspotList.value.find(h => h.id === hitId);

    if (hitItem) {
      selectHotspotByList(hitItem);
      
      if (selectedHotspot.value && selectedHotspot.value.id === hitId) {
        isDraggingHotspot.value = true;
        dragTargetMesh.value = toRaw(hitMesh);
        dragTargetId.value = hitId; // 记录拖拽中的热点ID
        controls.enabled = false;
        if (layoutRef.value) layoutRef.value.focus();
      }
    }
  } else {
    cancelHotspotSelection();
  }
};

const onPointerMove = (event) => {
  if (event.buttons === 0 && isDraggingHotspot.value) {
    onPointerUp();
    return;
  }

  if (activeTab.value !== 'hotspot') return;

  if (isDraggingHotspot.value && dragTargetMesh.value) {
    const rect = containerRef.value.getBoundingClientRect();
    pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(pointer, camera);
    const intersects = raycaster.intersectObject(sphereMesh);
    
    if (intersects.length > 0) {
      const point = intersects[0].point.normalize().multiplyScalar(450);
      
      // 更新 3D 对象位置
      dragTargetMesh.value.position.copy(point);
      
      // 更新标签位置
      const currentItem = hotspotList.value.find(h => h.id === dragTargetId.value);
      const rawLabel = toRaw(currentItem?._labelMesh);
      if (rawLabel) rawLabel.position.copy(point);
      
      // 关键：同步更新 Vue 数据源
      updateHotspotPositionInData(dragTargetId.value, [point.x, point.y, point.z]);
    }
    return;
  }

  // Hover 状态检测
  if (selectedHotspot.value) {
    const item = hotspotList.value.find(h => h.id === selectedHotspot.value.id);
    const targetMesh = item ? toRaw(item._mesh) : null;
    if (targetMesh) {
       const hits = getIntersects(event, [targetMesh]);
       isHoveringTarget.value = hits.length > 0;
    } else { isHoveringTarget.value = false; }
  } else { isHoveringTarget.value = false; }
};

const onPointerUp = () => {
  if (isDraggingHotspot.value) {
    isDraggingHotspot.value = false;
    dragTargetId.value = null;
    controls.enabled = true;
    dragTargetMesh.value = null;
  }
};

const onKeyDown = (e) => {
  if (!selectedHotspot.value || activeTab.value !== 'hotspot') return;
  const item = hotspotList.value.find(h => h.id === selectedHotspot.value.id);
  const mesh = item ? toRaw(item._mesh) : null;
  if (!mesh) return;

  const STEP = 0.01; 
  const pos = new THREE.Vector3().copy(mesh.position);
  const spherical = new THREE.Spherical().setFromVector3(pos);
  let changed = false;

  switch(e.key) {
    case 'ArrowUp': spherical.phi -= STEP; changed = true; break;
    case 'ArrowDown': spherical.phi += STEP; changed = true; break;
    case 'ArrowLeft': spherical.theta += STEP; changed = true; break; 
    case 'ArrowRight': spherical.theta -= STEP; changed = true; break;
  }

  if (changed) {
    e.preventDefault();
    spherical.phi = Math.max(0.1, Math.min(Math.PI - 0.1, spherical.phi));
    const newPos = new THREE.Vector3().setFromSpherical(spherical);
    
    // 更新 3D 对象
    mesh.position.copy(newPos);
    
    // 更新标签
    const rawLabel = toRaw(item._labelMesh);
    if (rawLabel) rawLabel.position.copy(newPos);
    
    // 同步更新 Vue 数据源
    updateHotspotPositionInData(selectedHotspot.value.id, [newPos.x, newPos.y, newPos.z]);
  }
};

const createHotspotAtCenter = async () => {
  const dist = 450; const vec = new THREE.Vector3(); camera.getWorldDirection(vec); vec.multiplyScalar(dist);
  const pos = [vec.x, vec.y, vec.z];
  const defaultIcon = availableIcons.value.find(i => i.category === 'system');
  const defaultUrl = defaultIcon ? defaultIcon.url : '';

  try {
    const res = await authFetch('/hotspots/', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ text: '新建热点', x:pos[0], y:pos[1], z:pos[2], source_scene_id:currentScene.value.id, icon_type: 'system', icon_url: defaultUrl })
    });
    if(res.ok) {
      const s = await res.json();
      const hData = { id:s.id, text:'新建热点', type:'scene', position:pos, icon_type:'system', icon_url: s.icon_url, scale:1.0, show_text: false };
      hotspotList.value.push(hData);
      rebuildHotspotMeshes();
      selectHotspotByList(hData);
    }
  } catch(e) { alert("创建失败"); }
};

const selectHotspotByList = (h) => { 
  selectedHotspot.value = {...h}; 
  updateVisualSelection(h.id);
};

const cancelHotspotSelection = () => { 
  selectedHotspot.value = null; 
  updateVisualSelection(null);
};

const saveSelectedHotspot = async (panelData, silent = false) => {
  try {
    const currentItem = hotspotList.value.find(i => i.id === panelData.id);
    let finalPos = panelData.position; 
    
    if (currentItem && currentItem._mesh) {
      const rawMesh = toRaw(currentItem._mesh);
      finalPos = [rawMesh.position.x, rawMesh.position.y, rawMesh.position.z];
    }

    const payload = { 
      text: panelData.text, 
      target_scene_id: panelData.target_scene_id, 
      x: finalPos[0], y: finalPos[1], z: finalPos[2], 
      icon_type: panelData.icon_type, 
      icon_url: panelData.icon_url, 
      scale: panelData.scale, 
      show_text: panelData.show_text, 
      content: panelData.content, 
      type: panelData.type
    };

    const res = await authFetch(`/hotspots/${panelData.id}`, {
      method: 'PUT', headers: {'Content-Type':'application/json'}, 
      body: JSON.stringify(payload)
    });

    if(res.ok) {
      const idx = hotspotList.value.findIndex(i=>i.id===panelData.id);
      if(idx!==-1) {
        const existingMesh = hotspotList.value[idx]._mesh;
        const existingLabel = hotspotList.value[idx]._labelMesh;
        hotspotList.value[idx] = { 
          ...hotspotList.value[idx], 
          ...payload, 
          position: finalPos,
          _mesh: existingMesh, 
          _labelMesh: existingLabel 
        };
      }
      if(!silent) alert("热点已保存");
    }
  } catch(e){ if(!silent) alert("保存失败"); }
};

const deleteSelectedHotspot = async (h) => {
  if(!confirm("删除?")) return;
  try { await authFetch(`/hotspots/${h.id}`, { method:'DELETE' }); hotspotList.value = hotspotList.value.filter(i=>i.id!==h.id); selectedHotspot.value=null; rebuildHotspotMeshes(); } catch(e){alert("失败");}
};

const batchDeleteHotspots = async (ids) => {
  try { await authFetch('/hotspots/batch_delete/', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(ids) }); hotspotList.value = hotspotList.value.filter(h=>!ids.includes(h.id)); selectedHotspot.value=null; rebuildHotspotMeshes(); } catch(e){alert("失败");}
};

const switchTab = (tab) => { activeTab.value = tab; cancelHotspotSelection(); };
const switchScene = (id) => { if(isModified.value && !confirm("未保存将丢失"))return; loadScene(id); };
const handleBack = () => { if(isModified.value && !confirm("有未保存修改，离开？"))return; emit('back'); };
const saveAll = async () => { saving.value=true; try{ const p={...settings}; const r=await authFetch(`/scenes/${currentScene.value.id}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)}); if(r.ok){ originalSettingsJson.value=JSON.stringify(settings); } }catch(e){alert("Error");}finally{saving.value=false;} };
const resetToDefaults = () => { if(!confirm("恢复?"))return; Object.assign(settings, DEFAULT_SETTINGS); applyAllSettingsToThree(); };

const applyAllSettingsToThree = () => { if (!controls) return; camera.fov = settings.fov_default; camera.updateProjectionMatrix(); const az = settings.initial_heading * (Math.PI / 180); const pl = (settings.initial_pitch + 90) * (Math.PI / 180); const r = 0.1; camera.position.x = r * Math.sin(pl) * Math.sin(az); camera.position.y = r * Math.cos(pl); camera.position.z = r * Math.sin(pl) * Math.cos(az); controls.target.set(0,0,0); applyLimitsAndFOV(); controls.update(); };
const applyLimitsAndFOV = () => { 
  if(!controls) return; 
  camera.fov = settings.fov_default; camera.updateProjectionMatrix(); 
  if (settings.limit_h_min <= -180 && settings.limit_h_max >= 180) { controls.minAzimuthAngle = -Infinity; controls.maxAzimuthAngle = Infinity; } else { controls.minAzimuthAngle = settings.limit_h_min * (Math.PI / 180); controls.maxAzimuthAngle = settings.limit_h_max * (Math.PI / 180); } 
  controls.minPolarAngle = Math.max(0, (90 - settings.limit_v_max) * (Math.PI / 180));
  controls.maxPolarAngle = Math.min(Math.PI, (90 - settings.limit_v_min) * (Math.PI / 180));
  controls.update(); 
};
const onFovPreview = (val) => { camera.fov = val; camera.updateProjectionMatrix(); };
const onHLimitPreview = (val) => { const rad = val * (Math.PI / 180); controls.minAzimuthAngle = -Infinity; controls.maxAzimuthAngle = Infinity; const pl = controls.getPolarAngle(); const r = 0.1; camera.position.x = r * Math.sin(pl) * Math.sin(rad); camera.position.z = r * Math.sin(pl) * Math.cos(rad); controls.update(); };
const onVLimitPreview = (val) => { const rad = (90 - val) * (Math.PI / 180); controls.minPolarAngle = 0; controls.maxPolarAngle = Math.PI; const az = controls.getAzimuthalAngle(); const r = 0.1; camera.position.x = r * Math.sin(rad) * Math.sin(az); camera.position.y = r * Math.cos(rad); camera.position.z = r * Math.sin(rad) * Math.cos(az); controls.update(); };
const captureInitialState = () => { const az=controls.getAzimuthalAngle(); const pl=controls.getPolarAngle(); settings.initial_heading=az*(180/Math.PI); settings.initial_pitch=90-(pl*(180/Math.PI)); settings.fov_default=camera.fov; };
const captureCover = async () => { renderer.render(scene,camera); const d=renderer.domElement.toDataURL('image/jpeg',0.7); try{ const r1=await authFetch('/upload_base64/',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({image_data:d})}); const d1=await r1.json(); await authFetch(`/scenes/${currentScene.value.id}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({cover_url:d1.url})}); alert("封面已更新"); fetchProject(); }catch(e){} };

const onMouseWheel = (e) => { e.preventDefault(); let f=camera.fov+e.deltaY*0.05; f=Math.max(settings.fov_min, Math.min(settings.fov_max, f)); camera.fov=f; camera.updateProjectionMatrix(); };
const animate = () => { 
  animationId = requestAnimationFrame(animate); 
  
  activeGifTextures.forEach(texture => {
    if (texture.update) texture.update();
  });

  controls.update(); 
  renderer.render(scene,camera); 
};
const onResize = () => { if(containerRef.value){ camera.aspect=containerRef.value.clientWidth/containerRef.value.clientHeight; camera.updateProjectionMatrix(); renderer.setSize(containerRef.value.clientWidth,containerRef.value.clientHeight); } };
const onContextMenu = (e) => { e.preventDefault(); menuPos.value = {x:e.clientX, y:e.clientY}; menuVisible.value = true; };
const toggleDirection = () => { isReverse.value = !isReverse.value; controls.rotateSpeed = isReverse.value ? -0.5 : 0.5; };
const resetView = () => applyAllSettingsToThree();
const closeMenu = () => { menuVisible.value = false; };
const onBeforeUnload = (e) => { if (isModified.value) { e.preventDefault(); e.returnValue = ''; } };

onMounted(() => { 
  fetchIcons(); 
  fetchProject(); 
  window.addEventListener('beforeunload', onBeforeUnload); 
});
onBeforeUnmount(() => { 
  cancelAnimationFrame(animationId);
  activeGifTextures.clear();
  window.removeEventListener('beforeunload', onBeforeUnload); 
  window.removeEventListener('resize', onResize); 
  window.removeEventListener('click', closeMenu);
  if(renderer) renderer.dispose(); 
});
</script>

<style scoped>
.editor-layout { display: flex; height: 100vh; background: #1a1a1a; color: #ccc; user-select: none; flex-direction: column; outline: none; }
.global-header { height: 50px; background: #2d2d2d; border-bottom: 1px solid #111; display: flex; justify-content: space-between; align-items: center; padding: 0 20px; z-index: 100; }
.header-left { display: flex; align-items: center; z-index: 2; gap: 15px; }
.back-btn { background: none; border: none; color: #aaa; cursor: pointer; display: flex; align-items: center; gap: 5px; font-size: 13px; padding: 0; }
.back-btn:hover { color: white; }
.v-divider { width: 1px; height: 14px; background: #555; }
.scene-title { font-weight: bold; color: white; font-size: 15px; }
.modified-dot { color: #e74c3c; font-size: 20px; line-height: 1; margin-left: 5px; }
.header-right { display: flex; align-items: center; gap: 15px; z-index: 2; }
.workspace { flex: 1; display: flex; position: relative; overflow: hidden; }
.left-toolbar { width: 50px; background: #252526; border-right: 1px solid #111; display: flex; flex-direction: column; align-items: center; padding-top: 15px; }
.tool-btn { width: 40px; height: 40px; margin-bottom: 15px; display: flex; flex-direction: column; align-items: center; justify-content: center; cursor: pointer; color: #888; border-radius: 6px; transition: all 0.2s; }
.tool-btn:hover { background: #333; color: #fff; }
.tool-btn.active { background: #3498db; color: #fff; }
.tool-label { font-size: 10px; margin-top: 2px; }
.viewport { flex: 1; position: relative; background: #000; padding-bottom: 140px; }
.three-container { width: 100%; height: 100%; }
.right-sidebar { width: 320px; background: #252526; border-left: 1px solid #111; display: flex; flex-direction: column; }
.panel-header { height: 40px; line-height: 40px; padding: 0 15px; font-weight: bold; background: #2d2d2d; border-bottom: 1px solid #333; color: #eee; font-size: 13px; }
.btn-text { background: none; border: none; color: #888; cursor: pointer; font-size: 12px; }
.save-primary-btn { background: #333; color: #888; border: 1px solid #444; padding: 6px 16px; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 13px; transition: all 0.3s; }
.save-primary-btn.has-changes { background: #e67e22; color: white; border-color: #d35400; }
.center-cross { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: rgba(255,255,255,0.3); font-size: 20px; pointer-events: none; }
.toast-tip { position: absolute; top: 20px; left: 50%; transform: translateX(-50%); background: rgba(0,0,0,0.6); color: white; padding: 5px 15px; border-radius: 20px; font-size: 12px; pointer-events: none; }
.context-menu { position: fixed; z-index: 9999; background: #333; border: 1px solid #444; border-radius: 4px; padding: 5px 0; min-width: 160px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
.context-menu .item { padding: 8px 15px; font-size: 13px; color: #ddd; cursor: pointer; }
.context-menu .item:hover { background: #444; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>