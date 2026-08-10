<template>
  <div class="min-h-screen bg-bg">
    <NavBar />
    <router-view />
  </div>
</template>

<script setup>
import NavBar from './components/layout/NavBar.vue'
</script>
