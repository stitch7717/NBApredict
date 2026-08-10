<template>
  <el-config-provider :locale="zhCn">
    <router-view />
  </el-config-provider>
</template>

<script setup>
import zhCn from 'element-plus/es/locale/lang/zh-cn'
</script>

<style lang="scss">
html, body {
  margin: 0;
  padding: 0;
  height: 100%;
  background: $bg-base;
}

#app {
  height: 100%;
}
</style>
