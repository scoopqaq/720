<template>
  <div class="dual-slider-container">
    <div class="slider-track" ref="trackRef" @mousedown="onTrackClick">
      <div 
        class="slider-range" 
        :style="{ left: leftPercent + '%', width: widthPercent + '%' }"
      ></div>

      <div 
        class="slider-thumb left" 
        :class="{ active: currentHandle === 'min' }"
        :style="{ left: leftPercent + '%' }"
        @mousedown.stop="startDrag('min', $event)"
      >
        <div class="tooltip">{{ modelValue[0] }}°</div>
      </div>

      <div 
        class="slider-thumb right" 
        :class="{ active: currentHandle === 'max' }"
        :style="{ left: rightPercent + '%' }"
        @mousedown.stop="startDrag('max', $event)"
      >
        <div class="tooltip">{{ modelValue[1] }}°</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onBeforeUnmount } from 'vue';

const props = defineProps({
  min: { type: Number, default: 0 },
  max: { type: Number, default: 100 },
  modelValue: { type: Array, required: true }
});

// [新增] preview 事件，用于拖动时通知父组件哪个值在变
const emit = defineEmits(['update:modelValue', 'change', 'preview']);

const trackRef = ref(null);
const isDragging = ref(false);
const currentHandle = ref(null);

const totalRange = computed(() => props.max - props.min);
const leftPercent = computed(() => ((props.modelValue[0] - props.min) / totalRange.value) * 100);
const rightPercent = computed(() => ((props.modelValue[1] - props.min) / totalRange.value) * 100);
const widthPercent = computed(() => rightPercent.value - leftPercent.value);

const startDrag = (handle, e) => {
  isDragging.value = true;
  currentHandle.value = handle;
  window.addEventListener('mousemove', onDrag);
  window.addEventListener('mouseup', stopDrag);
};

const onDrag = (e) => {
  if (!isDragging.value || !trackRef.value) return;
  
  const rect = trackRef.value.getBoundingClientRect();
  const offsetX = e.clientX - rect.left;
  let percent = offsetX / rect.width;
  percent = Math.max(0, Math.min(1, percent));
  
  let newVal = Math.round(props.min + percent * totalRange.value);
  const newValues = [...props.modelValue];
  
  if (currentHandle.value === 'min') {
    newVal = Math.min(newVal, props.modelValue[1]);
    newValues[0] = newVal;
  } else {
    newVal = Math.max(newVal, props.modelValue[0]);
    newValues[1] = newVal;
  }
  
  emit('update:modelValue', newValues);
  // [新增] 告诉父组件：正在预览哪个滑块，当前值是多少
  emit('preview', { type: currentHandle.value, value: newVal });
};

const stopDrag = () => {
  if (isDragging.value) {
    emit('change', props.modelValue);
  }
  isDragging.value = false;
  currentHandle.value = null;
  window.removeEventListener('mousemove', onDrag);
  window.removeEventListener('mouseup', stopDrag);
};

// 简单的轨道点击逻辑
const onTrackClick = (e) => { /* 暂不实现防止误触 */ };

onBeforeUnmount(() => {
  window.removeEventListener('mousemove', onDrag);
  window.removeEventListener('mouseup', stopDrag);
});
</script>

<style scoped>
.dual-slider-container {
  height: 30px; display: flex; align-items: center; user-select: none; padding: 0 10px;
}
.slider-track {
  position: relative; width: 100%; height: 4px; background: #444; border-radius: 2px; cursor: pointer;
}
.slider-range {
  position: absolute; height: 100%; background: #3498db; border-radius: 2px;
}
.slider-thumb {
  position: absolute; top: 50%; width: 14px; height: 14px; background: #fff;
  border-radius: 50%; transform: translate(-50%, -50%); cursor: grab;
  box-shadow: 0 2px 4px rgba(0,0,0,0.5); z-index: 2; transition: transform 0.1s;
}
.slider-thumb.active { transform: translate(-50%, -50%) scale(1.3); background: #3498db; border: 2px solid white; }
.tooltip {
  position: absolute; top: -28px; left: 50%; transform: translateX(-50%);
  background: #333; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px;
  pointer-events: none; opacity: 0; transition: opacity 0.2s; white-space: nowrap;
}
.slider-thumb:hover .tooltip, .slider-thumb.active .tooltip { opacity: 1; }
</style>