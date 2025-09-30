<template>
  <div class="login-container">
    <!-- Left Sidebar Container -->
    <div class="sidebar-container">
      <div class="sidebar-content">
        <!-- Logo Section -->
        <div class="logo-section">
          <div class="logo-container">
          <v-img
            src="@/assets/img/logo.png"
            alt="Welcome to SDMS "
            width="60"
            height="80"
            class="logo-image"
          />
        </div>
        </div>

        <!-- Login Form Section -->
        <div class="login-form-section">
          <v-card class="login-card" elevation="0">
            <v-card-text class="pa-4">
              <div class="login-form">
                <!-- Username Input -->
                <v-text-field
                  v-model="user.userId"
                  label="아이디"
                  prepend-inner-icon="mdi-account"
                  outlined
                  dense
                  class="login-input"
                  hide-details="auto"
                />
                
                <!-- Password Input -->
                <v-text-field
                  v-model="user.password"
                  label="패스워드"
                  prepend-inner-icon="mdi-lock"
                  :type="showPassword ? 'text' : 'password'"
                  outlined
                  dense
                  class="login-input"
                  hide-details="auto"
                  @keyup.enter="handleLogin"
                >
                  <template v-slot:append>
                    <v-icon
                      @click="showPassword = !showPassword"
                      class="password-toggle"
                    >
                      {{ showPassword ? 'mdi-eye-off' : 'mdi-eye' }}
                    </v-icon>
                  </template>
                </v-text-field>

                <!-- Login Button -->
                <v-btn
                  @click="handleLogin"
                  color="primary"
                  block
                  large
                  class="login-btn"
                  :loading="isLoading"
                >
                  로그인
                </v-btn>

                <!-- Version Info -->
                <div class="version-info">
                  <span class="version-text">v{{ version }}</span>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </div>

        <!-- Footer Section -->
        <div class="sidebar-footer">
          <div class="contact-info">
            <div class="info-item">
              <span class="info-label">주소:</span>
              <span class="info-value">서울특별시 강남구</span>
            </div>
            <div class="info-item">
              <span class="info-label">Tel:</span>
              <span class="info-value">02-0000-0000</span>
            </div>
            <div class="info-item">
              <span class="info-label">E-Mail:</span>
              <span class="info-value">0000@0000.com</span>
            </div>
          </div>
          <div class="copyright">
            Copyright© 0000. All rights reserved.
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content Area -->
    <div class="main-content">
      <!-- Image Slideshow -->
      <div class="slideshow-container">
        <v-carousel
          v-model="currentSlide"
          :show-arrows="false"
          :show-indicators="false"
          height="100vh"
          width="100%"
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
import { mapActions } from 'vuex';
import { getConfig } from '@/api/config.api';
import { getEventSetting } from '@/api/eventSetting.api.js';
export default {
  name: 'Login',
  data() {
    return {
      currentSlide: 0,
      isLoading: false,
      showPassword: false,
      version: '1.0.0', // 기본 버전
      user: {
        userId: process.env.NODE_ENV === 'development' ? 'akj' : '',
        password: process.env.NODE_ENV === 'development' ? 'test123' : ''
      },
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
    this.loadVersionInfo();
    this.loadCustomSlideshowImages();
  },
  
  methods: {
    ...mapActions('auth', ['login']),
    
    // config.ini에서 version 정보 가져오기
    async loadVersionInfo() {
      try {
        const response = await getConfig();
        if (response.data && response.data.web && response.data.web.version) {
          this.version = response.data.web.version;
        }
      } catch (error) {
        console.warn('Failed to load version info:', error);
        // 에러가 발생해도 기본 버전 사용
      }
    },
    
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
    },
    
    async handleLogin() {
      if (!this.user.userId || !this.user.password) {
        this.$toast.error('아이디와 패스워드를 입력해주세요.');
        return;
      }

      this.isLoading = true;
      try {
        // 실제 로그인 API 호출
        await this.$store.dispatch('auth/login', { ...this.user });

        await getConfig();

        // 로그인 성공 후 Socket.IO 연결 시작
        try {
          const { connectSocket } = await import('@/common/socket-instance.js');
          connectSocket();
          console.log('[Login] Socket connection initiated');
        } catch (socketError) {
          console.warn('[Login] Socket connection failed:', socketError);
        }

        this.$router.push('/first-start');
      } catch (error) {
        console.error('Login error:', error);
        
        // 에러 메시지 처리
        let errorMessage = '로그인에 실패했습니다.';
        if (error.response && error.response.data && error.response.data.message) {
          errorMessage = error.response.data.message;
        } else if (error.message) {
          errorMessage = error.message;
        }
        
        this.$toast.error(errorMessage);
      } finally {
        this.isLoading = false;
      }
    }
  }
};
</script>

<style lang="scss" scoped>
.login-container {
  display: flex;
  height: 100vh;
  background: #f5f5f5;
}

// Sidebar Container
.sidebar-container {
  min-width: 340px;
  background: white;
  box-shadow: 2px 0 10px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  z-index: 1000;
}

.sidebar-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 20px;
}

// Logo Section
.logo-section {
  margin-bottom: 20px;
  
  .logo-container {
    display: flex;
    align-items: center;
    justify-content: center;
    transform: scale(0.6);
    transform-origin: center center;
    
    .logo-image {
      border-radius: 10%;
      background: #f3f5f6;
      padding: 8px;
    }
    
    .logo-text {
      margin-left: 12px;
      font-size: 18px;
      font-weight: 600;
      color: #232323;
    }
  }
}

// Login Form Section
.login-form-section {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 20px;
  
  .login-card {
    width: 100%;
    background-color: white!important;
    border: 1px solid #666;
    border-radius: 10px;
    padding: 20px;
    .login-form {
      .login-input {
        margin-bottom: 20px;
        
        ::v-deep .v-input__control {
          .v-input__slot {
            border-radius: 8px;
            border: 1px solid #e0e0e0;
            background-color: white !important;
            
            &:hover {
              border-color: #1976d2;
            }
            
            &.v-input--is-focused {
              border-color: #1976d2;
            }
          }
          
          .v-text-field__slot {
            input {
              color: #000000 !important;
            }
            
            label {
              color: #666666 !important;
            }
          }
        }
      }
      
      .login-btn {
        margin-top: 20px;
        height: 48px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 16px;
        text-transform: none;
        background-color: #95594c!important;
        color: #f3f5f6 !important;
        &:hover {
          background: linear-gradient(135deg, #1565c0, #0d47a1);
        }
      }

      .version-info {
        text-align: center;
        margin-top: 15px;
        
        .version-text {
          font-size: 14px;
          color: #666;
          font-weight: 500;
          letter-spacing: 0.5px;
        }
      }
      
      .password-toggle {
        cursor: pointer;
        color: #666;
        
        &:hover {
          color: #1976d2;
        }
      }
    }
  }
}

// Footer Section
.sidebar-footer {
  margin-top: auto;
  padding-top: 20px;
  border-top: 1px solid #e0e0e0;
  
  .contact-info {
    margin-bottom: 15px;
    
    .info-item {
      display: flex;
      margin-bottom: 8px;
      font-size: 12px;
      color: #666;
      
      .info-label {
        font-weight: 600;
        min-width: 60px;
        margin-right: 8px;
      }
      
      .info-value {
        color: #333;
      }
    }
  }
  
  .copyright {
    font-size: 11px;
    color: #999;
    text-align: center;
  }
}

// Main Content Area
.main-content {
  flex: 1;
  height: 100vh;
  background: #000;
  margin: 0 !important;
  padding: 0 !important;
  display: flex;
  align-items: center;
  justify-content: center;
}

.slideshow-container {
  height: 100vh;
  width: 100%;
  position: relative;
  margin: 0 !important;
  padding: 0 !important;
  display: flex;
  align-items: center;
  justify-content: center;
  
  .slideshow-carousel {
    height: 100%;
    width: 100%;

    margin: 0 !important;
    margin-left: -190px !important;
    padding: 0 0 !important;
    
          .slideshow-item {
        position: relative;
        height: 100%;
        width: 100%;
        
        .slideshow-image {
          position: relative;
          height: 100%;
          width: 100%;
        
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
            width: 100%;
            height: 100%;
          
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
@media (max-width: 1024px) {
  .sidebar-container {
    width: 350px;
  }
}

@media (max-width: 768px) {
  .login-container {
    flex-direction: column;
  }
  
  .sidebar-container {
    width: 100%;
    height: auto;
    min-height: 400px;
  }
  
  .main-content {
    height: calc(100vh - 400px);
  }
  
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
  .sidebar-content {
    padding: 15px;
  }
  
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
