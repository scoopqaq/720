<script setup>
import PanoramaViewer from './components/PanoramaViewer.vue'
</script>

<template>
  <PanoramaViewer />
</template>

<style>
/* 1. 全局重置 */
* {
  box-sizing: border-box;
}

body, html {
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100%;
  overflow: hidden; /* 禁止滚动条 */
}

/* 2. 关键：强制让 Vue 的挂载点 #app 占满全屏 */
#app {
  width: 100vw !important;
  height: 100vh !important;
  max-width: none !important; /* 覆盖默认样式的限制 */
  margin: 0 !important;       /* 覆盖默认样式的居中 */
  padding: 0 !important;      /* 去掉默认内边距 */
  display: block;
}
</style>