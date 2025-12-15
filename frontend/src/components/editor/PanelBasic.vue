<template>
  <div class="panel-content">
    <div class="section-block">
      <h3>1. 初始视角 & 封面</h3>
      <p class="desc">调整画面到最佳角度，点击下方按钮记录。</p>
      <div class="action-grid">
        <button class="action-btn primary" @click="$emit('capture-initial')">📍 设为初始视角</button>
        <button class="action-btn" @click="$emit('capture-cover')">🖼️ 截取封面</button>
      </div>
      <div class="data-display">
        <div class="tag">H: {{ Math.round(settings.initial_heading) }}°</div>
        <div class="tag">V: {{ Math.round(settings.initial_pitch) }}°</div>
        <div class="tag">FOV: {{ Math.round(settings.fov_default) }}</div>
      </div>
    </div>


    <div class="section-block">
      <h3>2. 缩放范围 (FOV)</h3>
      <div class="control-row">
        <label>范围 ({{ settings.fov_min }} - {{ settings.fov_max }})</label>
        <DualSlider 
          :min="10" :max="140" 
          v-model="fovRange" 
          @change="onFovChange" 
          @preview="(v) => $emit('preview-fov', v.value)" 
        />
      </div>
      <div class="control-row">
        <label>默认 FOV ({{ Math.round(settings.fov_default) }})</label>
        <input type="range" :min="settings.fov_min" :max="settings.fov_max" v-model.number="settings.fov_default" @input="$emit('update-camera')">
      </div>
    </div>


    <div class="section-block">
      <h3>3. 视角旋转限制</h3>
      <div class="control-row">
        <div class="label-row">
          <label>水平限制</label>
          <span class="status-tag" v-if="isFullHorizontal">360° 无限</span>
        </div>
        <DualSlider 
          :min="-180" :max="180" 
          v-model="hLimitRange" 
          @change="onLimitChange" 
          @preview="(v) => $emit('preview-h-limit', v.value)" 
        />
        <div class="val-display">{{ settings.limit_h_min }}° ~ {{ settings.limit_h_max }}°</div>
      </div>

      <div class="control-row">
        <label>垂直限制</label>
        <DualSlider 
          :min="-90" :max="90" 
          v-model="vLimitRange" 
          @change="onLimitChange" 
          @preview="handleVPreview" 
        />
        <div class="val-display">
           {{ Math.round(-settings.limit_v_max) }}° (底) ~ {{ Math.round(-settings.limit_v_min) }}° (顶)
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import DualSlider from '../DualSlider.vue';

const props = defineProps(['settings']);
const emit = defineEmits(['capture-initial', 'capture-cover', 'update-camera', 'preview-fov', 'preview-h-limit', 'preview-v-limit']);

const fovRange = computed({
  get: () => [props.settings.fov_min, props.settings.fov_max],
  set: (val) => { props.settings.fov_min = val[0]; props.settings.fov_max = val[1]; }
});

const hLimitRange = computed({
  get: () => [props.settings.limit_h_min, props.settings.limit_h_max],
  set: (val) => { props.settings.limit_h_min = val[0]; props.settings.limit_h_max = val[1]; }
});

// 【核心修改】垂直限制 - 视觉层反转代理
const vLimitRange = computed({
  get: () => {
    // 原始情况：min 是顶(负数), max 是底(正数)
    // 视觉需求：左滑块(min)控制底，右滑块(max)控制顶
    // 解决方案：取反并交换顺序
    // 例如：数据库存的是 [-90, 90]
    // 这里返回：[-90, 90] (因为 -90取反是90变右边，90取反是-90变左边)
    return [-props.settings.limit_v_max, -props.settings.limit_v_min];
  },
  set: (val) => {
    // val[0] 是用户拉到的左边界（看起来是底，负数）
    // val[1] 是用户拉到的右边界（看起来是顶，正数）
    
    // 存回去的时候，要还原这种“错误”的逻辑：
    // 把“看起来是顶”的值(val[1])取反，存给 min (因为系统里 min 是顶)
    props.settings.limit_v_min = -val[1];
    // 把“看起来是底”的值(val[0])取反，存给 max (因为系统里 max 是底)
    props.settings.limit_v_max = -val[0];
  }
});

const isFullHorizontal = computed(() => props.settings.limit_h_min <= -180 && props.settings.limit_h_max >= 180);

// 处理垂直预览，因为数值被我们反转了，预览发给父组件时也要还原一下逻辑
const handleVPreview = (v) => {
  // v.value 是滑块当前的值（例如 -90 到 90）
  // 如果 v.index === 0 (左滑块)，用户想预览“底”
  // 如果 v.index === 1 (右滑块)，用户想预览“顶”
  
  // 发给父组件时取反，父组件就能收到它习惯的“错误数据”了
  emit('preview-v-limit', -v.value);
};

const onFovChange = () => {
  if (props.settings.fov_default < props.settings.fov_min) props.settings.fov_default = props.settings.fov_min;
  if (props.settings.fov_default > props.settings.fov_max) props.settings.fov_default = props.settings.fov_max;
  emit('update-camera');
};

const onLimitChange = () => emit('update-camera');
</script>

<style scoped>
.panel-content { padding: 20px; height: 100%; overflow-y: auto; color: #ccc; }
.section-block { margin-bottom: 25px; }
.section-block h3 { font-size: 13px; color: #3498db; margin: 0 0 8px 0; font-weight: bold; }
.desc { font-size: 12px; color: #777; margin-bottom: 12px; }
.action-grid { display: flex; gap: 10px; margin-bottom: 10px; }
.action-btn { flex: 1; padding: 8px; border: 1px solid #444; background: #333; color: #ccc; border-radius: 4px; cursor: pointer; font-size: 12px; }
.action-btn.primary { border-color: #3498db; color: #3498db; background: rgba(52,152,219,0.15); }
.data-display { display: flex; justify-content: space-between; background: #1e1e1e; padding: 6px 10px; border-radius: 4px; }
.tag { font-size: 11px; color: #f1c40f; font-family: monospace; }
.control-row { margin-bottom: 20px; }
.label-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.control-row label { font-size: 12px; color: #aaa; margin-bottom: 5px; display: block;}
.status-tag { font-size: 10px; background: #27ae60; color: white; padding: 1px 4px; border-radius: 2px; }
.val-display { text-align: center; font-size: 11px; color: #f1c40f; margin-top: 5px; }
input[type=range] { width: 100%; cursor: pointer; }
</style>