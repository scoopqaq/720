<template>
  <div class="editor-layout">
    <div class="viewport">
      <div 
        ref="containerRef" 
        class="three-container"
        @contextmenu.prevent="onContextMenu"
      ></div>
      
      <div class="viewport-header">
        <button class="back-btn" @click="$emit('back')">← 返回列表</button>
        <div class="scene-info" v-if="currentScene">
          <span class="scene-name">{{ currentScene.name }}</span>
        </div>
        <button class="save-primary-btn" @click="saveAll" :disabled="saving">
          {{ saving ? '保存中...' : '💾 保存所有设置' }}
        </button>
      </div>
      
      <div class="center-cross">+</div>

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
       <div class="panel-header">全景参数配置</div>
       <div class="panel-body" v-if="currentScene">
          <div class="section-block">
            <h3>1. 初始状态与封面</h3>
            <p class="desc">在左侧调整好角度和缩放，点击下方按钮记录。</p>
            <div class="action-grid">
              <button class="action-btn primary" @click="captureInitialState">📍 设为初始视角 & FOV</button>
              <button class="action-btn" @click="captureCover">🖼️ 截取当前画面为封面</button>
            </div>
            <div class="data-display">
              <div class="tag">水平: {{ Math.round(settings.initial_heading) }}°</div>
              <div class="tag">垂直: {{ Math.round(settings.initial_pitch) }}°</div>
              <div class="tag">FOV: {{ Math.round(settings.fov_default) }}</div>
            </div>
          </div>
          <hr class="divider">
          <div class="section-block">
            <h3>2. 缩放范围 (FOV)</h3>
            <div class="control-row">
              <label>范围 ({{ settings.fov_min }} - {{ settings.fov_max }})</label>
              <DualSlider :min="10" :max="150" v-model="fovRange" @change="onFovRangeChange" />
            </div>
            <div class="control-row">
              <label>默认值 ({{ Math.round(settings.fov_default) }})</label>
              <input type="range" :min="settings.fov_min" :max="settings.fov_max" v-model.number="settings.fov_default" @input="updateCameraFOV">
            </div>
          </div>
          <hr class="divider">
          <div class="section-block">
            <h3>3. 视角旋转限制</h3>
            <div class="control-row">
              <label>水平限制 ({{ settings.limit_h_min }}° ~ {{ settings.limit_h_max }}°)</label>
              <DualSlider :min="-180" :max="180" v-model="hLimitRange" @change="onHLimitChange" />
            </div>
            <div class="control-row">
              <label>垂直限制 ({{ settings.limit_v_min }}° ~ {{ settings.limit_v_max }}°)</label>
              <DualSlider :min="-90" :max="90" v-model="vLimitRange" @change="onVLimitChange" />
              <p class="sub-desc">90°=天顶，-90°=脚底</p>
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

const settings = reactive({
  initial_heading: 0,
  initial_pitch: 0,
  fov_min: 70,
  fov_max: 120,
  fov_default: 95,
  limit_h_min: -180,
  limit_h_max: 180,
  limit_v_min: -90,
  limit_v_max: 90,
});

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

let scene, camera, renderer, controls, sphereMesh, textureLoader, animationId;

// [新增] 菜单状态
const menuVisible = ref(false);
const menuPos = ref({ x: 0, y: 0 });
const isReverse = ref(false); // 拖拽方向状态

// --- 初始化与加载 (保持原有逻辑) ---
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

  settings.initial_heading = target.initial_heading ?? 0;
  settings.initial_pitch = target.initial_pitch ?? 0;
  settings.fov_min = target.fov_min ?? 70;
  settings.fov_max = target.fov_max ?? 120;
  settings.fov_default = target.fov_default ?? 95;
  settings.limit_h_min = target.limit_h_min ?? -180;
  settings.limit_h_max = target.limit_h_max ?? 180;
  settings.limit_v_min = target.limit_v_min ?? -90;
  settings.limit_v_max = target.limit_v_max ?? 90;

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
  scene.add(sphereMesh);

  textureLoader = new THREE.TextureLoader();
  textureLoader.setCrossOrigin('anonymous');

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.1;
  controls.enableZoom = false; 
  // [新增] 初始化方向
  controls.rotateSpeed = isReverse.value ? -0.5 : 0.5;

  containerRef.value.addEventListener('wheel', onMouseWheel, { passive: false });

  animate();
  window.addEventListener('resize', onResize);
  // [新增] 关闭菜单监听
  window.addEventListener('click', closeMenu);
};

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
  controls.update();
  updateControlsLimits();
};

const updateControlsLimits = () => {
  if (!controls) return;
  controls.minAzimuthAngle = settings.limit_h_min * (Math.PI / 180);
  controls.maxAzimuthAngle = settings.limit_h_max * (Math.PI / 180);
  controls.minPolarAngle = (90 - settings.limit_v_max) * (Math.PI / 180);
  controls.maxPolarAngle = (90 - settings.limit_v_min) * (Math.PI / 180);
  controls.update();
};

// [新增] 右键逻辑
const onContextMenu = (e) => {
  e.preventDefault(); // 屏蔽浏览器菜单
  menuPos.value = { x: e.clientX, y: e.clientY };
  menuVisible.value = true;
};

const closeMenu = () => {
  menuVisible.value = false;
};

const toggleDirection = () => {
  if (!controls) return;
  isReverse.value = !isReverse.value;
  const speed = 0.5;
  controls.rotateSpeed = isReverse.value ? -speed : speed;
};

const resetView = () => {
  // 恢复到当前保存的初始状态
  applyAllSettingsToThree();
};

const captureInitialState = () => {
  if (!controls) return;
  const azimuth = controls.getAzimuthalAngle(); 
  const polar = controls.getPolarAngle(); 
  settings.initial_heading = azimuth * (180 / Math.PI);
  settings.initial_pitch = 90 - (polar * (180 / Math.PI));
  settings.fov_default = camera.fov;
  const tempBtn = document.querySelector('.action-btn.primary');
  if(tempBtn) {
    const originalText = tempBtn.innerText;
    tempBtn.innerText = "✅ 已记录";
    setTimeout(() => tempBtn.innerText = originalText, 1000);
  }
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
  } catch(e) { alert("上传失败"); }
};

const saveAll = async () => {
  saving.value = true;
  try {
    const payload = { ...settings };
    payload.fov_default = camera.fov;
    const res = await fetch(`http://127.0.0.1:8000/scenes/${currentScene.value.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) alert("设置已保存！");
    else throw new Error("API Error");
  } catch(e) { alert("保存失败"); } 
  finally { saving.value = false; }
};

const onFovRangeChange = () => {
  if (settings.fov_default < settings.fov_min) settings.fov_default = settings.fov_min;
  if (settings.fov_default > settings.fov_max) settings.fov_default = settings.fov_max;
  updateCameraFOV();
};
const updateCameraFOV = () => {
  if (camera) { camera.fov = settings.fov_default; camera.updateProjectionMatrix(); }
};
const onHLimitChange = () => { updateControlsLimits(); };
const onVLimitChange = () => { updateControlsLimits(); };

const onMouseWheel = (e) => {
  e.preventDefault();
  let newFov = camera.fov + e.deltaY * 0.05;
  newFov = Math.max(settings.fov_min, Math.min(settings.fov_max, newFov));
  camera.fov = newFov;
  camera.updateProjectionMatrix();
};

const animate = () => {
  animationId = requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
};

const onResize = () => {
  if (!containerRef.value) return;
  camera.aspect = containerRef.value.clientWidth / containerRef.value.clientHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(containerRef.value.clientWidth, containerRef.value.clientHeight);
};

onMounted(() => fetchProject());
onBeforeUnmount(() => {
  cancelAnimationFrame(animationId);
  window.removeEventListener('resize', onResize);
  window.removeEventListener('click', closeMenu);
  if (containerRef.value) containerRef.value.removeEventListener('wheel', onMouseWheel);
  if (renderer) renderer.dispose();
});
</script>

<style scoped>
/* 这里样式与之前基本一致，只需增加 context-menu 的样式 */
.editor-layout { display: flex; height: 100vh; background: #1a1a1a; color: #ccc; }
.viewport { flex: 1; position: relative; background: #000; }
.three-container { width: 100%; height: 100%; }
.viewport-header {
  position: absolute; top: 0; left: 0; right: 0; height: 56px;
  background: rgba(30,30,30,0.9); border-bottom: 1px solid #333;
  display: flex; justify-content: space-between; align-items: center; padding: 0 20px; z-index: 10;
}
.back-btn { background: none; border: none; color: #aaa; cursor: pointer; font-size: 14px; }
.back-btn:hover { color: white; }
.scene-name { font-size: 16px; font-weight: bold; color: white; }
.center-cross { 
  position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
  color: rgba(255,255,255,0.5); font-size: 20px; pointer-events: none;
}

/* [新增] 上下文菜单样式 */
.context-menu {
  position: fixed; z-index: 9999;
  background: #333; border: 1px solid #444; border-radius: 4px;
  padding: 5px 0; min-width: 160px; box-shadow: 0 4px 10px rgba(0,0,0,0.5);
}
.context-menu .item {
  padding: 8px 15px; font-size: 13px; color: #ddd; cursor: pointer;
}
.context-menu .item:hover { background: #444; color: #fff; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* 侧边栏及其他样式保持不变 (复用之前的 CSS) */
.sidebar { width: 360px; background: #252526; border-left: 1px solid #333; display: flex; flex-direction: column; }
.panel-header { height: 56px; line-height: 56px; padding: 0 20px; font-size: 16px; font-weight: bold; background: #252526; border-bottom: 1px solid #333; color: white; }
.panel-body { flex: 1; padding: 20px; overflow-y: auto; }
.section-block { margin-bottom: 25px; }
.section-block h3 { font-size: 14px; color: #3498db; margin: 0 0 5px 0; text-transform: uppercase; }
.desc { font-size: 12px; color: #777; margin-bottom: 15px; }
.action-grid { display: flex; gap: 10px; margin-bottom: 15px; }
.action-btn { flex: 1; padding: 10px 5px; background: #333; border: 1px solid #444; color: #ccc; border-radius: 6px; cursor: pointer; font-size: 12px; }
.action-btn.primary { background: rgba(52,152,219,0.1); border-color: #3498db; color: #3498db; }
.action-btn:hover { background: #444; color: white; }
.data-display { display: flex; justify-content: space-between; background: #1e1e1e; padding: 8px; border-radius: 4px; }
.tag { font-size: 12px; color: #f1c40f; font-family: monospace; }
.divider { border: 0; border-top: 1px solid #333; margin: 25px 0; }
.control-row { margin-bottom: 20px; }
.control-row label { display: block; font-size: 12px; margin-bottom: 8px; color: #aaa; }
.sub-desc { font-size: 11px; color: #555; margin-top: 5px; text-align: right; }
.save-primary-btn { background: #3498db; color: white; border: none; padding: 8px 24px; border-radius: 4px; font-weight: 600; cursor: pointer; }
.save-primary-btn:hover { background: #2980b9; }
</style>