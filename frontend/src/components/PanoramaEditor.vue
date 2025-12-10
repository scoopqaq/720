<template>
  <div class="editor-layout">
    
    <div class="left-toolbar">
      <div 
        class="tool-btn" 
        :class="{ active: activeTab === 'view' }"
        @click="switchTab('view')"
        title="基础视角设置"
      >
        👁️
        <span class="tool-label">视角</span>
      </div>
      <div 
        class="tool-btn" 
        :class="{ active: activeTab === 'hotspot' }"
        @click="switchTab('hotspot')"
        title="热点编辑"
      >
        📍
        <span class="tool-label">热点</span>
      </div>
    </div>

    <div class="viewport">
      <div 
        ref="containerRef" 
        class="three-container" 
        @contextmenu.prevent="onContextMenu" 
        @pointerdown="onViewportClick" 
      ></div>
      
      <div class="viewport-header">
        <button class="back-btn" @click="handleBack">← 返回</button>
        <div class="scene-info" v-if="currentScene">
          <span class="scene-name">{{ currentScene.name }}</span>
          <span v-if="isModified" class="modified-dot" title="有未保存的修改">•</span>
        </div>
        <div class="header-actions">
          <button class="save-primary-btn" :class="{ 'has-changes': isModified }" @click="saveAll" :disabled="saving">
            {{ saving ? '保存中...' : (isModified ? '💾 保存*' : '💾 已保存') }}
          </button>
        </div>
      </div>
      
      <div v-if="activeTab === 'view'" class="center-cross">+</div>

      <div class="toast-tip" v-if="activeTab === 'hotspot'">
        提示：双击画面任意位置可添加新热点
      </div>

      <transition name="fade">
        <div 
          v-if="menuVisible" 
          class="context-menu" 
          :style="{ left: menuPos.x + 'px', top: menuPos.y + 'px' }"
        >
          <div class="item" @click="toggleDirection">
            ⇄ 拖拽方向: {{ isReverse ? '反向 (画面跟随)' : '正向 (相机跟随)' }}
          </div>
          <div class="item" @click="resetView">↺ 视角复位</div>
        </div>
      </transition>
    </div>

    <div class="sidebar">
      
      <template v-if="activeTab === 'view'">
        <div class="panel-header">基础视角设置</div>
        <div class="panel-body" v-if="currentScene">
           <div class="section-block">
              <h3>初始视角 & 封面</h3>
              <div class="action-grid">
                <button class="action-btn primary" @click="captureInitialState">📍 设为初始视角</button>
                <button class="action-btn" @click="captureCover">🖼️ 截取封面</button>
              </div>
              <div class="data-display">
                <div class="tag">H: {{ Math.round(settings.initial_heading) }}°</div>
                <div class="tag">V: {{ Math.round(settings.initial_pitch) }}°</div>
                <div class="tag">FOV: {{ Math.round(settings.fov_default) }}</div>
              </div>
           </div>
           <hr class="divider">
           <div class="section-block">
              <h3>FOV 设置</h3>
              <div class="control-row">
                <label>范围 ({{ settings.fov_min }} - {{ settings.fov_max }})</label>
                <DualSlider :min="10" :max="140" v-model="fovRange" @change="onFovRangeChange" @preview="onFovPreview" />
              </div>
              <div class="control-row">
                <label>默认: {{ Math.round(settings.fov_default) }}</label>
                <input type="range" :min="settings.fov_min" :max="settings.fov_max" v-model.number="settings.fov_default" @input="updateCameraFOV">
              </div>
           </div>
           <hr class="divider">
           <div class="section-block">
              <h3>视角限制</h3>
              <div class="control-row">
                <div class="label-row">
                  <label>水平限制</label>
                  <span class="status-tag" v-if="isFullHorizontal">360° 无限</span>
                </div>
                <DualSlider :min="-180" :max="180" v-model="hLimitRange" @change="onHLimitChange" @preview="onHLimitPreview" />
              </div>
              <div class="control-row">
                <label>垂直限制</label>
                <DualSlider :min="-90" :max="90" v-model="vLimitRange" @change="onVLimitChange" @preview="onVLimitPreview" />
                <div class="val-display">{{ settings.limit_v_min }}°(底) ~ {{ settings.limit_v_max }}°(顶)</div>
              </div>
           </div>
        </div>
      </template>

      <template v-if="activeTab === 'hotspot'">
        <div class="panel-header">热点编辑</div>
        <div class="panel-body">
          <div v-if="selectedHotspot" class="hotspot-form">
            <div class="section-block">
              <h3>编辑热点</h3>
              <div class="form-group">
                <label>显示标题</label>
                <input type="text" v-model="selectedHotspot.text" class="form-input">
              </div>
              <div class="form-group">
                <label>跳转目标</label>
                <select v-model="selectedHotspot.target_scene_id" class="form-select">
                  <option disabled value="">请选择...</option>
                  <option v-for="s in otherScenes" :key="s.id" :value="s.id">{{ s.name }}</option>
                </select>
              </div>
              <div class="btn-row">
                <button class="btn-danger" @click="deleteSelectedHotspot">删除</button>
                <button class="btn-primary" @click="saveSelectedHotspot">保存</button>
              </div>
            </div>
          </div>
          <div v-else class="empty-tip">
            <p>👋 操作指南：</p>
            <ul>
              <li><strong>双击画面</strong>：添加热点</li>
              <li><strong>点击红球</strong>：编辑热点</li>
            </ul>
            <hr class="divider">
            <div class="hotspot-list">
              <h4>热点列表 ({{ hotspotList.length }})</h4>
              <div v-for="h in hotspotList" :key="h.id" class="hotspot-item" @click="selectHotspotByList(h)">
                <span class="icon">📍</span> <span class="name">{{ h.text }}</span>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <SceneManager 
      v-if="projectData"
      ref="sceneManagerRef"
      :projectData="projectData"
      :currentSceneId="currentScene ? currentScene.id : null"
      @change-scene="switchScene"
      @refresh-data="fetchProject"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch } from 'vue';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import DualSlider from './DualSlider.vue';
import SceneManager from './SceneManager.vue';

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

const DEFAULT_SETTINGS = {
  initial_heading: 0, initial_pitch: 0,
  fov_min: 70, fov_max: 120, fov_default: 95,
  limit_h_min: -180, limit_h_max: 180,
  limit_v_min: -90, limit_v_max: 90,
};
const settings = reactive({ ...DEFAULT_SETTINGS });
// 原始设置 Json (用于脏检查)
const originalSettingsJson = ref(JSON.stringify(DEFAULT_SETTINGS));
const isModified = computed(() => JSON.stringify(settings) !== originalSettingsJson.value);

// 热点状态
const hotspotList = ref([]);
const selectedHotspot = ref(null);

// Three.js
let scene, camera, renderer, controls, sphereMesh, textureLoader, raycaster, pointer;
let hotspotMeshes = [];
let animationId;

// [修复] 菜单与方向状态
const menuVisible = ref(false);
const menuPos = ref({ x: 0, y: 0 });
const isReverse = ref(false); // 拖拽方向

// Computed
const fovRange = computed({ get: () => [settings.fov_min, settings.fov_max], set: (v) => { settings.fov_min = v[0]; settings.fov_max = v[1]; } });
const hLimitRange = computed({ get: () => [settings.limit_h_min, settings.limit_h_max], set: (v) => { settings.limit_h_min = v[0]; settings.limit_h_max = v[1]; } });
const vLimitRange = computed({ get: () => [settings.limit_v_min, settings.limit_v_max], set: (v) => { settings.limit_v_min = v[0]; settings.limit_v_max = v[1]; } });
const isFullHorizontal = computed(() => settings.limit_h_min <= -180 && settings.limit_h_max >= 180);
const otherScenes = computed(() => currentScene.value ? scenes.value.filter(s => s.id !== currentScene.value.id) : []);

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
      if (!currentScene.value) loadScene(allScenes[0].id);
      else {
        const fresh = allScenes.find(s => s.id === currentScene.value.id);
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
  originalSettingsJson.value = JSON.stringify(settings); // 更新基准

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
  // [修复] 初始化应用方向
  controls.rotateSpeed = isReverse.value ? -0.5 : 0.5;

  raycaster = new THREE.Raycaster();
  pointer = new THREE.Vector2();

  containerRef.value.addEventListener('wheel', onMouseWheel, { passive: false });
  containerRef.value.addEventListener('dblclick', onDoubleClick);

  animate();
  window.addEventListener('resize', onResize);
  // [修复] 全局点击关闭菜单
  window.addEventListener('click', closeMenu);
};

// --- Settings Logic ---
const applyAllSettingsToThree = () => {
  if (!controls) return;
  camera.fov = settings.fov_default;
  camera.updateProjectionMatrix();
  const azimuth = settings.initial_heading * (Math.PI / 180);
  const polar = (90 - settings.initial_pitch) * (Math.PI / 180); // 90-UI = Three Polar
  const r = 0.1;
  camera.position.x = r * Math.sin(polar) * Math.sin(azimuth);
  camera.position.y = r * Math.cos(polar);
  camera.position.z = r * Math.sin(polar) * Math.cos(azimuth);
  controls.target.set(0,0,0);
  applyLimits();
  controls.update();
};

const applyLimits = () => {
  if (!controls) return;
  if (settings.limit_h_min <= -180 && settings.limit_h_max >= 180) {
    controls.minAzimuthAngle = -Infinity; controls.maxAzimuthAngle = Infinity;
  } else {
    controls.minAzimuthAngle = settings.limit_h_min * (Math.PI / 180);
    controls.maxAzimuthAngle = settings.limit_h_max * (Math.PI / 180);
  }
  // Min(UI left) -> Bottom(Three Max)
  controls.maxPolarAngle = (90 - settings.limit_v_min) * (Math.PI / 180);
  // Max(UI right) -> Top(Three Min)
  controls.minPolarAngle = (90 - settings.limit_v_max) * (Math.PI / 180);
  controls.update();
};

// --- Hotspots ---
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
    if (hData) selectHotspot(hData);
  } else {
    selectedHotspot.value = null; highlightHotspot(null);
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
      hotspotList.value.push(hData); selectHotspot(hData);
    }
  } catch(e){alert("添加失败");}
};
const selectHotspot = (h) => { selectedHotspot.value = { ...h }; highlightHotspot(h._mesh); };
const selectHotspotByList = (h) => selectHotspot(h);
const highlightHotspot = (mesh) => { hotspotMeshes.forEach(m => m.material.color.set(0xff0000)); if(mesh) mesh.material.color.set(0x00ff00); };
const saveSelectedHotspot = async () => {
  if(!selectedHotspot.value) return;
  const h = selectedHotspot.value;
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
const deleteSelectedHotspot = async () => {
  if(!selectedHotspot.value || !confirm("删除热点?")) return;
  const id = selectedHotspot.value.id;
  try {
    await fetch(`http://127.0.0.1:8000/hotspots/${id}`, { method:'DELETE' });
    const mesh = hotspotMeshes.find(m=>m.userData.id===id);
    if(mesh) { scene.remove(mesh); mesh.geometry.dispose(); mesh.material.dispose(); hotspotMeshes=hotspotMeshes.filter(m=>m!==mesh); }
    hotspotList.value = hotspotList.value.filter(h=>h.id!==id);
    selectedHotspot.value = null;
  } catch(e){alert("失败");}
};

// --- 菜单与交互 ---
// [修复] 右键菜单逻辑
const onContextMenu = (e) => {
  menuPos.value = { x: e.clientX, y: e.clientY };
  menuVisible.value = true;
};
const closeMenu = () => menuVisible.value = false;

// [修复] 切换拖拽方向
const toggleDirection = () => {
  isReverse.value = !isReverse.value;
  const speed = 0.5;
  controls.rotateSpeed = isReverse.value ? -speed : speed;
};
const resetView = () => applyAllSettingsToThree();

const switchTab = (tab) => { activeTab.value = tab; selectedHotspot.value=null; highlightHotspot(null); };
const switchScene = (id) => { if(isModified.value && !confirm("未保存将丢失"))return; loadScene(id); };
const handleBack = () => { if(isModified.value && !confirm("有未保存修改，离开？"))return; emit('back'); };

// ... 其他辅助函数 ...
const captureInitialState = () => { 
  const az=controls.getAzimuthalAngle(); const pl=controls.getPolarAngle();
  settings.initial_heading=az*(180/Math.PI); settings.initial_pitch=90-(pl*(180/Math.PI)); settings.fov_default=camera.fov; 
};
const captureCover = async () => { renderer.render(scene,camera); const d=renderer.domElement.toDataURL('image/jpeg',0.7); try{ const r1=await fetch('http://127.0.0.1:8000/upload_base64/',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({image_data:d})}); const d1=await r1.json(); await fetch(`http://127.0.0.1:8000/scenes/${currentScene.value.id}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({cover_url:d1.url})}); alert("封面已更新"); fetchProject(); }catch(e){} };
const saveAll = async () => { saving.value=true; try{ const p={...settings}; const r=await fetch(`http://127.0.0.1:8000/scenes/${currentScene.value.id}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)}); if(r.ok){ originalSettingsJson.value=JSON.stringify(settings); } }catch(e){alert("Error");}finally{saving.value=false;} };
const resetToDefaults = () => { if(!confirm("恢复?"))return; Object.assign(settings, DEFAULT_SETTINGS); applyAllSettingsToThree(); };
const updateCameraFOV = () => { if(camera){ camera.fov=settings.fov_default; camera.updateProjectionMatrix(); } };
const onFovRangeChange = () => { if(settings.fov_default<settings.fov_min)settings.fov_default=settings.fov_min; if(settings.fov_default>settings.fov_max)settings.fov_default=settings.fov_max; updateCameraFOV(); };
const onFovPreview = ({value}) => { camera.fov=value; camera.updateProjectionMatrix(); };
const onHLimitChange = () => applyLimits();
const onHLimitPreview = ({value}) => { const rad=value*(Math.PI/180); controls.minAzimuthAngle=-Infinity; controls.maxAzimuthAngle=Infinity; const pl=controls.getPolarAngle(); const r=0.1; camera.position.x=r*Math.sin(pl)*Math.sin(rad); camera.position.z=r*Math.sin(pl)*Math.cos(rad); controls.update(); };
const onVLimitChange = () => applyLimits();
const onVLimitPreview = ({value}) => { const rad=(90-value)*(Math.PI/180); controls.minPolarAngle=0; controls.maxPolarAngle=Math.PI; const az=controls.getAzimuthalAngle(); const r=0.1; camera.position.x=r*Math.sin(rad)*Math.sin(az); camera.position.y=r*Math.cos(rad); camera.position.z=r*Math.sin(rad)*Math.cos(az); controls.update(); };
const onMouseWheel = (e) => { e.preventDefault(); let f=camera.fov+e.deltaY*0.05; f=Math.max(settings.fov_min, Math.min(settings.fov_max, f)); camera.fov=f; camera.updateProjectionMatrix(); };
const animate = () => { animationId=requestAnimationFrame(animate); controls.update(); renderer.render(scene,camera); };
const onResize = () => { if(containerRef.value){ camera.aspect=containerRef.value.clientWidth/containerRef.value.clientHeight; camera.updateProjectionMatrix(); renderer.setSize(containerRef.value.clientWidth,containerRef.value.clientHeight); } };

// [修复] 浏览器关闭拦截
const onBeforeUnload = (e) => { if (isModified.value) { e.preventDefault(); e.returnValue = ''; } };

onMounted(() => { fetchProject(); window.addEventListener('beforeunload', onBeforeUnload); });
onBeforeUnmount(() => { cancelAnimationFrame(animationId); window.removeEventListener('beforeunload', onBeforeUnload); window.removeEventListener('resize', onResize); window.removeEventListener('click', closeMenu); if(renderer) renderer.dispose(); });
</script>

<style scoped>
/* 样式复用之前的，确保包含 .context-menu */
.editor-layout { display: flex; height: 100vh; background: #1a1a1a; color: #ccc; user-select: none; }
.left-toolbar { width: 50px; background: #222; border-right: 1px solid #333; display: flex; flex-direction: column; align-items: center; padding-top: 10px; }
.tool-btn { width: 40px; height: 40px; margin-bottom: 10px; border-radius: 6px; display: flex; flex-direction: column; align-items: center; justify-content: center; cursor: pointer; color: #888; font-size: 18px; transition: all 0.2s; }
.tool-btn:hover { background: #333; color: #fff; }
.tool-btn.active { background: #3498db; color: #fff; }
.tool-label { font-size: 10px; margin-top: 2px; }
.viewport { flex: 1; position: relative; background: #000; padding-bottom: 140px; }
.three-container { width: 100%; height: 100%; }
.viewport-header { position: absolute; top: 0; left: 0; right: 0; height: 50px; background: rgba(30,30,30,0.9); border-bottom: 1px solid #333; display: flex; justify-content: space-between; align-items: center; padding: 0 20px; z-index: 10; }
.back-btn, .btn-text { background: none; border: none; color: #aaa; cursor: pointer; font-size: 13px; }
.save-primary-btn { background: #333; color: #888; border: 1px solid #444; padding: 6px 16px; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 13px; transition: all 0.3s; }
.save-primary-btn.has-changes { background: #e67e22; color: white; border-color: #d35400; }
.scene-name { font-weight: bold; color: white; margin-right: 10px; }
.modified-dot { color: #e74c3c; font-size: 20px; line-height: 1; }
.center-cross { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: rgba(255,255,255,0.3); font-size: 20px; pointer-events: none; }
.toast-tip { position: absolute; top: 60px; left: 50%; transform: translateX(-50%); background: rgba(0,0,0,0.6); color: white; padding: 5px 15px; border-radius: 20px; font-size: 12px; pointer-events: none; }
.sidebar { width: 340px; background: #252526; border-left: 1px solid #333; display: flex; flex-direction: column; }
.panel-header { height: 50px; line-height: 50px; padding: 0 20px; font-weight: bold; background: #2d2d2d; border-bottom: 1px solid #333; color: #eee; }
.panel-body { flex: 1; padding: 20px; overflow-y: auto; }
.section-block { margin-bottom: 25px; }
.section-block h3 { font-size: 13px; color: #3498db; margin: 0 0 8px 0; font-weight: bold; }
.desc { font-size: 12px; color: #777; margin-bottom: 12px; }
.action-grid { display: flex; gap: 10px; margin-bottom: 10px; }
.action-btn { flex: 1; padding: 8px; border: 1px solid #444; background: #333; color: #ccc; border-radius: 4px; cursor: pointer; font-size: 12px; }
.action-btn.primary { border-color: #3498db; color: #3498db; background: rgba(52,152,219,0.15); }
.data-display { display: flex; justify-content: space-between; background: #1e1e1e; padding: 6px 10px; border-radius: 4px; }
.tag { font-size: 11px; color: #f1c40f; font-family: monospace; }
.divider { border: 0; border-top: 1px solid #333; margin: 20px 0; }
.control-row { margin-bottom: 20px; }
.label-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.control-row label { font-size: 12px; color: #aaa; }
.status-tag { font-size: 10px; background: #27ae60; color: white; padding: 1px 4px; border-radius: 2px; }
.val-display { text-align: center; font-size: 11px; color: #f1c40f; margin-top: 5px; }
input[type=range] { width: 100%; cursor: pointer; }
.form-group { margin-bottom: 15px; }
.form-group label { display: block; font-size: 12px; margin-bottom: 5px; color: #aaa; }
.form-input, .form-select { width: 100%; padding: 8px; background: #333; border: 1px solid #444; color: white; border-radius: 4px; outline: none; }
.form-input:focus { border-color: #3498db; }
.btn-row { display: flex; gap: 10px; margin-top: 20px; }
.btn-danger { flex: 1; padding: 8px; background: #c0392b; border: none; color: white; border-radius: 4px; cursor: pointer; }
.btn-primary { flex: 1; padding: 8px; background: #3498db; border: none; color: white; border-radius: 4px; cursor: pointer; }
.hotspot-list { margin-top: 20px; }
.hotspot-list h4 { font-size: 12px; color: #888; margin-bottom: 10px; }
.hotspot-item { display: flex; align-items: center; gap: 10px; padding: 8px; background: #333; border-radius: 4px; margin-bottom: 5px; cursor: pointer; }
.hotspot-item:hover { background: #444; }
.empty-tip { color: #888; font-size: 13px; line-height: 1.6; }
.empty-tip ul { padding-left: 20px; }
.context-menu { position: fixed; z-index: 9999; background: #333; border: 1px solid #444; border-radius: 4px; padding: 5px 0; min-width: 160px; }
.context-menu .item { padding: 8px 15px; font-size: 13px; color: #ddd; cursor: pointer; }
.context-menu .item:hover { background: #444; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>