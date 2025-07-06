<template>
  <div class="event-area">
    <div class="video-container">
      <!-- 비디오 플레이어가 들어갈 위치 -->
      <video ref="videoPlayer" class="video-player"></video>
    </div>
    
    <div class="options-panel">
      <div class="option-item">
        <label>Force Close Timer (초)</label>
        <div class="slider-container">
          <input 
            type="range" 
            v-model="options.forceCloseTimer" 
            min="1" 
            max="100" 
            class="slider"
            @input="updateOptions"
          >
          <span class="value">{{ options.forceCloseTimer }}</span>
        </div>
      </div>

      <div class="option-item">
        <label>Dwell Timer (초)</label>
        <div class="slider-container">
          <input 
            type="range" 
            v-model="options.dwellTimer" 
            min="1" 
            max="100" 
            class="slider"
            @input="updateOptions"
          >
          <span class="value">{{ options.dwellTimer }}</span>
        </div>
      </div>

      <div class="option-item">
        <label>Sensitivity</label>
        <div class="slider-container">
          <input 
            type="range" 
            v-model="options.sensitivity" 
            min="1" 
            max="100" 
            class="slider"
            @input="updateOptions"
          >
          <span class="value">{{ options.sensitivity }}</span>
        </div>
      </div>

      <div class="option-item">
        <label>Difference</label>
        <div class="slider-container">
          <input 
            type="range" 
            v-model="options.difference" 
            min="1" 
            max="100" 
            class="slider"
            @input="updateOptions"
          >
          <span class="value">{{ options.difference }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'EventArea',
  data() {
    return {
      options: {
        forceCloseTimer: 30,
        dwellTimer: 50,
        sensitivity: 75,
        difference: 50
      }
    }
  },
  methods: {
    updateOptions() {
      // 옵션 변경 시 부모 컴포넌트에 이벤트 발생
      this.$emit('options-updated', this.options)
    }
  }
}
</script>

<style scoped>
.event-area {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
}

.video-container {
  width: 100%;
  height: 70%;
  background-color: #000;
  position: relative;
}

.video-player {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.options-panel {
  height: 30%;
  padding: 20px;
  background-color: #f5f5f5;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.option-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.option-item label {
  font-size: 14px;
  color: #333;
}

.slider-container {
  display: flex;
  align-items: center;
  gap: 10px;
}

.slider {
  flex: 1;
  height: 6px;
  -webkit-appearance: none;
  background: #ddd;
  border-radius: 3px;
  outline: none;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  background: #4CAF50;
  border-radius: 50%;
  cursor: pointer;
}

.slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  background: #4CAF50;
  border-radius: 50%;
  cursor: pointer;
  border: none;
}

.value {
  min-width: 30px;
  text-align: right;
  font-size: 14px;
  color: #666;
}
</style> 