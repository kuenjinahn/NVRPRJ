<!-- eslint-disable vue/multi-word-component-names -->
<template>
  <v-dialog 
    v-model="dialog" 
    :max-width="maxWidth || '2100px'"
    persistent
  >
    <v-card>
      <v-card-title class="dialog-title">
        <span>{{ isEditMode ? '영역 수정' : '영역 추가' }}</span>
        <v-spacer></v-spacer>
        <v-btn icon @click="closeDialog">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>
      
      <v-card-text>
        <!-- 로딩 상태 표시 -->
        <div v-if="isLoading" class="loading-container">
          <v-progress-circular
            indeterminate
            color="primary"
            size="64"
          ></v-progress-circular>
          <div class="loading-text">데이터를 불러오는 중...</div>
        </div>
        
        <!-- 메인 컨텐츠 -->
        <div v-else-if="isDataReady" class="event-area">
          <v-container fluid>
            <!-- 입력 필드 영역 -->
            <v-row class="input-fields-row">
              <v-col cols="12">
                <div class="custom-input-group">
                  <label class="custom-label">영역 번호(ID)</label>
                  <select
                    v-model="roiId"
                    class="custom-select"
                  >
                    <option value="">영역 번호를 선택하세요</option>
                    <option v-for="i in 10" :key="i-1" :value="(i-1).toString()">{{ i-1 }}</option>
                  </select>
                </div>
              </v-col>
            </v-row>
            
            <v-row class="input-fields-row">
              <v-col cols="6">
                <div class="custom-input-group">
                  <label class="custom-label">start_point_x</label>
                  <input
                    v-model="startPointX"
                    type="text"
                    class="custom-input"
                    placeholder="시작점 X 좌표"
                  />
                </div>
              </v-col>
              <v-col cols="6">
                <div class="custom-input-group">
                  <label class="custom-label">start_point_y</label>
                  <input
                    v-model="startPointY"
                    type="text"
                    class="custom-input"
                    placeholder="시작점 Y 좌표"
                  />
                </div>
              </v-col>
            </v-row>
            
            <v-row class="input-fields-row">
              <v-col cols="6">
                <div class="custom-input-group">
                  <label class="custom-label">end_point_x</label>
                  <input
                    v-model="endPointX"
                    type="text"
                    class="custom-input"
                    placeholder="끝점 X 좌표"
                  />
                </div>
              </v-col>
              <v-col cols="6">
                <div class="custom-input-group">
                  <label class="custom-label">end_point_y</label>
                  <input
                    v-model="endPointY"
                    type="text"
                    class="custom-input"
                    placeholder="끝점 Y 좌표"
                  />
                </div>
              </v-col>
            </v-row>

            <!-- 파노라마 이미지 영역 -->
            <v-row class="video-row">
              <v-col cols="12">
                <div class="video-container panorama-container" @mouseleave="handleMouseLeave">
                  <!-- 파노라마 이미지 로딩 중 -->
                  <div 
                    v-if="isLoadingPanorama && !panoramaImage"
                    class="loading-panorama"
                  >
                    <v-progress-circular
                      indeterminate
                      color="primary"
                      size="64"
                    ></v-progress-circular>
                    <div class="loading-text">파노라마 이미지를 불러오는 중...</div>
                  </div>
                  <!-- 파노라마 이미지 표시 -->
                  <img 
                    v-if="panoramaImage"
                    :src="panoramaImage"
                    alt="Panorama"
                    class="panorama-image"
                    @load="onPanoramaImageLoad"
                    @error="onPanoramaImageError"
                  />
                  <!-- 파노라마 이미지 없음 (로딩 완료 후 이미지가 없는 경우) -->
                  <div 
                    v-if="!isLoadingPanorama && !panoramaImage"
                    class="loading-panorama"
                  >
                    <v-icon size="48" color="grey">mdi-image-off</v-icon>
                    <div class="loading-text">파노라마 이미지가 없습니다.</div>
                  </div>
                  <div 
                    class="selection-overlay"
                    v-if="panoramaImage && !isLoadingPanorama"
                    @mousedown="startDrag"
                    @mousemove="updateMousePosition"
                  >
                    <div 
                      class="selection-box"
                      v-if="isDragging || region"
                      :style="selectionBoxStyle"
                      :key="`selection-box-${isDragging}-${dragStart.x}-${dragStart.y}-${dragEnd.x}-${dragEnd.y}`"
                    ></div>
                    <div 
                      class="coordinate-display"
                      v-if="false"
                      :style="coordinateDisplayStyle"
                    >
                      X: {{ mousePosition.x }}px Y: {{ mousePosition.y }}px
                    </div>
                  </div>
                  <div 
                    class="detection-zone"
                    v-if="region && regionVisible && region.left !== undefined && region.top !== undefined && region.right !== undefined && region.bottom !== undefined"
                    :style="zoneStyle"
                    :key="`region-${region.left}-${region.top}-${region.right}-${region.bottom}-${Date.now()}`"
                  ></div>
                </div>
              </v-col>
            </v-row>

            <!-- 하단 버튼 영역 -->
            <v-row class="button-row">
              <v-col cols="12" class="text-center">
                <v-btn @click="closeDialog" class="cancel-btn">취소</v-btn>
                <v-btn @click="saveRoiArea" class="save-btn" :loading="isSaving">
                  {{ isEditMode ? '수정' : '저장' }}
                </v-btn>
              </v-col>
            </v-row>
          </v-container>
        </div>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script>
import { getCameras, getCameraSettings } from '@/api/cameras.api';
import { getPanoramaData } from '@/api/panorama.api';
import { mdiRefresh, mdiMapMarkerRadius, mdiCheckboxMarkedCircle, mdiUndo, mdiPlus, mdiPencil, mdiDelete } from '@mdi/js';
import { addEventDetectionZone, getEventDetectionZone, updateEventDetectionZone, deleteEventDetectionZone, updateInPageZone } from '@/api/eventDetectionZone.api';

export default {
  name: 'RoiWindow',

  components: {
  },

  props: {
    value: {
      type: Boolean,
      default: false
    },
    editData: {
      type: Object,
      default: null
    },
    isEditMode: {
      type: Boolean,
      default: false
    },
    roiTableData: {
      type: Array,
      default: () => []
    },
    checkDuplicate: {
      type: Function,
      default: null
    },
    maxWidth: {
      type: String,
      default: '2100px'
    }
  },

  data() {
    return {
      cameraList: [],
      selectedCameraName: '',
      selectedCamera: null,
      videoKey: '',
      refreshing: false,
      description: '',
      videoContainerWidth: 1920,
      videoContainerHeight: 480,
      panoramaImage: null,
      isLoadingPanorama: false, // 파노라마 이미지 로딩 상태
      icons: {
        mdiMapMarkerRadius,
        mdiCheckboxMarkedCircle,
        mdiUndo,
        mdiRefresh,
        mdiPlus,
        mdiPencil,
        mdiDelete
      },
      playgroundOptions: {},
      region: null,
      regionVisible: true, // region 표시 여부를 별도로 관리
      customizing: true, // 디폴트로 항상 드래그 가능하도록 true로 변경
      options: {
        forceCloseTimer: {
          label: 'Force Close Timer',
          value: 30
        },
        dwellTimer: {
          label: 'Dwell Timer',
          value: 50
        },
        sensitivity: {
          label: 'Sensitivity',
          value: 75
        },
        difference: {
          label: 'Difference',
          value: 50
        }
      },
      eventDetectionZoneList: [],
      tableHeaders: [
        { text: 'No', value: 'no', sortable: false },
        { text: '카메라', value: 'cameraName' },
        { text: '설명', value: 'description' },
        { text: '영역번호', value: 'type' },
        { text: '작업', value: 'actions', sortable: false, align: 'center' }
      ],
      deleteDialog: false,
      rowToDelete: null,
      editId: null,
      detectionZoneType: null,
      detectionZoneActive: true,
      detectionZoneTypes: Array.from({ length: 11 }, (_, i) => ({ text: i.toString(), value: i })),
      isDragging: false,
      dragStart: { x: 0, y: 0 },
      dragEnd: { x: 0, y: 0 },
      mousePosition: null,
      overlayRect: null, // selection-overlay의 rect를 저장
      imageOffset: { left: 0, top: 0 }, // 이미지의 컨테이너 내에서의 offset
      // 새로운 입력 필드들
      roiId: '',
      startPointX: '',
      startPointY: '',
      endPointX: '',
      endPointY: '',
      isSaving: false,
      isDataReady: false, // 데이터 준비 상태
      isLoading: false, // 로딩 상태
    };
  },

  computed: {
    dialog: {
      get() {
        return this.value;
      },
      set(value) {
        this.$emit('input', value);
      }
    },
    
    
    // 디버깅용 computed
    debugInfo() {
      return {
        editData: this.editData,
        isEditMode: this.isEditMode,
        dialog: this.dialog
      };
    },

    selectionBoxStyle() {
      if (this.isDragging) {
        // 드래그 중일 때 - 이미지 기준 좌표에 이미지 offset 추가
        const left = Math.min(this.dragStart.x, this.dragEnd.x);
        const top = Math.min(this.dragStart.y, this.dragEnd.y);
        const width = Math.abs(this.dragEnd.x - this.dragStart.x);
        const height = Math.abs(this.dragEnd.y - this.dragStart.y);
        
        // 최소 크기 보장 (드래그 시작 시에도 보이도록)
        const minSize = 1;
        const finalWidth = Math.max(width, minSize);
        const finalHeight = Math.max(height, minSize);
        
        const offsetLeft = this.imageOffset?.left || 0;
        const offsetTop = this.imageOffset?.top || 0;
        
        const style = {
          position: 'absolute',
          left: (left + offsetLeft) + 'px',
          top: (top + offsetTop) + 'px',
          width: finalWidth + 'px',
          height: finalHeight + 'px',
          display: 'block'
        };
        
        console.log('selectionBoxStyle (드래그 중):', {
          isDragging: this.isDragging,
          dragStart: this.dragStart,
          dragEnd: this.dragEnd,
          imageOffset: this.imageOffset,
          calculated: { left, top, width, height },
          final: { left: left + offsetLeft, top: top + offsetTop, width: finalWidth, height: finalHeight },
          style: style
        });
        
        return style;
      } else if (this.region) {
        // 그린 후 영역이 있을 때 - 이미지 기준 좌표에 이미지 offset 추가
        const offsetLeft = this.imageOffset?.left || 0;
        const offsetTop = this.imageOffset?.top || 0;
        
        const style = {
          position: 'absolute',
          left: (this.region.left + offsetLeft) + 'px',
          top: (this.region.top + offsetTop) + 'px',
          width: (this.region.right - this.region.left) + 'px',
          height: (this.region.bottom - this.region.top) + 'px',
          display: 'block'
        };
        
        console.log('selectionBoxStyle (region):', {
          region: this.region,
          imageOffset: this.imageOffset,
          style: style
        });
        
        return style;
      }
      console.log('selectionBoxStyle - 빈 객체 반환 (isDragging:', this.isDragging, ', region:', this.region, ')');
      return {};
    },

    coordinateDisplayStyle() {
      if (!this.mousePosition) return {};
      return {
        position: 'absolute',
        left: (this.mousePosition.x + this.imageOffset.left + 10) + 'px',
        top: (this.mousePosition.y + this.imageOffset.top + 10) + 'px',
        backgroundColor: 'rgba(0, 0, 0, 0.7)',
        color: 'white',
        padding: '4px 8px',
        borderRadius: '4px',
        fontSize: '12px',
        pointerEvents: 'none',
        zIndex: 1000
      };
    },

    zoneStyle() {
      console.log('zoneStyle 계산 시작 - region:', this.region, 'regionVisible:', this.regionVisible);
      
      if (!this.region || !this.regionVisible) {
        console.log('zoneStyle - 조건 불만족으로 빈 객체 반환');
        return {};
      }
      
      // region 객체의 유효성 검사
      if (typeof this.region.left === 'undefined' || 
          typeof this.region.top === 'undefined' || 
          typeof this.region.right === 'undefined' || 
          typeof this.region.bottom === 'undefined') {
        console.warn('region 객체에 필요한 속성이 없습니다:', this.region);
        return {};
      }
      
      // 픽셀 좌표를 직접 사용 (1920x480 파노라마 고정 크기) - 이미지 offset 추가
      const offsetLeft = this.imageOffset?.left || 0;
      const offsetTop = this.imageOffset?.top || 0;
      
      const style = {
        position: 'absolute',
        left: (this.region.left + offsetLeft) + 'px',
        top: (this.region.top + offsetTop) + 'px',
        width: (this.region.right - this.region.left) + 'px',
        height: (this.region.bottom - this.region.top) + 'px',
        border: '2px solid rgba(255, 255, 255, 0.5)',
        backgroundColor: 'rgba(255, 255, 255, 0.1)',
        pointerEvents: 'none',
        zIndex: 999 // 다른 요소들보다 위에 표시
      };
      
      console.log('zoneStyle 계산 완료:', style);
      return style;
    }
  },

  watch: {
    dialog(newVal) {
      if (newVal) {
        console.log('다이얼로그 열림 - 초기화 시작');
        
        // 로딩 상태 시작
        this.isLoading = true;
        this.isDataReady = false;
        
        // region 상태 강제 초기화
        this.region = null;
        this.regionVisible = false;
        
        // 강제 DOM 업데이트
        this.$forceUpdate();
        
        this.initializeData();
        
        // 다이얼로그가 열린 후 수정 데이터가 있으면 로드
        setTimeout(() => {
          // editData가 이미 있으면 즉시 로드, 없으면 나중에 로드될 때까지 대기
          if (this.editData && this.isEditMode) {
            console.log('수정 모드 - editData 로드 시작');
            this.loadEditData(this.editData);
          } else {
            console.log('추가 모드 또는 editData 없음 - 준비 완료');
            // 추가 모드이거나 editData가 없는 경우 바로 준비 완료
            this.prepareDataComplete();
          }
        }, 100);
      } else {
        console.log('다이얼로그 닫힘 - 상태 리셋');
        // 다이얼로그가 닫힐 때 상태 리셋
        this.isLoading = false;
        this.isDataReady = false;
        this.region = null;
        this.regionVisible = false;
      }
    },
    
    editData: {
      handler(newData) {
        if (newData && this.isEditMode && this.dialog) {
          // region 상태 초기화 후 데이터 로드
          this.region = null;
          this.regionVisible = false;
          this.$nextTick(() => {
            this.loadEditData(newData);
          });
        }
      },
      immediate: true
    },
    
    selectedCameraName(newName, oldName) {
      if (newName !== oldName) {
        if (!this.editId) {  // 수정 모드가 아닐 때만 초기화
          this.customizing = true; // 항상 true로 유지
          this.region = null;
          this.description = '';
          this.options = {
            forceCloseTimer: {
              label: 'Force Close Timer',
              value: 30
            },
            dwellTimer: {
              label: 'Dwell Timer',
              value: 50
            },
            sensitivity: {
              label: 'Sensitivity',
              value: 75
            },
            difference: {
              label: 'Difference',
              value: 50
            }
          };
        }
      }
      this.updateSelectedCamera(newName);
    }
  },

  mounted() {
            // region 표시 활성화
    // 컴포넌트 마운트 후 초기화
    this.$nextTick(() => {
      // 수정 모드이고 editData가 있으면 로드
      if (this.isEditMode && this.editData) {
        this.loadEditData(this.editData);
      }
      
      // 파노라마 이미지는 자동으로 로드됨
    });
  },

  methods: {
    closeDialog() {
      this.dialog = false;
    },

    prepareDataComplete() {
      console.log('데이터 준비 완료 - 화면 표시 시작');
      this.isLoading = false;
      this.isDataReady = true;
      
      // 이미지 offset 업데이트
      this.$nextTick(() => {
        this.updateImageOffset();
      });
    },

    loadEditData(data) {
      console.log('loadEditData 호출됨:', data);
      console.log('isEditMode:', this.isEditMode);
      
      // 수정 모드일 때 기존 데이터를 입력 필드에 설정
      this.roiId = data.roiId || '';
      this.startPointX = data.startPointX || '';
      this.startPointY = data.startPointY || '';
      this.endPointX = data.endPointX || '';
      this.endPointY = data.endPointY || '';
      
      console.log('입력 필드 설정 완료:', {
        roiId: this.roiId,
        startPointX: this.startPointX,
        startPointY: this.startPointY,
        endPointX: this.endPointX,
        endPointY: this.endPointY
      });
      
      // region 객체 생성
      if (data.startPointX && data.startPointY && data.endPointX && data.endPointY) {
        // 강제로 region을 null로 설정하고 DOM 업데이트 대기
        this.region = null;
        this.regionVisible = false;
        
        console.log('region 초기화 완료');
        
        // 강제 DOM 업데이트 후 region 설정
        this.$forceUpdate();
        
        setTimeout(() => {
          // 새로운 region 객체 생성
          const newRegion = {
            left: parseInt(data.startPointX),
            top: parseInt(data.startPointY),
            right: parseInt(data.endPointX),
            bottom: parseInt(data.endPointY),
            coords: [
              [parseInt(data.startPointX), parseInt(data.startPointY)],
              [parseInt(data.endPointX), parseInt(data.startPointY)],
              [parseInt(data.endPointX), parseInt(data.endPointY)],
              [parseInt(data.startPointX), parseInt(data.endPointY)]
            ]
          };
          
          console.log('새로운 region 객체:', newRegion);
          
          // Vue 반응형 시스템을 위해 $set 사용
          this.$set(this, 'region', newRegion);
          
          // region 표시 활성화
          this.$set(this, 'regionVisible', true);
          
          console.log('region 객체 설정 완료:', this.region);
          console.log('regionVisible:', this.regionVisible);
          
          // 강제 DOM 업데이트
          this.$forceUpdate();
          
          // 이미지 offset 업데이트
          this.$nextTick(() => {
            this.updateImageOffset();
          });
          
          // region 데이터 로딩 후 데이터 준비 완료
          setTimeout(() => {
            this.prepareDataComplete();
          }, 200);
        }, 100);
      } else {
        console.warn('editData에 좌표 정보가 없습니다:', data);
        // 좌표 정보가 없어도 데이터 준비 완료
        this.prepareDataComplete();
      }
    },

    async initializeData() {
      try {
        // 수정 모드가 아닐 때만 데이터 리셋
        if (!this.isEditMode) {
          this.areaNumber = 0;
          this.roiId = '';
          this.startPointX = '';
          this.startPointY = '';
          this.endPointX = '';
          this.endPointY = '';
          this.region = null;
        } else {
          // 수정 모드일 때는 region을 유지하고 editData가 있으면 로드
          if (this.editData) {
            this.loadEditData(this.editData);
          }
        }
        
        this.isDragging = false;
        this.dragStart = { x: 0, y: 0 };
        this.dragEnd = { x: 0, y: 0 };
        
        // 화면 진입시 updateInPageZone 호출 (1)
        await updateInPageZone(1);
        
        // 파노라마 이미지 로드
        await this.loadPanoramaImage();
        
        const response = await getCameras();
        for (const camera of response.data.result) {
          const settings = await getCameraSettings(camera.name);
          camera.settings = settings.data.settings;
          camera.favourite = camera.settings.camview.favourite;
          camera.live = camera.settings.camview.live || false;
          camera.refreshTimer = camera.settings.camview.refreshTimer || 60;
          camera.url = camera.videoConfig.source.replace(/\u00A0/g, ' ').split('-i ')[1];
          camera.videoType = camera.videoConfig?.videoType || 1;
          if (!camera.url.startsWith('/')) {
            const protocol = camera.url.split('://')[0];
            const url = new URL(camera.url.replace(protocol, 'http'));
            camera.url = `${protocol}://${url.hostname}:${url.port || 80}${url.pathname}`;
          }
        }
        this.cameraList = response.data.result;
        
        // videoType이 1인 카메라를 디폴트로 선택
        const thermalCamera = this.cameraList.find(camera => camera.videoType === 1);
        if (thermalCamera) {
          this.selectedCameraName = thermalCamera.name;
          this.updateSelectedCamera(this.selectedCameraName);
        } else if (this.cameraList.length > 0) {
          // videoType이 1인 카메라가 없으면 첫 번째 카메라 선택
          this.selectedCameraName = this.cameraList[0].name;
          this.updateSelectedCamera(this.selectedCameraName);
        }
        // detectionZoneType 초기값을 object로 설정
        if (this.detectionZoneTypes.length > 0) {
          this.detectionZoneType = this.detectionZoneTypes[0];
        }
        
        // 디폴트로 드래그 모드 활성화
        this.customizing = true;
      } catch (err) {
        this.$toast.error(err.message);
      }
      await this.loadEventDetectionZone();
    },

    async loadPanoramaImage() {
      // 로딩 상태 시작
      this.isLoadingPanorama = true;
      this.panoramaImage = null; // 이전 이미지 초기화
      
      try {
        // 최근 1장의 파노라마 이미지 가져오기
        console.log('파노라마 이미지 조회 시작...');
        const response = await getPanoramaData(1);
        console.log('파노라마 데이터 응답:', response);
        
        if (response.data && response.data.length > 0) {
          console.log(`파노라마 데이터 ${response.data.length}개 조회됨`);
          
          // 첫 번째(최신) 이미지 사용
          const panoramaData = response.data[0];
          try {
            const parsedData = JSON.parse(panoramaData.panoramaData);
            if (parsedData.image) {
              // 이미지 크기 확인
              const imageWidth = await this.getImageWidth(parsedData.image);
              console.log(`파노라마 이미지 크기 확인: ${imageWidth}px`);
              
              // 가로 크기가 1600 이상인 경우에만 사용
              if (imageWidth >= 1600) {
                console.log(`✅ 파노라마 이미지 선택: ${imageWidth}px`);
                // 이미지 소스 설정
                const imageSrc = `data:image/jpeg;base64,${parsedData.image}`;
                this.panoramaImage = imageSrc;
                console.log('panoramaImage 설정 완료:', this.panoramaImage ? '설정됨' : 'null');
                
                // 타임아웃 설정 (이미지 로드가 실패하거나 @load 이벤트가 발생하지 않을 경우 대비)
                const timeoutId = setTimeout(() => {
                  console.warn('이미지 로드 타임아웃 (3초) - 강제로 로딩 상태 해제');
                  this.isLoadingPanorama = false;
                }, 3000);
                
                // 이미지가 이미 로드되어 있을 경우를 대비해 체크
                this.$nextTick(() => {
                  setTimeout(() => {
                    const imgElement = this.$el?.querySelector('.panorama-image');
                    console.log('이미지 요소 확인:', imgElement ? '찾음' : '없음');
                    
                    if (imgElement) {
                      console.log('이미지 상태:', {
                        complete: imgElement.complete,
                        naturalWidth: imgElement.naturalWidth,
                        naturalHeight: imgElement.naturalHeight
                      });
                      
                      if (imgElement.complete && imgElement.naturalWidth > 0) {
                        // 이미 로드된 경우
                        console.log('이미지가 이미 로드되어 있음 - 즉시 표시');
                        clearTimeout(timeoutId);
                        this.isLoadingPanorama = false;
                        // CSS로 비율 유지 표시 (강제 설정 제거)
                        console.log('이미지 로드 완료 - CSS로 비율 유지 표시');
                      } else {
                        // 이미지 로드 대기 중 - @load 이벤트에서 처리됨
                        console.log('이미지 로드 대기 중... (@load 이벤트 대기)');
                        
                        // 추가 이벤트 리스너 (이중 체크)
                        imgElement.addEventListener('load', () => {
                          console.log('이미지 load 이벤트 리스너에서 로드 완료 확인');
                          clearTimeout(timeoutId);
                          this.isLoadingPanorama = false;
                          // CSS로 비율 유지 표시 (강제 설정 제거)
                          console.log('이미지 로드 완료 - CSS로 비율 유지 표시');
                        }, { once: true });
                      }
                    } else {
                      console.warn('이미지 요소를 찾을 수 없음');
                    }
                  }, 200); // DOM 업데이트 대기
                });
              } else {
                this.panoramaImage = null;
                this.isLoadingPanorama = false;
                console.warn(`이미지 크기 부족: ${imageWidth}px < 1600px`);
                this.$toast.warning('가로 크기 1600px 이상인 파노라마 이미지를 찾을 수 없습니다.');
              }
            } else {
              this.panoramaImage = null;
              this.isLoadingPanorama = false;
              console.warn('이미지 데이터 없음');
              this.$toast.warning('파노라마 이미지 데이터가 없습니다.');
            }
          } catch (error) {
            console.error('파노라마 데이터 파싱 오류:', error);
            this.panoramaImage = null;
            this.isLoadingPanorama = false;
            this.$toast.error('파노라마 이미지 데이터 파싱에 실패했습니다.');
          }
        } else {
          this.panoramaImage = null;
          this.isLoadingPanorama = false;
          console.warn('파노라마 데이터가 없습니다.');
          this.$toast.warning('파노라마 데이터가 없습니다.');
        }
      } catch (error) {
        console.error('파노라마 이미지 로드 오류:', error);
        this.panoramaImage = null;
        this.isLoadingPanorama = false;
        this.$toast.error('파노라마 이미지를 불러올 수 없습니다.');
      }
    },
    
    // 파노라마 이미지 로드 완료 핸들러
        onPanoramaImageLoad(event) {
          console.log('파노라마 이미지 @load 이벤트 발생');
          if (event && event.target) {
            console.log('이미지 크기:', event.target.naturalWidth, 'x', event.target.naturalHeight);
            // CSS로 비율 유지 표시 (강제 설정 제거)
            console.log('이미지 로드 완료 - CSS로 비율 유지 표시');
          }
          this.isLoadingPanorama = false;
          console.log('파노라마 이미지 로드 완료 - 로딩 상태 해제');
          
          // 이미지 위치 업데이트
          this.$nextTick(() => {
            this.updateImageOffset();
          });
        },
    
    // 파노라마 이미지 로드 오류 핸들러
    onPanoramaImageError(event) {
      console.error('파노라마 이미지 로드 오류:', event);
      this.isLoadingPanorama = false;
      this.panoramaImage = null;
      this.$toast.error('파노라마 이미지 로드에 실패했습니다.');
    },
    
    // 이미지 가로 크기 확인 함수
    getImageWidth(imageBase64) {
      return new Promise((resolve, reject) => {
        try {
          const img = new Image();
          img.onload = () => {
            resolve(img.naturalWidth || img.width);
          };
          img.onerror = () => {
            reject(new Error('이미지 로드 실패'));
          };
          img.src = `data:image/jpeg;base64,${imageBase64}`;
        } catch (error) {
          reject(error);
        }
      });
    },

    async updateSelectedCamera(name) {
      const camera = this.cameraList.find(cam => cam.name === name);
      if (camera) {
        this.selectedCamera = { ...camera };
        this.videoKey = camera.name + '_' + Date.now();
        this.$nextTick(() => {
          this.updateVideoContainerSize();
        });
      }
    },

    updateVideoContainerSize() {
      // 고정된 파노라마 이미지 크기 설정
      this.videoContainerWidth = 1920;
      this.videoContainerHeight = 480;
    },


    async refreshVideo() {
      if (this.refreshing || !this.selectedCamera) return;
      this.refreshing = true;
      try {
        const videoCard = this.$refs[this.selectedCamera.name];
        if (videoCard) {
          await this.cleanupVideoResources(videoCard, this.selectedCamera.name);
        }
        const response = await getCameras();
        const camera = response.data.result.find(cam => cam.name === this.selectedCamera.name);
        if (camera) {
          const settings = await getCameraSettings(camera.name);
          camera.settings = settings.data;
          camera.favourite = camera.settings.camview.favourite;
          camera.live = camera.settings.camview.live || false;
          camera.refreshTimer = camera.settings.camview.refreshTimer || 60;
          if (!camera.videoConfig || !camera.videoConfig.source) {
            this.$toast.error(`${camera.name} 영상 소스가 없습니다.`);
            this.refreshing = false;
            return;
          }
          camera.url = camera.videoConfig.source.replace(/\u00A0/g, ' ').split('-i ')[1];
          if (!camera.url.startsWith('/')) {
            const protocol = camera.url.split('://')[0];
            const url = new URL(camera.url.replace(protocol, 'http'));
            camera.url = `${protocol}://${url.hostname}:${url.port || 80}${url.pathname}`;
          }
          this.selectedCamera = { ...camera };
          this.videoKey = camera.name + '_' + Date.now();
        }
      } catch (err) {
        this.$toast.error(err.message);
      } finally {
        this.refreshing = false;
      }
    },

    async cleanupVideoResources(videoCard, cameraName) {
      this.$socket.client.emit('leave_stream', { feed: cameraName });
      if (videoCard.player) {
        try {
          videoCard.player.destroy();
          videoCard.player = null;
        } catch (error) {
          console.warn('Error destroying player:', error);
        }
      }
      this.$socket.client.off(cameraName);
      videoCard.loading = true;
      videoCard.offline = false;
      videoCard.play = false;
    },

    addHandle(e) {
      const x = Math.round((e.offsetX / this.videoContainerWidth) * 100);
      const y = Math.round((e.offsetY / this.videoContainerHeight) * 100);
      let regionIndex = this.regions.length - 1;
      if (
        !this.regions.length ||
        (this.regions[regionIndex] && this.regions[regionIndex].finished)
      ) {
        this.regions.push({
          finished: false,
          coords: [],
        });
        regionIndex = this.regions.length - 1;
      }
      this.regions[regionIndex].coords.push([x, y]);
    },

    updateHandle(payload) {
      const x = Math.round((payload.x / this.videoContainerWidth) * 100);
      const y = Math.round((payload.y / this.videoContainerHeight) * 100);
      this.$set(this.regions[payload.regionIndex].coords, payload.coordIndex, [x, y]);
    },

    undo() {
      if (!this.regions.length) return;
      const rIndex = this.regions.length - 1;
      this.regions[rIndex].coords.pop();
      if (!this.regions[rIndex].coords.length) {
        this.regions.splice(rIndex, 1);
      }
    },

    clear() {
      this.region = null;
    },

    startCustom() {
      this.customizing = true;
      this.editId = null;
      this.region = null;
      this.description = '';
      this.detectionZoneType = null;
      this.detectionZoneActive = true;
      this.options = {
        forceCloseTimer: {
          label: 'Force Close Timer',
          value: 30
        },
        dwellTimer: {
          label: 'Dwell Timer',
          value: 50
        },
        sensitivity: {
          label: 'Sensitivity',
          value: 75
        },
        difference: {
          label: 'Difference',
          value: 50
        }
      };
    },

    finishCustom() {
      this.customizing = true; // 항상 true로 유지
      this.editId = null;
      this.region = null;
      this.description = '';
      this.detectionZoneType = null;
      this.detectionZoneActive = true;
      this.options = {
        forceCloseTimer: {
          label: 'Force Close Timer',
          value: 30
        },
        dwellTimer: {
          label: 'Dwell Timer',
          value: 50
        },
        sensitivity: {
          label: 'Sensitivity',
          value: 75
        },
        difference: {
          label: 'Difference',
          value: 50
        }
      };
    },

    updateOptions() {
      this.$emit('options-updated', {
        forceCloseTimer: this.options.forceCloseTimer.value,
        dwellTimer: this.options.dwellTimer.value,
        sensitivity: this.options.sensitivity.value,
        difference: this.options.difference.value,
        description: this.description,
        type: this.detectionZoneType ? this.detectionZoneType.value : null,
        active: this.detectionZoneActive
      });
    },

    async add() {
      if (!this.selectedCamera) {
        this.$toast.error('카메라를 선택해주세요.');
        return;
      }

      if (!this.region) {
        this.$toast.error('감지 영역을 설정해주세요.');
        return;
      }

      if (!this.description || this.description.trim() === '') {
        this.$toast.error('설명을 입력해주세요.');
        return;
      }
      
      // 중복 영역 번호 체크
      const isDuplicateType = this.eventDetectionZoneList.some(
        zone => Number(zone.type) === Number(this.detectionZoneType?.value)
      );
      if (isDuplicateType) {
        this.$toast.error('동일한 영역 번호가 이미 존재합니다.');
        return;
      }

      const cameraId = this.cameraList.findIndex(cam => cam.name === this.selectedCamera.name);
      const currentType = Number(this.detectionZoneType?.value);
      const roiEnableArr = Array(10).fill('0');
      this.eventDetectionZoneList.forEach(zone => {
        const t = Number(zone.type);
        if (!isNaN(t) && t >= 0 && t <= 9) {
          roiEnableArr[9 - t] = '1'; // 0번이 오른쪽
        }
      });
      if (!isNaN(currentType) && currentType >= 0 && currentType <= 9) {
        roiEnableArr[9 - currentType] = '1';
      }
      const roiEnable = roiEnableArr.join('');
      const roiIndex = (!isNaN(currentType) && currentType >= 0 && currentType <= 10) ? currentType : 0;
      const exist = this.eventDetectionZoneList.find(e => e.id === this.editId);
      const eventDetectionZoneData = {
        cameraId,
        options: {
          forceCloseTimer: this.options.forceCloseTimer.value,
          dwellTimer: this.options.dwellTimer.value,
          sensitivity: this.options.sensitivity.value,
          difference: this.options.difference.value
        },
        regions: [this.region],
        description: this.description,
        type: this.detectionZoneType ? this.detectionZoneType.value : null,
        active: this.detectionZoneActive,
        roiIndex: roiIndex,
        roiEnable: roiEnable
      };
      if (exist) {
        // 수정
        await updateEventDetectionZone(exist.id, eventDetectionZoneData);
        this.$toast.success('수정되었습니다.');
      } else {
        // 추가
        await addEventDetectionZone(eventDetectionZoneData);
        this.$toast.success('이벤트 감지 영역이 저장되었습니다.');
      }
      this.clear();
      this.description = '';
      this.editId = null;
      this.detectionZoneType = null;
      this.detectionZoneActive = true;
      this.customizing = true; // 항상 true로 유지
      await this.loadEventDetectionZone();
    },
  
    async loadEventDetectionZone() {
      try {
        const res = await getEventDetectionZone();
        this.eventDetectionZoneList = Array.isArray(res.data) ? res.data : (Array.isArray(res) ? res : []);
      } catch (e) {
        console.error('eventDetectionZone API error:', e);
        this.eventDetectionZoneList = [];
      }
    },

    getCameraName(cameraId) {
      return this.cameraList[cameraId]?.name || '';
    },

    onRowClick(item) {
      this.editId = item.id;
      this.selectedCameraName = this.getCameraName(item.cameraId);
      this.options.forceCloseTimer.value = item.options.forceCloseTimer;
      this.options.dwellTimer.value = item.options.dwellTimer;
      this.options.sensitivity.value = item.options.sensitivity;
      this.options.difference.value = item.options.difference;
      
      // Use stored coordinates directly for 1920x480 panorama fixed size
      const storedRegion = item.regions[0];
      if (storedRegion) {
        this.region = {
          left: Math.round(storedRegion.left),
          top: Math.round(storedRegion.top),
          right: Math.round(storedRegion.right),
          bottom: Math.round(storedRegion.bottom),
          coords: storedRegion.coords.map(coord => [
            Math.round(coord[0]),
            Math.round(coord[1])
          ])
        };
      }
      
      this.description = item.description;
      this.detectionZoneType = this.detectionZoneTypes.find(t => t.value === Number(item.type));
      this.detectionZoneActive = item.active;
      this.customizing = true;
    },

    async editRow(item) {
      const found = this.detectionZoneTypes.find(t => t.value === Number(item.type));
      this.detectionZoneType = found || this.detectionZoneTypes[0];
      this.editId = item.id;
      this.selectedCameraName = this.getCameraName(item.cameraId);
      this.options.forceCloseTimer.value = item.options.forceCloseTimer;
      this.options.dwellTimer.value = item.options.dwellTimer;
      this.options.sensitivity.value = item.options.sensitivity;
      this.options.difference.value = item.options.difference;
      
      // Use stored coordinates directly for 1920x480 panorama fixed size
      const storedRegion = item.regions[0];
      if (storedRegion) {
        this.region = {
          left: Math.round(storedRegion.left),
          top: Math.round(storedRegion.top),
          right: Math.round(storedRegion.right),
          bottom: Math.round(storedRegion.bottom),
          coords: storedRegion.coords.map(coord => [
            Math.round(coord[0]),
            Math.round(coord[1])
          ])
        };
      }
      
      this.description = item.description;
      this.detectionZoneActive = item.active;
      this.customizing = true;
    },

    confirmDelete(item) {
      this.rowToDelete = item;
      this.deleteDialog = true;
    },

    async deleteRow() {
      if (this.rowToDelete) {
        // 삭제 후 남은 리스트로 roiEnable 계산
        const remainList = this.eventDetectionZoneList.filter(e => e.id !== this.rowToDelete.id);
        const roiEnableArr = Array(10).fill('0');
        remainList.forEach(zone => {
          const t = Number(zone.type);
          if (!isNaN(t) && t >= 0 && t <= 9) {
            roiEnableArr[9 - t] = '1';
          }
        });
        const roiEnable = roiEnableArr.join('');
        const roiIndex = Number(this.rowToDelete.type);
        await deleteEventDetectionZone(`${this.rowToDelete.id}?roiEnable=${roiEnable}&roiIndex=${roiIndex}`);
        this.$toast.success('삭제되었습니다.');
        this.deleteDialog = false;
        this.rowToDelete = null;
        await this.loadEventDetectionZone();
      }
    },

    getTypeText(type) {
      const typeItem = this.detectionZoneTypes.find(t => t.value === type);
      return typeItem ? typeItem.text : type;
    },

    handleMouseLeave() {
      if (this.isDragging) {
        // 전역 이벤트 리스너 제거
        document.removeEventListener('mousemove', this.onDrag);
        document.removeEventListener('mouseup', this.endDrag);
        
        this.isDragging = false;
        this.dragStart = { x: 0, y: 0 };
        this.dragEnd = { x: 0, y: 0 };
        this.mousePosition = null;
        this.overlayRect = null;
      }
    },

    updateImageOffset() {
      // 이미지의 컨테이너 내에서의 offset 계산
      const imgElement = this.$el?.querySelector('.panorama-image');
      const containerElement = this.$el?.querySelector('.video-container');
      
      if (imgElement && containerElement) {
        const imgRect = imgElement.getBoundingClientRect();
        const containerRect = containerElement.getBoundingClientRect();
        
        // 이미지의 컨테이너 내에서의 상대 위치 계산
        this.imageOffset = {
          left: imgRect.left - containerRect.left,
          top: imgRect.top - containerRect.top
        };
        
        console.log('이미지 offset 업데이트:', {
          imgRect: { left: imgRect.left, top: imgRect.top, width: imgRect.width, height: imgRect.height },
          containerRect: { left: containerRect.left, top: containerRect.top, width: containerRect.width, height: containerRect.height },
          imageOffset: this.imageOffset
        });
      } else {
        console.warn('updateImageOffset - 요소를 찾을 수 없음:', {
          imgElement: !!imgElement,
          containerElement: !!containerElement
        });
        // 기본값 설정
        this.imageOffset = { left: 0, top: 0 };
      }
    },
    
    startDrag(event) {
      // customizing을 강제로 true로 설정하여 항상 드래그 가능하도록 변경
      this.customizing = true;
      
      // selection-overlay 요소를 직접 찾아서 rect 저장
      const overlayElement = event.currentTarget || event.target.closest('.selection-overlay');
      if (!overlayElement) {
        console.error('selection-overlay 요소를 찾을 수 없습니다.');
        return;
      }
      
      const overlayRect = overlayElement.getBoundingClientRect();
      this.overlayRect = overlayRect; // rect 저장
      
      // DOM 업데이트를 기다린 후 이미지 요소 찾기
      this.$nextTick(() => {
        // 이미지 offset 업데이트
        this.updateImageOffset();
        
        // 실제 이미지 요소의 렌더링 크기와 위치 가져오기
        const imgElement = this.$el?.querySelector('.panorama-image');
        
        let imageWidth = this.videoContainerWidth; // 기본값: 1920
        let imageHeight = this.videoContainerHeight; // 기본값: 480
        let imageLeft = overlayRect.left; // overlay 기준으로 시작
        let imageTop = overlayRect.top; // overlay 기준으로 시작
        
        if (imgElement) {
          const imgRect = imgElement.getBoundingClientRect();
          imageWidth = imgRect.width;
          imageHeight = imgRect.height;
          imageLeft = imgRect.left; // 이미지의 실제 시작 X 좌표
          imageTop = imgRect.top; // 이미지의 실제 시작 Y 좌표
        } else {
          console.warn('panorama-image 요소를 찾을 수 없습니다. overlay 기준으로 계산합니다.');
          // 이미지 offset이 있으면 사용
          if (this.imageOffset && this.imageOffset.left > 0) {
            imageLeft = overlayRect.left + this.imageOffset.left;
            imageTop = overlayRect.top + this.imageOffset.top;
          }
        }
        
        console.log('startDrag - 크기 정보:', {
          imageWidth: imageWidth,
          imageHeight: imageHeight,
          imageLeft: imageLeft,
          imageTop: imageTop,
          imageOffset: this.imageOffset,
          overlayRect: overlayRect
        });
        
        // 이미지의 시작 위치를 기준으로 좌표 계산
        const normalizedX = event.clientX - imageLeft;
        const normalizedY = event.clientY - imageTop;
        
        // 이미지 크기 범위를 벗어나지 않도록 제한
        const clampedX = Math.max(0, Math.min(imageWidth, Math.round(normalizedX)));
        const clampedY = Math.max(0, Math.min(imageHeight, Math.round(normalizedY)));
        
        this.isDragging = true;
        this.dragStart = {
          x: clampedX,
          y: clampedY
        };
        // 초기에는 dragEnd를 약간 오프셋하여 최소 크기 보장
        this.dragEnd = {
          x: clampedX + 1,
          y: clampedY + 1
        };
        
        console.log('startDrag 완료:', {
          isDragging: this.isDragging,
          dragStart: this.dragStart,
          dragEnd: this.dragEnd,
          imageOffset: this.imageOffset
        });
        
        // Vue 반응성 보장을 위해 강제 업데이트
        this.$forceUpdate();
        
        this.updateMousePosition(event);
        
        // 전역 mousemove와 mouseup 이벤트 리스너 추가
        document.addEventListener('mousemove', this.onDrag);
        document.addEventListener('mouseup', this.endDrag);
        
        // Clear existing region when starting new drag
        this.region = null;
      });
    },
    
    onDrag(event) {
      if (!this.isDragging) return;
      
      // 이미지 offset 업데이트 (윈도우 리사이즈 등으로 변경될 수 있음)
      this.updateImageOffset();
      
      // overlay rect가 없으면 다시 계산
      let overlayRect = this.overlayRect;
      if (!overlayRect) {
        const overlayElement = this.$el?.querySelector('.selection-overlay');
        if (overlayElement) {
          overlayRect = overlayElement.getBoundingClientRect();
          this.overlayRect = overlayRect;
        }
      }
      
      // 실제 이미지 요소의 렌더링 크기와 위치 가져오기
      const imgElement = this.$el?.querySelector('.panorama-image');
      
      let imageWidth = this.videoContainerWidth; // 기본값: 1920
      let imageHeight = this.videoContainerHeight; // 기본값: 480
      let imageLeft = overlayRect ? overlayRect.left : 0;
      let imageTop = overlayRect ? overlayRect.top : 0;
      
      if (imgElement) {
        const imgRect = imgElement.getBoundingClientRect();
        imageWidth = imgRect.width;
        imageHeight = imgRect.height;
        imageLeft = imgRect.left; // 이미지의 실제 시작 X 좌표
        imageTop = imgRect.top; // 이미지의 실제 시작 Y 좌표
      } else if (overlayRect && this.imageOffset) {
        // 이미지 요소를 찾지 못했지만 overlay와 offset이 있으면 사용
        imageLeft = overlayRect.left + (this.imageOffset.left || 0);
        imageTop = overlayRect.top + (this.imageOffset.top || 0);
      }
      
      // 이미지의 시작 위치를 기준으로 좌표 계산
      const normalizedX = event.clientX - imageLeft;
      const normalizedY = event.clientY - imageTop;
      
      // 이미지 크기 범위를 벗어나지 않도록 제한
      const clampedX = Math.max(0, Math.min(imageWidth, Math.round(normalizedX)));
      const clampedY = Math.max(0, Math.min(imageHeight, Math.round(normalizedY)));
      
      this.dragEnd = {
        x: clampedX,
        y: clampedY
      };
      
      console.log('onDrag 업데이트:', {
        dragStart: this.dragStart,
        dragEnd: this.dragEnd,
        imageOffset: this.imageOffset,
        imageWidth: imageWidth,
        imageHeight: imageHeight
      });

      // Vue 반응성 보장을 위해 강제 업데이트
      this.$forceUpdate();

      // Update mouse position for coordinate display
      this.updateMousePosition(event);
    },
    
    updateMousePosition(event) {
      // 실제 이미지 요소의 렌더링 크기와 위치 가져오기
      const imgElement = this.$el?.querySelector('.panorama-image');
      
      let imageWidth = this.videoContainerWidth; // 기본값: 1920
      let imageHeight = this.videoContainerHeight; // 기본값: 480
      let imageLeft = 0;
      let imageTop = 0;
      
      if (imgElement) {
        const imgRect = imgElement.getBoundingClientRect();
        imageWidth = imgRect.width;
        imageHeight = imgRect.height;
        imageLeft = imgRect.left; // 이미지의 실제 시작 X 좌표
        imageTop = imgRect.top; // 이미지의 실제 시작 Y 좌표
      } else if (this.overlayRect && this.imageOffset) {
        // 이미지 요소를 찾지 못했지만 overlay와 offset이 있으면 사용
        imageLeft = this.overlayRect.left + (this.imageOffset.left || 0);
        imageTop = this.overlayRect.top + (this.imageOffset.top || 0);
      } else {
        // 요소를 찾을 수 없으면 좌표 표시하지 않음
        return;
      }
      
      // 이미지의 시작 위치를 기준으로 좌표 계산
      const normalizedX = event.clientX - imageLeft;
      const normalizedY = event.clientY - imageTop;
      
      // 이미지 크기 범위를 벗어나지 않도록 제한
      const x = Math.max(0, Math.min(imageWidth, Math.round(normalizedX)));
      const y = Math.max(0, Math.min(imageHeight, Math.round(normalizedY)));
      this.mousePosition = { x, y };
    },
    
    endDrag() {
      if (!this.isDragging) return;
      
      // 전역 이벤트 리스너 제거
      document.removeEventListener('mousemove', this.onDrag);
      document.removeEventListener('mouseup', this.endDrag);
      
      this.isDragging = false;
      
      // Only create region if we have valid coordinates
      if (this.dragStart.x !== 0 && this.dragStart.y !== 0 && 
          this.dragEnd.x !== 0 && this.dragEnd.y !== 0) {
        // Get pixel coordinates for 1920x480 panorama fixed size
        const left = Math.round(Math.min(this.dragStart.x, this.dragEnd.x));
        const top = Math.round(Math.min(this.dragStart.y, this.dragEnd.y));
        const right = Math.round(Math.max(this.dragStart.x, this.dragEnd.x));
        const bottom = Math.round(Math.max(this.dragStart.y, this.dragEnd.y));
        
        // Create a single region with pixel coordinates
        this.$set(this, 'region', {
          left,
          top,
          right,
          bottom,
          coords: [
            [left, top],
            [right, top],
            [right, bottom],
            [left, bottom]
          ]
        });
        
        // region 표시 활성화
        this.$set(this, 'regionVisible', true);
        
        // Update input fields with coordinates
        this.startPointX = left.toString();
        this.startPointY = top.toString();
        this.endPointX = right.toString();
        this.endPointY = bottom.toString();
        
        console.log('Region coordinates (1920x480):', {
          left,
          top,
          right,
          bottom,
          width: right - left,
          height: bottom - top
        });
        
        this.$emit('updateHandle', { region: this.region });
      }
      
      this.mousePosition = null;
    },
    
    getZoneStyle(zone) {
      // 픽셀 좌표를 직접 사용 (1920x480 파노라마 고정 크기)
      const style = {
        position: 'absolute',
        left: zone.left + 'px',
        top: zone.top + 'px',
        width: (zone.right - zone.left) + 'px',
        height: (zone.bottom - zone.top) + 'px',
        border: '2px solid rgba(255, 255, 255, 0.5)',
        backgroundColor: 'rgba(255, 255, 255, 0.1)',
        pointerEvents: 'none'
      };
      
      return style;
    },

    async saveRoiArea() {
      if (!this.region) {
        this.$toast.error('감지 영역을 설정해주세요.');
        return;
      }

      if (!this.roiId || this.roiId.trim() === '') {
        this.$toast.error('영역 번호를 입력해주세요.');
        return;
      }

      // 중복 영역 번호 체크 (추가 모드일 때만)
      if (!this.isEditMode && this.checkDuplicate) {
        const isDuplicate = this.checkDuplicate(this.roiId);
        if (isDuplicate) {
          this.$toast.error('동일한 영역 번호가 이미 존재합니다.');
          return;
        }
      }

      // 수정 모드일 때는 현재 편집 중인 항목을 제외하고 중복 체크
      if (this.isEditMode && this.checkDuplicate && this.editData && this.editData.id) {
        const isDuplicate = this.checkDuplicate(this.roiId, this.editData.id);
        if (isDuplicate) {
          this.$toast.error('동일한 영역 번호가 이미 존재합니다.');
          return;
        }
      }

      this.isSaving = true;

      try {
        // roiEnable 계산 로직 - 모화면의 ROI 데이터를 사용
        const roiEnableArr = Array(10).fill('0');
        this.roiTableData.forEach(zone => {
          const t = Number(zone.areaNumber);
          if (!isNaN(t) && t >= 0 && t <= 9) {
            roiEnableArr[9 - t] = '1'; // 0번이 오른쪽
          }
        });
        
        // 현재 추가/수정하는 영역도 포함
        const currentAreaNumber = parseInt(this.roiId);
        if (!isNaN(currentAreaNumber) && currentAreaNumber >= 0 && currentAreaNumber <= 9) {
          roiEnableArr[9 - currentAreaNumber] = '1';
        }
        
        const roiEnable = roiEnableArr.join('');
        console.log('계산된 roiEnable:', roiEnable);

        const roiData = {
          cameraId: this.cameraList.findIndex(cam => cam.name === this.selectedCamera.name),
          options: this.options,
          regions: [this.region],
          description: `ROI ${this.roiId}`,
          type: parseInt(this.roiId),
          active: true,
          roiIndex: parseInt(this.roiId) - 1,
          roiEnable: roiEnable
        };

        let response;
        if (this.isEditMode && this.editData && this.editData.id) {
          // 수정 모드
          response = await updateEventDetectionZone(this.editData.id, roiData);
          console.log('ROI 수정 응답:', response);
          this.$toast.success('영역이 수정되었습니다.');
        } else {
          // 추가 모드
          response = await addEventDetectionZone(roiData);
          console.log('ROI 추가 응답:', response);
          this.$toast.success('새로운 영역이 추가되었습니다.');
        }
        
        if (response) {
          this.dialog = false;
          this.$emit('saved'); // 부모 컴포넌트에 저장 완료 알림
        }
      } catch (error) {
        console.error('ROI 저장 오류:', error);
        this.$toast.error(this.isEditMode ? '영역 수정 중 오류가 발생했습니다.' : '영역 추가 중 오류가 발생했습니다.');
      } finally {
        this.isSaving = false;
      }
    },
    
  },

  beforeDestroy() {
    // 전역 이벤트 리스너 정리
    document.removeEventListener('mousemove', this.onDrag);
    document.removeEventListener('mouseup', this.endDrag);
  }
};
</script>

<style lang="scss">
// 전역 스타일 - 입력 필드 배경색 강제 설정
::v-deep .v-text-field {
  background-color: white !important;
}

::v-deep .v-text-field .v-input__control {
  background-color: white !important;
}

::v-deep .v-text-field .v-input__control .v-input__slot {
  background-color: white !important;
  box-shadow: none !important;
}

::v-deep .v-text-field .v-input__control .v-input__slot .v-text-field__slot {
  background-color: white !important;
}

::v-deep .v-text-field .v-input__control .v-input__slot .v-text-field__slot input {
  background-color: white !important;
  color: black !important;
}

.dialog-title {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-bottom: 1px solid #e0e0e0;
  text-align: center;
  font-weight: bold;
}

// v-dialog와 v-card-text의 기본 여백 제거 및 가로 스크롤 방지
::v-deep .v-dialog {
  overflow-x: hidden !important;
}

::v-deep .v-dialog .v-card {
  overflow-x: hidden !important;
  max-width: 100% !important;
}

::v-deep .v-dialog .v-card__text {
  padding: 16px !important;
  overflow-x: hidden !important;
  max-width: 100% !important;
}

.event-area {
  padding: 20px;
  background-color: white; // 배경을 흰색으로 변경
  width: 100%;
  min-width: 1960px; // 최소 너비 보장 (1920px + 40px padding)
  margin: 0 auto; // 중앙 정렬
  box-sizing: border-box;
  overflow-x: auto; // 필요시 가로 스크롤 허용

  .input-fields-row {
    margin-bottom: 0; // 간격 제거
    padding: 0; // 패딩 제거
    
    .custom-input-group {
      display: flex;
      flex-direction: row; // 수평 배치로 변경
      align-items: center; // 세로 중앙 정렬
      margin-bottom: 0; // 간격 제거
      padding: 0; // 패딩 제거
      
      .custom-label {
        font-size: 14px;
        color: black;
        margin-right: 10px; // 오른쪽 여백
        margin-bottom: 0; // 하단 여백 제거
        font-weight: 500;
        min-width: 120px; // 라벨 최소 너비 고정
        flex-shrink: 0; // 라벨 크기 고정
      }
      
      .custom-input {
        flex: 1; // 남은 공간 모두 차지
        padding: 8px 12px; // 패딩 줄임
        border: 2px solid #e0e0e0;
        border-radius: 4px;
        background-color: white;
        color: black;
        font-size: 14px;
        outline: none;
        transition: border-color 0.3s ease;
        box-sizing: border-box;
        display: block;
        min-height: 36px; // 높이 줄임
        line-height: 1.5;
        margin: 0; // 마진 제거
        
        &:focus {
          border-color: #1976d2;
          box-shadow: 0 0 0 2px rgba(25, 118, 210, 0.2);
        }
        
        &::placeholder {
          color: #999;
        }
        
        &:hover {
          border-color: #bdbdbd;
        }
        
        // 테두리가 보이지 않을 경우를 대비한 추가 스타일
        &:not(:focus):not(:hover) {
          border: 2px solid #e0e0e0 !important;
        }
      }
      
      .custom-select {
        flex: 1; // 남은 공간 모두 차지
        padding: 8px 12px; // 패딩 줄임
        border: 2px solid #e0e0e0;
        border-radius: 4px;
        background-color: white;
        color: black;
        font-size: 14px;
        outline: none;
        transition: border-color 0.3s ease;
        box-sizing: border-box;
        display: block;
        min-height: 36px; // 높이 줄임
        line-height: 1.5;
        margin: 0; // 마진 제거
        cursor: pointer;
        
        &:focus {
          border-color: #1976d2;
          box-shadow: 0 0 0 2px rgba(25, 118, 210, 0.2);
        }
        
        &:hover {
          border-color: #bdbdbd;
        }
        
        // 테두리가 보이지 않을 경우를 대비한 추가 스타일
        &:not(:focus):not(:hover) {
          border: 2px solid #e0e0e0 !important;
        }
        
        option {
          background-color: white;
          color: black;
          padding: 8px;
        }
      }
    }
    
    .input-field {
      // 모든 Vuetify 텍스트 필드 스타일 오버라이드
      ::v-deep .v-text-field {
        background-color: white !important;
      }
      
      ::v-deep .v-text-field .v-input__control {
        background-color: white !important;
      }
      
      ::v-deep .v-text-field .v-input__control .v-input__slot {
        background-color: white !important;
        box-shadow: none !important;
        border: 1px solid #e0e0e0 !important;
      }
      
      ::v-deep .v-text-field .v-input__control .v-input__slot .v-text-field__slot {
        background-color: white !important;
      }
      
      ::v-deep .v-text-field .v-input__control .v-input__slot .v-text-field__slot input {
        background-color: white !important;
        color: black !important;
      }
      
      // 라벨 색상
      ::v-deep .v-text-field .v-label {
        color: black !important;
      }
      
      // 플레이스홀더 색상
      ::v-deep .v-text-field .v-text-field__slot input::placeholder {
        color: #666 !important;
      }
      
      // 포커스 상태에서도 흰색 유지
      ::v-deep .v-text-field.v-input--is-focused .v-input__control .v-input__slot {
        background-color: white !important;
      }
      
      ::v-deep .v-text-field.v-input--is-focused .v-input__control .v-input__slot .v-text-field__slot {
        background-color: white !important;
      }
      
      ::v-deep .v-text-field.v-input--is-focused .v-input__control .v-input__slot .v-text-field__slot input {
        background-color: white !important;
      }
      
      // 호버 상태에서도 흰색 유지
      ::v-deep .v-text-field:hover .v-input__control .v-input__slot {
        background-color: white !important;
      }
      
      ::v-deep .v-text-field:hover .v-input__control .v-input__slot .v-text-field__slot {
        background-color: white !important;
      }
      
      ::v-deep .v-text-field:hover .v-input__control .v-input__slot .v-text-field__slot input {
        background-color: white !important;
      }
    }
  }

  .video-row {
    margin-bottom: 20px;
    margin-left: 0 !important;
    margin-right: 0 !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
    
    .video-col {
      padding: 0 !important;
      margin: 0 !important;
    }
    
    .col {
      padding: 0 !important;
      margin: 0 !important;
    }
  }
  
  // v-container와 v-row의 기본 패딩 제거 및 정렬
  ::v-deep .event-area .v-container {
    padding-left: 0 !important;
    padding-right: 0 !important;
    max-width: 100% !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
  }
  
  ::v-deep .event-area .video-row {
    margin-left: 0 !important;
    margin-right: 0 !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
  }
  
  ::v-deep .event-area .video-row .video-col {
    padding-left: 0 !important;
    padding-right: 0 !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
  }
  
  // v-col의 기본 패딩 완전 제거
  ::v-deep .event-area .v-row {
    margin-left: 0 !important;
    margin-right: 0 !important;
  }
  
  ::v-deep .event-area .v-col {
    padding-left: 0 !important;
    padding-right: 0 !important;
  }

  .button-row {
    margin-top: 20px;
    
    .cancel-btn {
      background-color: #9e9e9e;
      color: white;
      margin-right: 10px;
      min-width: 80px;
    }
    
    .save-btn {
      background-color: #ff9800;
      color: white;
      min-width: 80px;
    }
  }

  .video-container {
    position: relative;
    width: 1920px; // 1920px로 고정
    min-width: 1920px; // 최소 너비 보장
    max-width: 1920px; // 최대 너비 제한
    height: 480px;
    overflow: hidden; // 스크롤 제거 (이미지가 1920x480으로 강제 리사이즈됨)
    margin: 0 auto; // 중앙 정렬
    background-color: #f0f0f0;
    border-radius: 8px;
    border: 1px solid #e0e0e0;
    display: flex;
    align-items: center; // 세로 중앙 정렬
    justify-content: center; // 가로 중앙 정렬

    .panorama-image {
      height: 480px; // 높이 480px로 고정
      width: auto; // 비율에 맞춰 자동 조정
      max-width: 1920px; // 최대 너비 제한
      object-fit: contain; // 비율 유지하며 컨테이너 안에 완전히 표시
      display: block;
      pointer-events: none;
    }

    .loading-panorama {
      width: 100%;
      height: 100%;
      min-height: 480px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      background-color: #f0f0f0;
      color: #666;
      font-size: 16px;
      
      .loading-text {
        margin-top: 16px;
        font-size: 14px;
        color: #666;
      }
    }

    .video-card {
      width: 100%;
      height: 100%;
      z-index: 1;
      position: relative;
    }

    .selection-overlay {
      position: absolute;
      top: 0;
      left: 0;
      width: 1920px; // 이미지 전체 너비에 맞춤 (고정)
      min-width: 1920px; // 최소 너비 보장
      max-width: 1920px; // 최대 너비 제한
      height: 480px; // 이미지 전체 높이에 맞춤 (고정)
      min-height: 480px; // 최소 높이 보장
      max-height: 480px; // 최대 높이 제한
      cursor: crosshair !important; // 항상 crosshair 커서 유지
      z-index: 1000; // 높은 z-index 추가
      pointer-events: auto; // 마우스 이벤트 활성화
      
      .selection-box {
        position: absolute !important;
        border: 2px solid rgba(255, 140, 0, 0.8) !important; // 주황색 테두리로 변경
        background-color: rgba(255, 140, 0, 0.1) !important; // 주황색 배경으로 변경
        pointer-events: none;
        z-index: 1001 !important; // selection-box보다 높은 z-index
        box-sizing: border-box;
        min-width: 1px;
        min-height: 1px;
      }

      .coordinate-display {
        position: absolute;
        transform: translate(-50%, -50%);
        white-space: nowrap;
        font-family: monospace;
        font-size: 12px;
        background-color: rgba(0, 0, 0, 0.7);
        color: white;
        padding: 4px 8px;
        border-radius: 4px;
        pointer-events: none;
        z-index: 1000; // 가장 높은 z-index
      }
    }
    
    .detection-zone {
      position: absolute;
      pointer-events: none;
    }
  }

  .playground-overlay {
    position: absolute;
    top: -10px;
    left: -10px;
    width: 100%;
    height: 100%;
    pointer-events: all;
    z-index: 10;

    ::v-deep .handle {
      width: 10px !important;
      height: 10px !important;
      background-color: #FFD700 !important;
      border: 2px solid #FFD700 !important;
      box-shadow: none !important;
    }
  }

  .options-panel {
    margin-top: 10px;
    padding: 10px;
    background-color: #1e1e20;
    border-radius: 8px;
  }

  .option-item {
    margin-bottom: 5px;
  }

  .option-label {
    color: #fff;
    font-size: 14px;
  }

  .option-value {
    color: #fff;
    font-size: 14px;
    text-align: right;
  }

  .video-player {
    width: 160px;
    background: #000;
    border-radius: 8px;
    overflow: hidden;
    transition: all 0.3s;

    video {
      width: 100%;
      height: 100%;
      object-fit: contain;
    }
  }

  .refresh-button-container {
    margin-top: 10px;
    display: flex;
    justify-content: center;
  }

  .button-box-dark {
    border-radius: 12px;
    background: #1e1e20;
    padding: 24px 0 16px 0;
    margin: 32px 0 16px 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 24px rgba(0,0,0,0.25);
    min-width: 200px;
    max-height: 200px;
  }

  .v-card-title {
    color: var(--cui-text-default) !important;
    font-size: 1.25rem;
    font-weight: 500;
    padding: 16px 20px;
    border-bottom: 1px solid rgba(var(--cui-bg-nav-border-rgb));
  }

  .v-data-table ::v-deep {
    .v-data-table__wrapper {
      overflow-x: auto;
    }

    tbody tr {
      cursor: pointer;

      &:hover {
        background-color: rgba(0, 0, 0, 0.03);
      }
    }
  }

  .loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 20px;
    text-align: center;
  }

  .loading-text {
    margin-top: 16px;
    color: #666;
    font-size: 16px;
  }
}
</style> 
