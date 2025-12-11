// src/utils/api.js

const BASE_URL = 'http://127.0.0.1:8000';

export const authFetch = async (endpoint, options = {}) => {
  // 1. 获取 Token
  const token = localStorage.getItem('auth_token');
  
  // 2. 构造 Headers
  const headers = {
    ...options.headers,
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // 3. 发送请求
  // 如果 endpoint 是完整链接(http开头)就直接用，否则拼接 BASE_URL
  const url = endpoint.startsWith('http') ? endpoint : `${BASE_URL}${endpoint}`;
  
  const response = await fetch(url, {
    ...options,
    headers
  });

  // 4. 统一处理 401 未登录/过期
  if (response.status === 401) {
    localStorage.removeItem('auth_token');
    // 强制刷新页面，App.vue 会自动检测到无 Token 并显示登录页
    window.location.reload();
    throw new Error("登录已过期，请重新登录");
  }

  return response;
};

// 辅助函数：生成图片完整 URL
export const getImageUrl = (path) => {
  if (!path) return '';
  if (path.startsWith('http')) return path;
  return `${BASE_URL}${path}`;
};