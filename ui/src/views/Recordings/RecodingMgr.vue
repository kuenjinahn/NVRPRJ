<!-- eslint-disable vue/multi-word-component-names -->
<template lang="pug">
.recording-mgr
  v-container(fluid)
    v-row
      v-col(cols="12")
        RecodingCompare
</template>

<script>
import RecodingCompare from './RecodingCompare.vue';

export default {
  name: 'RecodingMgr',

  components: {
    RecodingCompare
  }
};
</script>

<style scoped>
.recording-mgr {
  padding: 20px;
}
</style> 
