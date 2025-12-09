<template>
  <div class="editor-layout">
    <div class="viewport">
      <div ref="containerRef" class="three-container" @contextmenu.prevent="onContextMenu"></div>
      <div class="viewport-header">
        <button class="back-btn" @click="$emit('back')">← 返回列表</button>
        <div class="scene-info" v-if="currentScene"><span class="scene-name">{{ currentScene.name }}</span></div>
        <div class="header-actions">
          <button class="btn-text" @click="resetToDefaults">↺ 恢复默认</button>
          <button class="save-primary-btn" @click="saveAll" :disabled="saving">{{ saving ? '保存中...' : '💾 保存' }}</button>
        </div>
      </div>
      <div class="center-cross">+</div>
      <transition name="fade">
        <div v-if="menuVisible" class="context-menu" :style="{ left: menuPos.x + 'px', top: menuPos.y + 'px' }">
          <div class="item" @click="toggleDirection">⇄ 拖拽方向: {{ isReverse ? '反向' : '正向' }}</div>
          <div class="item" @click="resetView">↺ 视角复位</div>
        </div>
      </transition>
    </div>

    <div class="sidebar">
      <div class="panel-header">全景参数配置</div>
      <div class="panel-body" v-if="currentScene">
        <div class="section-block">
          <h3>1. 初始视角 & 封面</h3>
          <p class="desc">调整画面到最佳角度，点击下方按钮记录。</p>
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
          <h3>2. 缩放范围 (FOV)</h3>
          <div class="control-row">
            <label>范围 ({{ settings.fov_min }} - {{ settings.fov_max }})</label>
            <DualSlider :min="10" :max="140" v-model="fovRange" @change="onFovRangeChange" @preview="onFovPreview" />
          </div>
          <div class="control-row">
            <label>默认 FOV ({{ Math.round(settings.fov_default) }})</label>
            <input type="range" :min="settings.fov_min" :max="settings.fov_max" v-model.number="settings.fov_default" @input="updateCameraFOV">
          </div>
        </div>
        <hr class="divider">
        <div class="section-block">
          <h3>3. 视角旋转限制</h3>
          <div class="control-row">
            <div class="label-row"><label>水平限制</label><span class="status-tag" v-if="isFullHorizontal">360° 无限</span></div>
            <DualSlider :min="-180" :max="180" v-model="hLimitRange" @change="onHLimitChange" @preview="onHLimitPreview" />
            <div class="val-display">{{ settings.limit_h_min }}° ~ {{ settings.limit_h_max }}°</div>
          </div>
          <div class="control-row">
            <label>垂直限制</label>
            <DualSlider :min="-90" :max="90" v-model="vLimitRange" @change="onVLimitChange" @preview="onVLimitPreview" />
            <div class="val-display">{{ settings.limit_v_min }}° (底) ~ {{ settings.limit_v_max }}° (顶)</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import DualSlider from './DualSlider.vue';

const props = defineProps(['projectId']);
const emit = defineEmits(['back']);

const scenes = ref([]);
const currentScene = ref(null);
const containerRef = ref(null);
const saving = ref(false);

const DEFAULT_SETTINGS = {
  initial_heading: 0,
  initial_pitch: 0,
  fov_min: 70,
  fov_max: 120,
  fov_default: 95,
  limit_h_min: -180,
  limit_h_max: 180,
  limit_v_min: -90,
  limit_v_max: 90,
};

const settings = reactive({ ...DEFAULT_SETTINGS });

// Computed 绑定
const fovRange = computed({
  get: () => [settings.fov_min, settings.fov_max],
  set: (val) => { settings.fov_min = val[0]; settings.fov_max = val[1]; }
});
const hLimitRange = computed({
  get: () => [settings.limit_h_min, settings.limit_h_max],
  set: (val) => { settings.limit_h_min = val[0]; settings.limit_h_max = val[1]; }
});
const vLimitRange = computed({
  get: () => [settings.limit_v_min, settings.limit_v_max],
  set: (val) => { settings.limit_v_min = val[0]; settings.limit_v_max = val[1]; }
});
const isFullHorizontal = computed(() => settings.limit_h_min <= -180 && settings.limit_h_max >= 180);

let scene, camera, renderer, controls, sphereMesh, textureLoader, animationId;
const menuVisible = ref(false);
const menuPos = ref({ x: 0, y: 0 });
const isReverse = ref(false);

const fetchProject = async () => {
  try {
    const res = await fetch(`http://127.0.0.1:8000/projects/${props.projectId}`);
    const data = await res.json();
    scenes.value = data.scenes || [];
    if (scenes.value.length > 0) loadScene(scenes.value[0].id);
  } catch(e) { console.error(e); }
};

const loadScene = (sceneId) => {
  const target = scenes.value.find(s => s.id == sceneId);
  if (!target) return;
  currentScene.value = target;
  
  // 合并数据
  Object.keys(DEFAULT_SETTINGS).forEach(key => {
    settings[key] = target[key] ?? DEFAULT_SETTINGS[key];
  });

  if (!renderer) initThree();

  textureLoader.load(
    `http://127.0.0.1:8000${target.image_url}?t=${Date.now()}`,
    (tex) => {
      tex.colorSpace = THREE.SRGBColorSpace;
      sphereMesh.material.map = tex;
      sphereMesh.material.needsUpdate = true;
      controls.reset();
      applyAllSettingsToThree();
    }
  );
};

const initThree = () => {
  const width = containerRef.value.clientWidth;
  const height = containerRef.value.clientHeight;
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(settings.fov_default, width / height, 0.1, 1000);
  camera.position.set(0, 0, 0.1);
  renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setSize(width, height);
  containerRef.value.appendChild(renderer.domElement);
  
  const geo = new THREE.SphereGeometry(500, 60, 40);
  geo.scale(-1, 1, 1);
  sphereMesh = new THREE.Mesh(geo, new THREE.MeshBasicMaterial());
  sphereMesh.rotation.y = -Math.PI / 2; // 基础修正
  scene.add(sphereMesh);

  textureLoader = new THREE.TextureLoader();
  textureLoader.setCrossOrigin('anonymous');
  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.enableZoom = false; 
  controls.rotateSpeed = 0.5;

  containerRef.value.addEventListener('wheel', onMouseWheel, { passive: false });
  animate();
  window.addEventListener('resize', onResize);
  window.addEventListener('click', () => menuVisible.value = false);
};

// --- 应用设置 ---
const applyAllSettingsToThree = () => {
  if (!controls) return;
  camera.fov = settings.fov_default;
  camera.updateProjectionMatrix();

  const azimuth = settings.initial_heading * (Math.PI / 180);
  const polar = (90 - settings.initial_pitch) * (Math.PI / 180);
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
    controls.minAzimuthAngle = -Infinity;
    controls.maxAzimuthAngle = Infinity;
  } else {
    controls.minAzimuthAngle = settings.limit_h_min * (Math.PI / 180);
    controls.maxAzimuthAngle = settings.limit_h_max * (Math.PI / 180);
  }

  // [关键] 垂直限制修正
  // UI Min (e.g. -90 地) -> Three Max (PI)
  // UI Max (e.g. 90 天) -> Three Min (0)
  controls.minPolarAngle = (90 - settings.limit_v_max) * (Math.PI / 180);
  controls.maxPolarAngle = (90 - settings.limit_v_min) * (Math.PI / 180);
  
  controls.update();
};

// --- 实时预览 ---
const onFovPreview = ({ value }) => { camera.fov = value; camera.updateProjectionMatrix(); };
const onFovRangeChange = () => {
  if (settings.fov_default < settings.fov_min) settings.fov_default = settings.fov_min;
  if (settings.fov_default > settings.fov_max) settings.fov_default = settings.fov_max;
  updateCameraFOV();
};

const onHLimitPreview = ({ value }) => {
  const rad = value * (Math.PI / 180);
  controls.minAzimuthAngle = -Infinity; controls.maxAzimuthAngle = Infinity;
  // 预览时让相机对准该角度
  const polar = controls.getPolarAngle();
  const r = 0.1;
  camera.position.x = r * Math.sin(polar) * Math.sin(rad);
  camera.position.z = r * Math.sin(polar) * Math.cos(rad);
  controls.update();
};
const onHLimitChange = () => applyLimits();

const onVLimitPreview = ({ value }) => {
  const polarRad = (90 - value) * (Math.PI / 180);
  controls.minPolarAngle = 0; controls.maxPolarAngle = Math.PI;
  const azimuth = controls.getAzimuthalAngle();
  const r = 0.1;
  camera.position.x = r * Math.sin(polarRad) * Math.sin(azimuth);
  camera.position.y = r * Math.cos(polarRad);
  camera.position.z = r * Math.sin(polarRad) * Math.cos(azimuth);
  controls.update();
};
const onVLimitChange = () => applyLimits();

// --- 交互 ---
const captureInitialState = () => {
  const azimuth = controls.getAzimuthalAngle(); 
  const polar = controls.getPolarAngle(); 
  settings.initial_heading = azimuth * (180 / Math.PI);
  settings.initial_pitch = 90 - (polar * (180 / Math.PI));
  settings.fov_default = camera.fov;
  alert("已记录！请点击保存生效。");
};

const captureCover = async () => {
  renderer.render(scene, camera);
  const dataUrl = renderer.domElement.toDataURL('image/jpeg', 0.7);
  try {
    const res = await fetch('http://127.0.0.1:8000/upload_base64/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_data: dataUrl })
    });
    const data = await res.json();
    await fetch(`http://127.0.0.1:8000/scenes/${currentScene.value.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cover_url: data.url })
    });
    alert("封面已更新！");
  } catch(e) { alert("失败"); }
};

const saveAll = async () => {
  saving.value = true;
  try {
    // 确保发送前 fov_default 是最新的
    const payload = { ...settings };
    const res = await fetch(`http://127.0.0.1:8000/scenes/${currentScene.value.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) alert("保存成功");
  } catch(e) { alert("失败"); } 
  finally { saving.value = false; }
};

const resetToDefaults = () => {
  if(!confirm("恢复默认?")) return;
  Object.assign(settings, DEFAULT_SETTINGS);
  applyAllSettingsToThree();
};

// ... mouseWheel, animate, resize, menu 保持一致 ...
const updateCameraFOV = () => { if(camera) { camera.fov = settings.fov_default; camera.updateProjectionMatrix(); } };
const onMouseWheel = (e) => {
  e.preventDefault();
  let newFov = camera.fov + e.deltaY * 0.05;
  newFov = Math.max(settings.fov_min, Math.min(settings.fov_max, newFov));
  camera.fov = newFov;
  camera.updateProjectionMatrix();
};
const animate = () => { requestAnimationFrame(animate); controls.update(); renderer.render(scene, camera); };
const onResize = () => { if(containerRef.value) { camera.aspect = containerRef.value.clientWidth / containerRef.value.clientHeight; camera.updateProjectionMatrix(); renderer.setSize(containerRef.value.clientWidth, containerRef.value.clientHeight); } };
const onContextMenu = (e) => { e.preventDefault(); menuPos.value = {x:e.clientX, y:e.clientY}; menuVisible.value = true; };
const toggleDirection = () => { isReverse.value = !isReverse.value; controls.rotateSpeed = isReverse.value ? -0.5 : 0.5; };
const resetView = () => applyAllSettingsToThree();

onMounted(() => fetchProject());
onBeforeUnmount(() => { /* 清理逻辑同上 */ });
</script>

<style scoped>
/* 样式复用之前的，确保引入了 DualSlider */
.editor-layout { display: flex; height: 100vh; background: #1a1a1a; color: #ccc; user-select: none; }
.viewport { flex: 1; position: relative; background: #000; }
.three-container { width: 100%; height: 100%; }
.viewport-header {
  position: absolute; top: 0; left: 0; right: 0; height: 50px;
  background: rgba(30,30,30,0.9); border-bottom: 1px solid #333;
  display: flex; justify-content: space-between; align-items: center; padding: 0 20px; z-index: 10;
}
.back-btn, .btn-text { background: none; border: none; color: #aaa; cursor: pointer; font-size: 13px; }
.back-btn:hover, .btn-text:hover { color: white; }
.save-primary-btn { background: #3498db; color: white; border: none; padding: 6px 16px; border-radius: 4px; font-weight: bold; cursor: pointer; }
.scene-name { color: white; font-weight: bold; }
.center-cross { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: rgba(255,255,255,0.3); font-size: 20px; pointer-events: none; }
.context-menu { position: fixed; z-index: 9999; background: #333; border: 1px solid #444; border-radius: 4px; padding: 5px 0; min-width: 160px; }
.context-menu .item { padding: 8px 15px; font-size: 13px; color: #ddd; cursor: pointer; }
.context-menu .item:hover { background: #444; }

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
.sub-desc { font-size: 11px; color: #555; margin-top: 5px; text-align: right; }
.val-display { text-align: center; font-size: 11px; color: #f1c40f; margin-top: 5px; }
input[type=range] { width: 100%; cursor: pointer; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>