import * as THREE from 'three';
import { GifReader } from 'omggif';

export class GifTexture extends THREE.CanvasTexture {
  constructor(url) {
    // 初始化 1x1 占位
    const canvas = document.createElement('canvas');
    canvas.width = 1;
    canvas.height = 1;
    
    super(canvas);
    
    this.url = url;
    this.frames = [];
    this.frameDelays = [];
    this.currentFrame = 0;
    this.lastFrameTime = 0;
    this.isLoaded = false;
    this.totalDuration = 0;

    // 关键配置：动态纹理不需要 mipmap，否则会卡顿且容易报错
    this.minFilter = THREE.LinearFilter;
    this.magFilter = THREE.LinearFilter;
    this.generateMipmaps = false; 
    this.colorSpace = THREE.SRGBColorSpace;

    this.load();
  }

  async load() {
    try {
      const response = await fetch(this.url);
      const buffer = await response.arrayBuffer();
      const data = new Uint8Array(buffer);
      
      const reader = new GifReader(data);
      const width = reader.width;
      const height = reader.height;

      // 1. 设置正确的 Canvas 尺寸
      this.image.width = width;
      this.image.height = height;
      
      const ctx = this.image.getContext('2d', { willReadFrequently: true });
      const frameData = new Uint8ClampedArray(width * height * 4);
      
      // 2. 解析每一帧
      for (let i = 0; i < reader.numFrames(); i++) {
        // 兼容性处理
        if (reader.decodeAndBlitFrameRGBA8) {
          reader.decodeAndBlitFrameRGBA8(i, frameData);
        } else if (reader.decodeAndBlitFrameRGBA) {
          reader.decodeAndBlitFrameRGBA(i, frameData);
        } else {
          throw new Error("GifReader decode method not found");
        }
        
        const imageData = new ImageData(
          new Uint8ClampedArray(frameData), 
          width, 
          height
        );

        this.frames.push(imageData);
        
        let delay = reader.frameInfo(i).delay * 10;
        if (delay === 0) delay = 100;
        
        this.frameDelays.push(delay);
        this.totalDuration += delay;
      }

      // 3. 绘制第一帧
      if (this.frames.length > 0) {
        ctx.putImageData(this.frames[0], 0, 0);
      }

      // --- 【核心修复代码】 ---
      // 在标记更新之前，必须调用 dispose()。
      // 这告诉 GPU：“销毁之前那个 1x1 的纹理显存，下次渲染时重新申请一块大的。”
      this.dispose(); 
      
      // 标记加载完成并请求更新
      this.isLoaded = true;
      this.needsUpdate = true;
      
    } catch (e) {
      console.error('GIF 加载失败:', this.url, e);
    }
  }

  update() {
    if (!this.isLoaded || this.frames.length <= 1) return;

    const now = performance.now();
    const delay = this.frameDelays[this.currentFrame];

    if (now - this.lastFrameTime >= delay) {
      this.currentFrame = (this.currentFrame + 1) % this.frames.length;
      this.lastFrameTime = now;

      const ctx = this.image.getContext('2d');
      ctx.putImageData(this.frames[this.currentFrame], 0, 0);
      
      this.needsUpdate = true;
    }
  }
}