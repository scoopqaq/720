<template>
    <div class="dual-slider-container">
      <div class="slider-track" ref="trackRef" @mousedown="onTrackClick">
        <div 
          class="slider-range" 
          :style="{ left: leftPercent + '%', width: widthPercent + '%' }"
        ></div>
  
        <div 
          class="slider-thumb left" 
          :style="{ left: leftPercent + '%' }"
          @mousedown.stop="startDrag('min', $event)"
        >
          <div class="tooltip">{{ modelValue[0] }}°</div>
        </div>
  
        <div 
          class="slider-thumb right" 
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
    modelValue: { type: Array, required: true } // [minVal, maxVal]
  });
  
  const emit = defineEmits(['update:modelValue', 'change']);
  
  const trackRef = ref(null);
  let isDragging = false;
  let currentHandle = null;
  
  // 计算百分比位置
  const totalRange = computed(() => props.max - props.min);
  const leftPercent = computed(() => ((props.modelValue[0] - props.min) / totalRange.value) * 100);
  const rightPercent = computed(() => ((props.modelValue[1] - props.min) / totalRange.value) * 100);
  const widthPercent = computed(() => rightPercent.value - leftPercent.value);
  
  const startDrag = (handle, e) => {
    isDragging = true;
    currentHandle = handle;
    window.addEventListener('mousemove', onDrag);
    window.addEventListener('mouseup', stopDrag);
  };
  
  const onDrag = (e) => {
    if (!isDragging || !trackRef.value) return;
    
    const rect = trackRef.value.getBoundingClientRect();
    const offsetX = e.clientX - rect.left;
    let percent = offsetX / rect.width;
    percent = Math.max(0, Math.min(1, percent));
    
    let newVal = Math.round(props.min + percent * totalRange.value);
    
    const newValues = [...props.modelValue];
    
    if (currentHandle === 'min') {
      // 限制不能超过右滑块
      newVal = Math.min(newVal, props.modelValue[1]);
      newValues[0] = newVal;
    } else {
      // 限制不能小于左滑块
      newVal = Math.max(newVal, props.modelValue[0]);
      newValues[1] = newVal;
    }
    
    emit('update:modelValue', newValues);
  };
  
  const stopDrag = () => {
    if (isDragging) {
      emit('change', props.modelValue);
    }
    isDragging = false;
    currentHandle = null;
    window.removeEventListener('mousemove', onDrag);
    window.removeEventListener('mouseup', stopDrag);
  };
  
  const onTrackClick = (e) => {
    // 点击轨道移动最近的滑块逻辑略复杂，暂且省略，防止误触
  };
  
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
    position: relative; width: 100%; height: 6px; background: #444; border-radius: 3px; cursor: pointer;
  }
  .slider-range {
    position: absolute; height: 100%; background: #3498db; border-radius: 3px;
  }
  .slider-thumb {
    position: absolute; top: 50%; width: 16px; height: 16px; background: #fff;
    border-radius: 50%; transform: translate(-50%, -50%); cursor: grab;
    box-shadow: 0 2px 4px rgba(0,0,0,0.3); z-index: 2;
  }
  .slider-thumb:active { cursor: grabbing; transform: translate(-50%, -50%) scale(1.1); }
  
  .tooltip {
    position: absolute; top: -25px; left: 50%; transform: translateX(-50%);
    background: #333; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px;
    pointer-events: none; white-space: nowrap; opacity: 0; transition: opacity 0.2s;
  }
  .slider-thumb:hover .tooltip, .slider-thumb:active .tooltip { opacity: 1; }
  </style>