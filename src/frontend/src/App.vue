<template>
  <div id="app">
    <header class="app-header">
      <h1 class="app-title">
        <RouterLink to="/" class="app-title-link">
          <i class="pi pi-video"></i>
          Video2Minutes
        </RouterLink>
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
import { RouterView, RouterLink } from 'vue-router'
import Toast from 'primevue/toast'

export default {
  name: 'App',
  components: {
    RouterView,
    RouterLink,
    Toast
  }
}
</script>

<style>
#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
}

.app-header {
  background: linear-gradient(
    135deg,
    var(--primary-700) 0%,
    var(--secondary-700) 100%
  );
  color: white;
  padding: var(--space-12) 0;
  text-align: center;
  position: relative;
  overflow: hidden;
}

/* Dark overlay for better text contrast */
.app-header::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.1);
  pointer-events: none;
}

.app-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 100" fill="white" opacity="0.1"><polygon points="0,100 1000,0 1000,100"/></svg>')
    no-repeat center bottom;
  background-size: cover;
}

.app-title {
  font-size: 3rem;
  font-weight: 800;
  margin-bottom: var(--space-3);
  position: relative;
  z-index: 1;
  text-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
  color: white;
  user-select: none;
}

.home-link {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-4);
  cursor: pointer;
  transition: all 0.3s ease;
}

.home-link:hover {
  transform: scale(1.05);
  text-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  filter: brightness(1.1);
}

.home-link i {
  font-size: 3.5rem;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
}

.app-title-link {
  text-decoration: none;
  color: inherit;
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.app-subtitle {
  font-size: 1.25rem;
  font-weight: 500;
  color: white;
  opacity: 1;
  position: relative;
  z-index: 1;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);
}

.app-main {
  flex: 1;
  padding: var(--space-10) var(--space-8);
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
  position: relative;
}

/* Enhanced responsive design */
@media (max-width: 1024px) {
  .app-main {
    max-width: 1000px;
    padding: var(--space-8) var(--space-6);
  }
}

@media (max-width: 768px) {
  .app-header {
    padding: var(--space-10) var(--space-4);
  }

  .home-link {
    font-size: 2.25rem;
    flex-direction: column;
    gap: var(--space-3);
  }

  .home-link i {
    font-size: 2.75rem;
  }

  .app-subtitle {
    font-size: 1.1rem;
  }

  .app-main {
    padding: var(--space-6) var(--space-4);
  }
}

@media (max-width: 480px) {
  .app-header {
    padding: var(--space-8) var(--space-3);
  }

  .home-link {
    font-size: 1.875rem;
  }

  .home-link i {
    font-size: 2.25rem;
  }

  .app-subtitle {
    font-size: 1rem;
  }

  .app-main {
    padding: var(--space-4) var(--space-3);
  }
}

/* Toast positioning - handled in global.css */
</style>
