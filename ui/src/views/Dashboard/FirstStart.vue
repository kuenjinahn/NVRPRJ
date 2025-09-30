<template>
  <div class="dashboard-main">
    <!-- Main Content Area -->
    <div class="main-content">
      <!-- Image Slideshow -->
      <div class="slideshow-container">
        <v-carousel
          v-model="currentSlide"
          :show-arrows="false"
          :show-indicators="false"
          height="100vh"
          class="slideshow-carousel"
          cycle
          interval="5000"
        >
          <v-carousel-item
            v-for="(image, index) in (customSlideshowImages.length > 0 ? customSlideshowImages : slideshowImages)"
            :key="index"
            class="slideshow-item"
          >
            <v-img
              :src="image.src"
              :alt="image.alt"
              height="100%"
              width="100%"
              cover
              class="slideshow-image"
            >
              <div class="image-overlay">
                <div class="overlay-content">
                  <h1 class="main-title">댐 열화상카메라 스마트 모니터링 시스템</h1>
                  <h2 class="sub-title">Welcome to SDMS </h2>
                </div>
              </div>
            </v-img>
          </v-carousel-item>
        </v-carousel>
      </div>
    </div>
  </div>
</template>

<script>
import { getEventSetting } from '@/api/eventSetting.api.js';

export default {
  name: 'Dashboard',
  data() {
    return {
      currentSlide: 0,
      slideshowImages: [
        {
          src: 'https://images.unsplash.com/photo-1578662996442-48f60103fc96?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2070&q=80',
          alt: 'Dam and Mountains'
        },
        {
          src: 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2070&q=80',
          alt: 'Mountain Landscape'
        },
        {
          src: 'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2071&q=80',
          alt: 'Forest and Water'
        }
      ],
      customSlideshowImages: [] // EventSetting에서 설정한 커스텀 배경이미지
    };
  },
  
  mounted() {
    this.loadCustomSlideshowImages();
  },
  
  methods: {
    // EventSetting에서 설정한 커스텀 배경이미지 로드
    async loadCustomSlideshowImages() {
      try {
        const data = await getEventSetting();
        if (data && data.system_json) {
          const system = JSON.parse(data.system_json);
          if (system.slideshowImages && Array.isArray(system.slideshowImages)) {
            // null이 아닌 이미지만 필터링
            this.customSlideshowImages = system.slideshowImages.filter(img => img && img.src);
            console.log('커스텀 슬라이드쇼 이미지 로드됨:', this.customSlideshowImages);
          }
        }
      } catch (error) {
        console.warn('Failed to load custom slideshow images:', error);
        // 에러가 발생해도 기본 이미지 사용
      }
    }
  }
};
</script>

<style lang="scss" scoped>
.dashboard-main {
  height: 100vh;
  background: #000;
  margin: 0 !important;
  padding: 0 !important;
}

.main-content {
  height: 100vh;
  background: #000;
  margin: 0 !important;
  padding: 0 !important;
}

.slideshow-container {
  height: 100vh;
  position: relative;
  margin: 0 !important;
  padding: 0 !important;
  
  .slideshow-carousel {
  height: 100%;
  margin: 0 !important;
  padding: 0 !important;
    
    .slideshow-item {
      position: relative;
      
      .slideshow-image {
        position: relative;
        
        .image-overlay {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.3);
          display: flex;
          align-items: center;
          justify-content: center;
          
          .overlay-content {
            text-align: center;
            color: white;
            
            .main-title {
              font-size: 3rem;
              font-weight: 700;
              margin-bottom: 1rem;
              text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
              line-height: 1.2;
            }
            
            .sub-title {
              font-size: 1.5rem;
              font-weight: 400;
              text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
            }
          }
        }
      }
    }
  }
}

// 반응형 디자인
@media (max-width: 768px) {
  .slideshow-container {
    .image-overlay {
      .overlay-content {
        .main-title {
          font-size: 2rem;
        }
        
        .sub-title {
          font-size: 1.2rem;
        }
      }
    }
  }
}

@media (max-width: 480px) {
  .slideshow-container {
    .image-overlay {
      .overlay-content {
        .main-title {
          font-size: 1.5rem;
        }
        
        .sub-title {
          font-size: 1rem;
        }
      }
    }
  }
}
</style>
