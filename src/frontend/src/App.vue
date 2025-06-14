<template>
  <div id="app">
    <header class="app-header">
      <h1 class="app-title">
        <i class="pi pi-video"></i>
        Video2Minutes
      </h1>
      <p class="app-subtitle">動画から議事録を自動生成</p>
    </header>
    
    <main class="app-main">
      <RouterView />
    </main>
    
    <Toast />
  </div>
</template>

<script>
import { RouterView } from 'vue-router'
import Toast from 'primevue/toast'

export default {
  name: 'App',
  components: {
    RouterView,
    Toast
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background-color: #f8f9fa;
  color: #333;
}

#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 2rem 0;
  text-align: center;
}

.app-title {
  font-size: 2.5rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
}

.app-subtitle {
  font-size: 1.1rem;
  opacity: 0.9;
}

.app-main {
  flex: 1;
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}

@media (max-width: 768px) {
  .app-title {
    font-size: 2rem;
  }
  
  .app-main {
    padding: 1rem;
  }
}
</style>