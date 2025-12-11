<template>
  <div class="editor-layout">
    
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
          @contextmenu.prevent="onContextMenu" 
          @pointerdown="onViewportClick" 
        ></div>
        
        <div v-if="activeTab === 'view'" class="center-cross">+</div>

        <div class="toast-tip" v-if="activeTab === 'hotspot'">
          提示：双击画面 或 点击右侧“添加”按钮创建热点
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
          @create="createHotspotAtCenter"
          @select="selectHotspotByList"
          @save="saveSelectedHotspot"
          @delete="deleteSelectedHotspot"
          @batch-delete="batchDeleteHotspots"
          @cancel="cancelHotspotSelection"
        />
      </aside>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch } from 'vue';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import SceneManager from './SceneManager.vue';
import PanelBasic from './editor/PanelBasic.vue';
import PanelHotspot from './editor/PanelHotspot.vue';
import { authFetch, getImageUrl } from '../utils/api';

const props = defineProps(['projectId']);
const emit = defineEmits(['back']);

// Base64 Icons
const SYSTEM_ICONS = {
  arrow: 'data:image/png;base64,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'
};

const iconTextures = {}; 

// State
const activeTab = ref('view');
const projectData = ref(null);
const scenes = ref([]);
const currentScene = ref(null);
const containerRef = ref(null);
const sceneManagerRef = ref(null);
const saving = ref(false);

const DEFAULT_SETTINGS = { initial_heading: 0, initial_pitch: 0, fov_min: 70, fov_max: 120, fov_default: 95, limit_h_min: -180, limit_h_max: 180, limit_v_min: -90, limit_v_max: 90 };
const settings = reactive({ ...DEFAULT_SETTINGS });
const originalSettingsJson = ref(JSON.stringify(DEFAULT_SETTINGS));

// [核心] 修复脏检查逻辑：对比时忽略顺序差异，确保数据加载完再对比
const isModified = computed(() => {
  return JSON.stringify(settings) !== originalSettingsJson.value;
});

// Hotspots
const hotspotList = ref([]);
const selectedHotspot = ref(null);
const otherScenes = computed(() => currentScene.value ? scenes.value.filter(s => s.id !== currentScene.value.id) : []);

// Three Vars
let scene, camera, renderer, controls, sphereMesh, textureLoader, raycaster, pointer;
let hotspotMeshes = [];
let animationId;
let isDraggingHotspot = false;
let draggedHotspot = null;
let dragPlane = new THREE.Plane();
let dragOffset = new THREE.Vector3();
const menuVisible = ref(false);
const menuPos = ref({ x: 0, y: 0 });
const isReverse = ref(false);

const fetchProject = async () => {
  try {
    const res = await authFetch(`/projects/${props.projectId}`);
    const data = await res.json();
    projectData.value = data;
    const allScenes = [];
    if (data.groups) data.groups.forEach(g => { if (g.scenes) allScenes.push(...g.scenes); });
    scenes.value = allScenes;
    if (allScenes.length > 0) {
      if (!currentScene.value || !allScenes.find(s=>s.id===currentScene.value.id)) loadScene(allScenes[0].id);
      else { const fresh = allScenes.find(s=>s.id===currentScene.value.id); if(fresh) currentScene.value = fresh; }
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
    id: h.id, text: h.text, type: h.type, content: h.content, 
    target_scene_id: h.target_scene_id, position: [h.x, h.y, h.z],
    icon_type: h.icon_type, icon_url: h.icon_url, scale: h.scale, use_fixed_size: h.use_fixed_size
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
  containerRef.value.addEventListener('dblclick', onDoubleClick);

  animate();
  window.addEventListener('resize', onResize);
  window.addEventListener('click', closeMenu);
};

const getIconTexture = (hData) => {
  let url = '';
  if (hData.icon_type === 'system') {
    url = SYSTEM_ICONS[hData.icon_url] || SYSTEM_ICONS['arrow'];
  } else {
    url = getImageUrl(hData.icon_url);
  }
  if (!iconTextures[url]) iconTextures[url] = textureLoader.load(url);
  return iconTextures[url];
};

const rebuildHotspotMeshes = () => {
  hotspotMeshes.forEach(mesh => scene.remove(mesh));
  hotspotMeshes = [];
  hotspotList.value.forEach(hData => {
    const map = getIconTexture(hData);
    const mat = new THREE.SpriteMaterial({ map: map, transparent: true, depthTest: false, sizeAttenuation: !hData.use_fixed_size });
    const sprite = new THREE.Sprite(mat);
    sprite.position.set(...hData.position);
    const baseScale = hData.use_fixed_size ? 0.08 : 30.0;
    const finalScale = (hData.scale || 1.0) * baseScale;
    sprite.scale.set(finalScale, finalScale, 1);
    sprite.userData = { id: hData.id, isHotspot: true };
    sprite.renderOrder = 999;
    scene.add(sprite);
    hotspotMeshes.push(sprite);
    hData._mesh = sprite;
  });
};

const createHotspotAtCenter = async () => {
  const dist = 450; const vec = new THREE.Vector3(); camera.getWorldDirection(vec); vec.multiplyScalar(dist);
  const pos = [vec.x, vec.y, vec.z];
  try {
    const res = await authFetch('/hotspots/', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ 
        text: '', x:pos[0], y:pos[1], z:pos[2], 
        source_scene_id:currentScene.value.id, 
        icon_type: 'system', icon_url: 'arrow' 
      })
    });
    if(res.ok) {
      const s = await res.json();
      const hData = { id:s.id, text:'', type:'scene', position:pos, icon_type:'system', icon_url:'arrow', scale:1.0, use_fixed_size:false };
      hotspotList.value.push(hData); rebuildHotspotMeshes(); selectHotspotByList(hData);
    }
  } catch(e) { alert("创建失败"); }
};

const selectHotspotByList = (h) => { selectedHotspot.value = {...h}; hotspotMeshes.forEach(m=>m.material.opacity=0.4); if(h._mesh) h._mesh.material.opacity=1.0; };
const cancelHotspotSelection = () => { selectedHotspot.value = null; hotspotMeshes.forEach(m=>m.material.opacity=1.0); };
const saveSelectedHotspot = async (newData) => {
  try {
    const res = await authFetch(`/hotspots/${newData.id}`, {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify(newData)});
    if(res.ok) {
      const idx = hotspotList.value.findIndex(i=>i.id===newData.id);
      if(idx!==-1) hotspotList.value[idx] = { ...newData, _mesh: hotspotList.value[idx]._mesh };
      rebuildHotspotMeshes(); selectHotspotByList(hotspotList.value[idx]); alert("已保存");
    }
  } catch(e){alert("失败");}
};
const deleteSelectedHotspot = async (h) => {
  if(!confirm("删除?")) return;
  try { await authFetch(`/hotspots/${h.id}`, { method:'DELETE' }); hotspotList.value = hotspotList.value.filter(i=>i.id!==h.id); selectedHotspot.value=null; rebuildHotspotMeshes(); } catch(e){alert("失败");}
};
const batchDeleteHotspots = async (ids) => {
  try { await authFetch('/hotspots/batch_delete/', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(ids) }); hotspotList.value = hotspotList.value.filter(h=>!ids.includes(h.id)); selectedHotspot.value=null; rebuildHotspotMeshes(); } catch(e){alert("失败");}
};
const onViewportClick = (e) => {
  if (activeTab.value !== 'hotspot') return;
  const r = containerRef.value.getBoundingClientRect(); pointer.x = ((e.clientX - r.left) / r.width) * 2 - 1; pointer.y = -((e.clientY - r.top) / r.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const hits = raycaster.intersectObjects(hotspotMeshes);
  if (hits.length > 0) { const h = hotspotList.value.find(i => i._mesh === hits[0].object); if(h) selectHotspotByList(h); } else cancelHotspotSelection();
};
const onDoubleClick = (e) => {
  if (activeTab.value !== 'hotspot') return;
  const r = containerRef.value.getBoundingClientRect(); pointer.x = ((e.clientX - r.left) / r.width) * 2 - 1; pointer.y = -((e.clientY - r.top) / r.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera); const hits = raycaster.intersectObject(sphereMesh);
  if (hits.length > 0) { const p = hits[0].point.clone().normalize().multiplyScalar(450); addNewHotspot([p.x, p.y, p.z]); }
};
const addNewHotspot = async (pos) => {
  try {
    const res = await authFetch('/hotspots/', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ text:'', x:pos[0], y:pos[1], z:pos[2], source_scene_id:currentScene.value.id, icon_type:'system', icon_url:'arrow' }) });
    if(res.ok) { const s = await res.json(); const h={id:s.id,text:'',type:'scene',position:pos,icon_type:'system',icon_url:'arrow',scale:1.0,use_fixed_size:false}; hotspotList.value.push(h); rebuildHotspotMeshes(); selectHotspotByList(h); }
  } catch(e) {}
};

const switchTab = (tab) => { activeTab.value = tab; cancelHotspotSelection(); };
const switchScene = (id) => { if(isModified.value && !confirm("未保存将丢失"))return; loadScene(id); };

// [修复] 返回功能逻辑优化
const handleBack = () => {
  if (isModified.value) {
    const confirmLeave = confirm("您有未保存的修改，确定要离开吗？");
    if (!confirmLeave) return;
  }
  // 确保事件能够正确传递
  setTimeout(() => {
    emit('back');
  }, 0);
};

const saveAll = async () => { saving.value=true; try{ const p={...settings}; const r=await authFetch(`/scenes/${currentScene.value.id}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)}); if(r.ok){ originalSettingsJson.value=JSON.stringify(settings); } }catch(e){alert("Error");}finally{saving.value=false;} };
const resetToDefaults = () => { if(!confirm("恢复?"))return; Object.assign(settings, DEFAULT_SETTINGS); applyAllSettingsToThree(); };

const applyAllSettingsToThree = () => { if (!controls) return; camera.fov = settings.fov_default; camera.updateProjectionMatrix(); const az = settings.initial_heading * (Math.PI / 180); const pl = (settings.initial_pitch + 90) * (Math.PI / 180); const r = 0.1; camera.position.x = r * Math.sin(pl) * Math.sin(az); camera.position.y = r * Math.cos(pl); camera.position.z = r * Math.sin(pl) * Math.cos(az); controls.target.set(0,0,0); applyLimitsAndFOV(); controls.update(); };
const applyLimitsAndFOV = () => { if(!controls) return; camera.fov = settings.fov_default; camera.updateProjectionMatrix(); if (settings.limit_h_min <= -180 && settings.limit_h_max >= 180) { controls.minAzimuthAngle = -Infinity; controls.maxAzimuthAngle = Infinity; } else { controls.minAzimuthAngle = settings.limit_h_min * (Math.PI / 180); controls.maxAzimuthAngle = settings.limit_h_max * (Math.PI / 180); } controls.maxPolarAngle = (90 - settings.limit_v_min) * (Math.PI / 180); controls.minPolarAngle = (90 - settings.limit_v_max) * (Math.PI / 180); controls.update(); };
const onFovPreview = (val) => { camera.fov = val; camera.updateProjectionMatrix(); };
const onHLimitPreview = (val) => { const rad = val * (Math.PI / 180); controls.minAzimuthAngle = -Infinity; controls.maxAzimuthAngle = Infinity; const pl = controls.getPolarAngle(); const r = 0.1; camera.position.x = r * Math.sin(pl) * Math.sin(rad); camera.position.z = r * Math.sin(pl) * Math.cos(rad); controls.update(); };
const onVLimitPreview = (val) => { const rad = (90 - val) * (Math.PI / 180); controls.minPolarAngle = 0; controls.maxPolarAngle = Math.PI; const az = controls.getAzimuthalAngle(); const r = 0.1; camera.position.x = r * Math.sin(rad) * Math.sin(az); camera.position.y = r * Math.cos(rad); camera.position.z = r * Math.sin(rad) * Math.cos(az); controls.update(); };
const captureInitialState = () => { const az=controls.getAzimuthalAngle(); const pl=controls.getPolarAngle(); settings.initial_heading=az*(180/Math.PI); settings.initial_pitch=90-(pl*(180/Math.PI)); settings.fov_default=camera.fov; };
const captureCover = async () => { renderer.render(scene,camera); const d=renderer.domElement.toDataURL('image/jpeg',0.7); try{ const r1=await authFetch('/upload_base64/',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({image_data:d})}); const d1=await r1.json(); await authFetch(`/scenes/${currentScene.value.id}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({cover_url:d1.url})}); alert("封面已更新"); fetchProject(); }catch(e){} };
const onMouseWheel = (e) => { e.preventDefault(); let f=camera.fov+e.deltaY*0.05; f=Math.max(settings.fov_min, Math.min(settings.fov_max, f)); camera.fov=f; camera.updateProjectionMatrix(); };
const animate = () => { animationId=requestAnimationFrame(animate); controls.update(); renderer.render(scene,camera); };
const onResize = () => { if(containerRef.value){ camera.aspect=containerRef.value.clientWidth/containerRef.value.clientHeight; camera.updateProjectionMatrix(); renderer.setSize(containerRef.value.clientWidth,containerRef.value.clientHeight); } };
const onContextMenu = (e) => { e.preventDefault(); menuPos.value = {x:e.clientX, y:e.clientY}; menuVisible.value = true; };
const closeMenu = () => { menuVisible.value = false; }; 
const toggleDirection = () => { isReverse.value = !isReverse.value; controls.rotateSpeed = isReverse.value ? -0.5 : 0.5; };
const resetView = () => applyAllSettingsToThree();
const onBeforeUnload = (e) => { if (isModified.value) { e.preventDefault(); e.returnValue = ''; } };

onMounted(() => { fetchProject(); window.addEventListener('beforeunload', onBeforeUnload); });
onBeforeUnmount(() => { cancelAnimationFrame(animationId); window.removeEventListener('beforeunload', onBeforeUnload); window.removeEventListener('resize', onResize); window.removeEventListener('click', closeMenu); if(renderer) renderer.dispose(); });
</script>

<style scoped>
.editor-layout { display: flex; height: 100vh; background: #1a1a1a; color: #ccc; user-select: none; flex-direction: column; }

/* 1. 全局通栏 Header */
.global-header {
  height: 50px; background: #2d2d2d; border-bottom: 1px solid #111;
  display: flex; justify-content: space-between; align-items: center; padding: 0 20px; z-index: 100;
}
.header-left { display: flex; align-items: center; z-index: 2; gap: 15px; }
.back-btn { 
  background: none; border: none; color: #aaa; cursor: pointer; 
  display: flex; align-items: center; gap: 5px; font-size: 13px; padding: 0;
}
.back-btn:hover { color: white; }
.v-divider { width: 1px; height: 14px; background: #555; }
.scene-title { font-weight: bold; color: white; font-size: 15px; }
.modified-dot { color: #e74c3c; font-size: 20px; line-height: 1; margin-left: 5px; }
.header-right { display: flex; align-items: center; gap: 15px; z-index: 2; }

/* 2. 工作区 */
.workspace { flex: 1; display: flex; position: relative; overflow: hidden; }

/* 左侧工具栏 */
.left-toolbar { 
  width: 50px; background: #252526; border-right: 1px solid #111; 
  display: flex; flex-direction: column; align-items: center; padding-top: 15px; 
}
.tool-btn { 
  width: 40px; height: 40px; margin-bottom: 15px; 
  display: flex; flex-direction: column; align-items: center; justify-content: center; 
  cursor: pointer; color: #888; border-radius: 6px; transition: all 0.2s; 
}
.tool-btn:hover { background: #333; color: #fff; }
.tool-btn.active { background: #3498db; color: #fff; }
.tool-label { font-size: 10px; margin-top: 2px; }

/* 中间视窗 */
.viewport { flex: 1; position: relative; background: #000; padding-bottom: 140px; }
.three-container { width: 100%; height: 100%; }

/* 右侧面板 */
.right-sidebar { width: 320px; background: #252526; border-left: 1px solid #111; display: flex; flex-direction: column; }
.panel-header { height: 40px; line-height: 40px; padding: 0 15px; font-weight: bold; background: #2d2d2d; border-bottom: 1px solid #333; color: #eee; font-size: 13px; }

/* 其他样式 */
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