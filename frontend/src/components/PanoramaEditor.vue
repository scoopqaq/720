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
          @pointerdown="onPointerDown" 
          @pointermove="onPointerMove"
          @pointerup="onPointerUp"
        ></div>
        
        <div v-if="activeTab === 'view'" class="center-cross">+</div>

        <div class="toast-tip" v-if="activeTab === 'hotspot'">
          提示：点击右侧“添加”按钮创建热点，按住热点可拖动
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
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch } from 'vue';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import SceneManager from './SceneManager.vue';
import PanelBasic from './editor/PanelBasic.vue';
import PanelHotspot from './editor/PanelHotspot.vue';
import { authFetch, getImageUrl } from '../utils/api';

const props = defineProps(['projectId']);
const emit = defineEmits(['back']);

// 纹理缓存
const iconTextures = {}; 

// State
const activeTab = ref('view');
const projectData = ref(null);
const scenes = ref([]);
const currentScene = ref(null);
const containerRef = ref(null);
const sceneManagerRef = ref(null);
const saving = ref(false);
const availableIcons = ref([]);

const DEFAULT_SETTINGS = { initial_heading: 0, initial_pitch: 0, fov_min: 70, fov_max: 120, fov_default: 95, limit_h_min: -180, limit_h_max: 180, limit_v_min: -90, limit_v_max: 90 };
const settings = reactive({ ...DEFAULT_SETTINGS });
const originalSettingsJson = ref(JSON.stringify(DEFAULT_SETTINGS));
const isModified = computed(() => JSON.stringify(settings) !== originalSettingsJson.value);

const hotspotList = ref([]);
const selectedHotspot = ref(null);
const otherScenes = computed(() => currentScene.value ? scenes.value.filter(s => s.id !== currentScene.value.id) : []);

let scene, camera, renderer, controls, sphereMesh, textureLoader, raycaster, pointer;
let hotspotMeshes = [];
let animationId;
const menuVisible = ref(false);
const menuPos = ref({ x: 0, y: 0 });
const isReverse = ref(false);

const isDraggingHotspot = ref(false);
const draggedMesh = ref(null);

const fetchIcons = async () => {
  try {
    const res = await authFetch('/icons/');
    if (res.ok) {
      availableIcons.value = await res.json();
    }
  } catch (e) {
    console.error("加载图标失败", e);
  }
};

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

// [新增] 定义关闭菜单函数 (修复 ReferenceError)
const closeMenu = () => {
  menuVisible.value = false;
};

const initThree = () => {
  const w = containerRef.value.clientWidth;
  const h = containerRef.value.clientHeight;
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(settings.fov_default, w/h, 0.1, 1000);
  camera.position.set(0,0,0.1);
  
  renderer = new THREE.WebGLRenderer({ antialias: false, preserveDrawingBuffer: true });
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
  animate();
  window.addEventListener('resize', onResize);
  
  // [修改] 使用定义好的 closeMenu 函数
  window.addEventListener('click', closeMenu);
};

const getIconTexture = (hData) => {
  let url = '';
  if (hData.icon_url) {
    url = getImageUrl(hData.icon_url);
  } else {
    const defaultIcon = availableIcons.value.find(i => i.category === 'system');
    if (defaultIcon) {
        url = getImageUrl(defaultIcon.url);
    } else {
        return { isError: true }; 
    }
  }

  if (!iconTextures[url]) {
    iconTextures[url] = textureLoader.load(
      url, 
      undefined, 
      undefined, 
      (err) => { 
        console.warn('图标加载失败:', url);
        iconTextures[url].isError = true; 
      }
    );
  }
  return iconTextures[url];
};

const rebuildHotspotMeshes = () => {
  hotspotMeshes.forEach(mesh => scene.remove(mesh));
  hotspotMeshes = [];
  hotspotList.value.forEach(hData => {
    let texture = getIconTexture(hData);
    const matParams = { 
      transparent: true, 
      depthTest: false, 
      sizeAttenuation: !hData.use_fixed_size 
    };
    
    if (texture.isError) {
      matParams.color = 0xff0000; 
    } else {
      matParams.map = texture;
    }

    const mat = new THREE.SpriteMaterial(matParams);
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
  
  const defaultSysIcon = availableIcons.value.find(i => i.category === 'system');
  const defaultUrl = defaultSysIcon ? defaultSysIcon.url : '';

  try {
    const res = await authFetch('/hotspots/', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ 
        text: '', x:pos[0], y:pos[1], z:pos[2], 
        source_scene_id:currentScene.value.id, 
        icon_type: 'system', 
        icon_url: defaultUrl 
      })
    });
    if(res.ok) {
      const s = await res.json();
      const hData = { 
        id:s.id, text:'', type:'scene', 
        position:pos, icon_type:'system', 
        icon_url: s.icon_url, 
        scale:1.0, use_fixed_size:false 
      };
      hotspotList.value.push(hData);
      rebuildHotspotMeshes();
      selectHotspotByList(hData);
    }
  } catch(e) { alert("创建失败，请检查后端是否已初始化系统图标"); }
};

const onPointerDown = (event) => {
  if (activeTab.value !== 'hotspot') return;
  const rect = containerRef.value.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const intersects = raycaster.intersectObjects(hotspotMeshes);

  if (intersects.length > 0) {
    const hit = intersects[0].object;
    const hData = hotspotList.value.find(h => h._mesh === hit);
    if (hData) {
      selectHotspotByList(hData);
      isDraggingHotspot.value = true;
      draggedMesh.value = hit;
      controls.enabled = false;
    }
  } else {
    cancelHotspotSelection();
  }
};

const onPointerMove = (event) => {
  if (!isDraggingHotspot.value || !draggedMesh.value) return;
  const rect = containerRef.value.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const intersects = raycaster.intersectObject(sphereMesh);
  
  if (intersects.length > 0) {
    const targetPos = intersects[0].point.clone().normalize().multiplyScalar(450);
    draggedMesh.value.position.copy(targetPos);
    if (selectedHotspot.value) {
      selectedHotspot.value.position = [targetPos.x, targetPos.y, targetPos.z];
      const listData = hotspotList.value.find(h => h.id === selectedHotspot.value.id);
      if(listData) listData.position = [targetPos.x, targetPos.y, targetPos.z];
    }
  }
};

const onPointerUp = () => {
  if (isDraggingHotspot.value) {
    isDraggingHotspot.value = false;
    draggedMesh.value = null;
    controls.enabled = true;
    if (selectedHotspot.value) saveSelectedHotspot(selectedHotspot.value, true);
  }
};

const selectHotspotByList = (h) => { selectedHotspot.value = {...h}; hotspotMeshes.forEach(m=>m.material.opacity=0.4); if(h._mesh) h._mesh.material.opacity=1.0; };
const cancelHotspotSelection = () => { selectedHotspot.value = null; hotspotMeshes.forEach(m=>m.material.opacity=1.0); };
const saveSelectedHotspot = async (newData, silent = false) => {
  try {
    const res = await authFetch(`/hotspots/${newData.id}`, {
      method: 'PUT', headers: {'Content-Type':'application/json'}, 
      body: JSON.stringify({ 
        text: newData.text, target_scene_id: newData.target_scene_id,
        x: newData.position[0], y: newData.position[1], z: newData.position[2],
        icon_type: newData.icon_type, icon_url: newData.icon_url,
        scale: newData.scale, use_fixed_size: newData.use_fixed_size
      })
    });
    if(res.ok) {
      const idx = hotspotList.value.findIndex(i=>i.id===newData.id);
      if(idx!==-1) hotspotList.value[idx] = { ...newData, _mesh: hotspotList.value[idx]._mesh };
      rebuildHotspotMeshes(); selectHotspotByList(hotspotList.value[idx]);
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
  if (!controls) return;
  camera.fov = settings.fov_default;
  camera.updateProjectionMatrix();

  // ... 水平限制代码保持不变 ...
  if (settings.limit_h_min <= -180 && settings.limit_h_max >= 180) {
    controls.minAzimuthAngle = -Infinity;
    controls.maxAzimuthAngle = Infinity;
  } else {
    controls.minAzimuthAngle = settings.limit_h_min * (Math.PI / 180);
    controls.maxAzimuthAngle = settings.limit_h_max * (Math.PI / 180);
  }

  // [垂直限制修正] 
  // PanelBasic 传来的 settings.limit_v_max 是 "(顶)" (例如 90)，对应 Three.js 的 minPolarAngle (0)
  // PanelBasic 传来的 settings.limit_v_min 是 "(底)" (例如 -90)，对应 Three.js 的 maxPolarAngle (PI)
  
  // 顶 (Looking Up): 90 - 90 = 0 (ThreeJS Top)
  controls.minPolarAngle = Math.max(0, (90 - settings.limit_v_max) * (Math.PI / 180));
  
  // 底 (Looking Down): 90 - (-90) = 180 (ThreeJS Bottom)
  controls.maxPolarAngle = Math.min(Math.PI, (90 - settings.limit_v_min) * (Math.PI / 180));

  controls.update();
};
const onFovPreview = (val) => { camera.fov = val; camera.updateProjectionMatrix(); };
const onHLimitPreview = (val) => { const rad = val * (Math.PI / 180); controls.minAzimuthAngle = -Infinity; controls.maxAzimuthAngle = Infinity; const pl = controls.getPolarAngle(); const r = 0.1; camera.position.x = r * Math.sin(pl) * Math.sin(rad); camera.position.z = r * Math.sin(pl) * Math.cos(rad); controls.update(); };
const onVLimitPreview = (val) => { const rad = (90 - val) * (Math.PI / 180); controls.minPolarAngle = 0; controls.maxPolarAngle = Math.PI; const az = controls.getAzimuthalAngle(); const r = 0.1; camera.position.x = r * Math.sin(rad) * Math.sin(az); camera.position.y = r * Math.cos(rad); camera.position.z = r * Math.sin(rad) * Math.cos(az); controls.update(); };
const captureInitialState = () => { const az=controls.getAzimuthalAngle(); const pl=controls.getPolarAngle(); settings.initial_heading=az*(180/Math.PI); settings.initial_pitch=90-(pl*(180/Math.PI)); settings.fov_default=camera.fov; };
const captureCover = async () => { renderer.render(scene,camera); const d=renderer.domElement.toDataURL('image/jpeg',0.7); try{ const r1=await authFetch('/upload_base64/',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({image_data:d})}); const d1=await r1.json(); await authFetch(`/scenes/${currentScene.value.id}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({cover_url:d1.url})}); alert("封面已更新"); fetchProject(); }catch(e){} };
const onMouseWheel = (e) => { e.preventDefault(); let f=camera.fov+e.deltaY*0.05; f=Math.max(settings.fov_min, Math.min(settings.fov_max, f)); camera.fov=f; camera.updateProjectionMatrix(); };
const animate = () => { animationId=requestAnimationFrame(animate); controls.update(); renderer.render(scene,camera); };
const onResize = () => { if(containerRef.value){ camera.aspect=containerRef.value.clientWidth/containerRef.value.clientHeight; camera.updateProjectionMatrix(); renderer.setSize(containerRef.value.clientWidth,containerRef.value.clientHeight); } };
const onContextMenu = (e) => { e.preventDefault(); menuPos.value = {x:e.clientX, y:e.clientY}; menuVisible.value = true; };
const toggleDirection = () => { isReverse.value = !isReverse.value; controls.rotateSpeed = isReverse.value ? -0.5 : 0.5; };
const resetView = () => applyAllSettingsToThree();
const onBeforeUnload = (e) => { if (isModified.value) { e.preventDefault(); e.returnValue = ''; } };

onMounted(() => { 
  fetchIcons(); 
  fetchProject(); 
  window.addEventListener('beforeunload', onBeforeUnload); 
});
onBeforeUnmount(() => { 
  cancelAnimationFrame(animationId); 
  window.removeEventListener('beforeunload', onBeforeUnload); 
  window.removeEventListener('resize', onResize); 
  // [修复] 正确移除事件监听
  window.removeEventListener('click', closeMenu); 
  if(renderer) renderer.dispose(); 
});
</script>

<style scoped>
/* 样式保持不变 */
.editor-layout { display: flex; height: 100vh; background: #1a1a1a; color: #ccc; user-select: none; flex-direction: column; }
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