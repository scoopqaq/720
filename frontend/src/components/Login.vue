<template>
  <div class="auth-wrapper">
    <div class="auth-box">
      <h2>VR 全景云平台</h2>
      
      <div class="tabs">
        <div 
          class="tab" 
          :class="{active: mode==='login'}" 
          @click="mode='login'"
        >
          登录
        </div>
        <div 
          class="tab" 
          :class="{active: mode==='register'}" 
          @click="mode='register'"
        >
          注册
        </div>
      </div>

      <div class="form-body">
        <div class="input-group">
          <label>账号</label>
          <input 
            type="text" 
            v-model="form.username" 
            placeholder="请输入用户名" 
            @keyup.enter="submit"
          >
        </div>
        <div class="input-group">
          <label>密码</label>
          <input 
            type="password" 
            v-model="form.password" 
            placeholder="请输入密码" 
            @keyup.enter="submit"
          >
        </div>
        
        <div class="error-msg" v-if="errorMsg">{{ errorMsg }}</div>

        <button class="submit-btn" @click="submit" :disabled="loading">
          {{ loading ? '处理中...' : (mode==='login' ? '立即登录' : '注册账号') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';

// [关键] 定义正确的事件名，和 App.vue 里的 @login-success 对应
const emit = defineEmits(['login-success']);

const mode = ref('login'); // 'login' | 'register'
const loading = ref(false);
const errorMsg = ref('');
const form = reactive({ username: '', password: '' });

const submit = async () => {
  if(!form.username || !form.password) {
    errorMsg.value = "请输入账号和密码";
    return;
  }
  
  loading.value = true;
  errorMsg.value = '';
  
  // 这里不使用 authFetch，因为还没有 Token
  const url = mode.value === 'login' 
    ? 'http://127.0.0.1:8000/auth/login' 
    : 'http://127.0.0.1:8000/auth/register';

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(form)
    });
    
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || '请求失败');
    }

    if (mode.value === 'register') {
      alert("注册成功，请登录");
      mode.value = 'login';
      form.password = ''; // 清空密码方便登录
    } else {
      // 登录成功：保存 Token
      localStorage.setItem('auth_token', data.access_token);
      localStorage.setItem('username', data.username);
      
      // [关键] 发送信号通知父组件
      emit('login-success');
    }
  } catch (e) {
    errorMsg.value = e.message;
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.auth-wrapper { 
  height: 100vh; 
  background: #2c3e50; 
  display: flex; 
  align-items: center; 
  justify-content: center; 
}

.auth-box { 
  width: 380px; 
  background: white; 
  padding: 40px; 
  border-radius: 8px; 
  box-shadow: 0 10px 30px rgba(0,0,0,0.3); 
}

h2 { 
  text-align: center; 
  margin-bottom: 30px; 
  color: #333; 
}

.tabs { 
  display: flex; 
  border-bottom: 1px solid #eee; 
  margin-bottom: 20px; 
}

.tab { 
  flex: 1; 
  text-align: center; 
  padding: 10px; 
  cursor: pointer; 
  color: #999; 
  border-bottom: 2px solid transparent; 
  transition: all 0.3s;
}

.tab.active { 
  color: #3498db; 
  border-color: #3498db; 
  font-weight: bold; 
}

.input-group { 
  margin-bottom: 20px; 
}

.input-group label { 
  display: block; 
  margin-bottom: 8px; 
  font-size: 14px; 
  color: #666; 
}

.input-group input { 
  width: 100%; 
  padding: 10px; 
  border: 1px solid #ddd; 
  border-radius: 4px; 
  outline: none; 
  font-size: 16px;
}

.input-group input:focus { 
  border-color: #3498db; 
}

.error-msg { 
  color: #e74c3c; 
  font-size: 13px; 
  margin-bottom: 15px; 
  text-align: center; 
}

.submit-btn { 
  width: 100%; 
  background: #3498db; 
  color: white; 
  padding: 12px; 
  border: none; 
  border-radius: 4px; 
  cursor: pointer; 
  font-size: 16px; 
  font-weight: bold;
}

.submit-btn:disabled { 
  background: #ccc; 
  cursor: not-allowed; 
}

.submit-btn:hover:not(:disabled) {
  background: #2980b9;
}
</style>