<template>
  <router-view />
</template>

<script setup>
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html,
body {
  height: 100%;
  overflow: hidden;
}

#app {
  width: 100%;
  height: 100vh;
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.el-menu-vertical {
  border-right: none;
}

.el-main {
  background-color: #f5f5f5;
  padding: 20px;
}

.el-header {
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}
</style>
