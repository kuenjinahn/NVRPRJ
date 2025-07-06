<!-- eslint-disable vue/multi-word-component-names -->
<template lang="pug">
  .event-area
    v-container(fluid)
      v-row
        v-col(cols="6")
          v-select(
            v-if="cameraList.length"
            :items="cameraList"
            item-text="name"
            item-value="name"
            v-model="selectedCameraName"
            label="카메라 선택"
            dense
            outlined
            class="mb-4"
            @click="customizing = false"
          )
          .video-container(
            @mouseleave="handleMouseLeave"
          )
            VideoCard(
              v-if="selectedCamera"
              :key="videoKey"
              :ref="selectedCamera.name"
              :camera="selectedCamera"
              title
              titlePosition="inner-top"
              status
              :stream="selectedCamera.live"
              :refreshSnapshot="!selectedCamera.live"
              class="video-card"
            )
            .selection-overlay(
              v-if="selectedCamera && customizing"
              :style="{ width: '640px', height: '480px' }"
              @mousedown="startDrag"
              @mousemove="onDrag"
              @mouseup="endDrag"
            )
              .selection-box(
                v-if="isDragging"
                :style="selectionBoxStyle"
              )
              .coordinate-display(
                v-if="mousePosition"
                :style="coordinateDisplayStyle"
              )
                | X: {{ mousePosition.x }}px Y: {{ mousePosition.y }}px
            .detection-zone(
              v-if="region"
              :style="getZoneStyle(region)"
            )
          // .options-panel
          //   v-row
          //     v-col(cols="6")
          //       .option-item
          //         v-row(align="center" no-gutters)
          //           v-col(cols="5")
          //             span.option-label Force Close Timer
          //           v-col(cols="5")
          //             v-slider(
          //               v-model="options.forceCloseTimer.value"
          //               :min="1"
          //               :max="100"
          //               @input="updateOptions"
          //               color="primary"
          //               hide-details
          //               class="mt-0"
          //             )
          //           v-col(cols="2")
          //             span.option-value {{ options.forceCloseTimer.value }}
          //     v-col(cols="6")
          //       .option-item
          //         v-row(align="center" no-gutters)
          //           v-col(cols="5")
          //             span.option-label Dwell Timer
          //           v-col(cols="5")
          //             v-slider(
          //               v-model="options.dwellTimer.value"
          //               :min="1"
          //               :max="100"
          //               @input="updateOptions"
          //               color="primary"
          //               hide-details
          //               class="mt-0"
          //             )
          //           v-col(cols="2")
          //             span.option-value {{ options.dwellTimer.value }}
          //   v-row
          //     v-col(cols="6")
          //       .option-item
          //         v-row(align="center" no-gutters)
          //           v-col(cols="5")
          //             span.option-label Sensitivity
          //           v-col(cols="5")
          //             v-slider(
          //               v-model="options.sensitivity.value"
          //               :min="1"
          //               :max="100"
          //               @input="updateOptions"
          //               color="primary"
          //               hide-details
          //               class="mt-0"
          //             )
          //           v-col(cols="2")
          //             span.option-value {{ options.sensitivity.value }}
          //     v-col(cols="6")
          //       .option-item
          //         v-row(align="center" no-gutters)
          //           v-col(cols="5")
          //             span.option-label Difference
          //           v-col(cols="5")
          //             v-slider(
          //               v-model="options.difference.value"
          //               :min="1"
          //               :max="100"
          //               @input="updateOptions"
          //               color="primary"
          //               hide-details
          //               class="mt-0"
          //             )
          //           v-col(cols="2")
          //             span.option-value {{ options.difference.value }}
          v-row.mt-4
            v-col(cols="6")
              v-text-field(
                v-model="description"
                label="Description"
                outlined
                dense
                hide-details
                dark
                background-color="#2a2a2a"
                color="primary"
              )
            v-col(cols="3")
              v-select(
                v-model="detectionZoneType"
                :items="detectionZoneTypes"
                item-text="text"
                :return-object="true"
                label="영역 번호"
                outlined
                dense
                hide-details
                dark
                background-color="#2a2a2a"
                color="primary"
              )
          .tw-flex.tw-justify-center.tw-mt-4
          .button-box.button-box-dark.tw-flex.tw-flex-row.tw-gap-4
            v-btn(@click="customizing ? finishCustom() : startCustom()")
              v-icon {{ customizing ? icons.mdiCheckboxMarkedCircle : icons.mdiMapMarkerRadius }}
            v-btn(@click="undo")
              v-icon {{ icons.mdiUndo }}
            v-btn(@click="clear")
              v-icon {{ icons.mdiRefresh }}
            v-btn(@click="add")
              v-icon {{ editId ? icons.mdiPencil : icons.mdiPlus }}
              span {{ editId ? 'Modify' : 'Add' }}
        v-col(cols="6")
          v-data-table(
            :headers="tableHeaders"
            :items="eventDetectionZoneList"
            item-key="id"
            class="elevation-1"
          )
            template(#[`item.no`]="{ index }")
              span {{ index + 1 }}
            template(#[`item.cameraName`]="{ item }")
              span {{ getCameraName(item.cameraId) }}
            template(#[`item.description`]="{ item }")
              span {{ item.description }}
            template(#[`item.type`]="{ item }")
              span {{ getTypeText(item.type) }}
            template(v-slot:item.actions="{ item }")
              .tw-flex.tw-items-center.tw-gap-2
                v-btn.edit-btn(
                  color="white"
                  @click.stop="onRowClick(item)"
                  outlined
                )
                  v-icon(left size="20" ) {{ icons['mdiPencil'] }}
                  span 수정
                v-btn.delete-btn(
                  color="error"
                  @click.stop="confirmDelete(item)"
                  outlined
                )
                  v-icon(left size="20") {{ icons['mdiDelete'] }}
                  span 삭제              

          v-dialog(v-model="deleteDialog" max-width="400px")
            v-card
              v-card-title.error--text 삭제 확인
              v-card-text.tw-text-white 정말 삭제하시겠습니까?
              v-card-actions
                v-btn(@click="deleteDialog = false") 취소
                v-btn(color="error" @click="deleteRow") 삭제
</template>

<script>
import { getCameras, getCameraSettings } from '@/api/cameras.api';
import VideoCard from '@/components/camera-card.vue';
import { mdiRefresh, mdiMapMarkerRadius, mdiCheckboxMarkedCircle, mdiUndo, mdiPlus, mdiPencil, mdiDelete } from '@mdi/js';
import Playground from '@/components/playground.vue';
import { addEventDetectionZone, getEventDetectionZone, updateEventDetectionZone, deleteEventDetectionZone, updateInPageZone } from '@/api/eventDetectionZone.api';

export default {
  name: 'EventDetectionZone',

  components: {
    VideoCard,
    Playground
  },

  data() {
    return {
      cameraList: [],
      selectedCameraName: '',
      selectedCamera: null,
      videoKey: '',
      refreshing: false,
      description: '',
      videoContainerWidth: 640,
      videoContainerHeight: 480,
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
      customizing: false,
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
    };
  },
  computed: {
    selectionBoxStyle() {
      const left = Math.min(this.dragStart.x, this.dragEnd.x);
      const top = Math.min(this.dragStart.y, this.dragEnd.y);
      const width = Math.abs(this.dragEnd.x - this.dragStart.x);
      const height = Math.abs(this.dragEnd.y - this.dragStart.y);
      
      return {
        left: left + 'px',
        top: top + 'px',
        width: width + 'px',
        height: height + 'px'
      };
    },
    coordinateDisplayStyle() {
      if (!this.mousePosition) return {};
      return {
        position: 'absolute',
        left: (this.mousePosition.x + 10) + 'px',
        top: (this.mousePosition.y + 10) + 'px',
        backgroundColor: 'rgba(0, 0, 0, 0.7)',
        color: 'white',
        padding: '4px 8px',
        borderRadius: '4px',
        fontSize: '12px',
        pointerEvents: 'none',
        zIndex: 1000
      };
    }
  },
  watch: {
    selectedCameraName(newName, oldName) {
      if (newName !== oldName) {
        if (!this.editId) {  // 수정 모드가 아닐 때만 초기화
          this.customizing = false;
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
  methods: {
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
      this.videoContainerWidth = 640;
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
      this.customizing = false;
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
      
      // console.log('this.detectionZoneType :',this.detectionZoneType?.value,', this.eventDetectionZoneList :', JSON.stringify(this.eventDetectionZoneList));
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
      
      // Convert stored coordinates to pixels if they're percentages
      const storedRegion = item.regions[0];
      if (storedRegion) {
        this.region = {
          left: Math.round(storedRegion.left),
          top: Math.round(storedRegion.top),
          right: Math.round(storedRegion.right),
          bottom: Math.round(storedRegion.bottom),
          coords: storedRegion.coords.map(coord => [
            Math.round(coord[0]) + (coord[0] === storedRegion.left ? 1 : 0),  // Add correction for left
            Math.round(coord[1]) + (coord[1] === storedRegion.bottom ? 1 : 0)  // Add correction for bottom
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
      
      // Convert stored coordinates to pixels if they're percentages
      const storedRegion = item.regions[0];
      if (storedRegion) {
        this.region = {
          left: Math.round(storedRegion.left),
          top: Math.round(storedRegion.top),
          right: Math.round(storedRegion.right),
          bottom: Math.round(storedRegion.bottom),
          coords: storedRegion.coords.map(coord => [
            Math.round(coord[0]) + (coord[0] === storedRegion.left ? 1 : 0),  // Add correction for left
            Math.round(coord[1]) + (coord[1] === storedRegion.bottom ? 1 : 0)  // Add correction for bottom
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
        this.isDragging = false;
        this.dragStart = { x: 0, y: 0 };
        this.dragEnd = { x: 0, y: 0 };
        this.mousePosition = null;
      }
    },

    startDrag(event) {
      if (!this.customizing) return;
      
      const rect = event.target.getBoundingClientRect();
      this.isDragging = true;
      this.dragStart = {
        x: event.clientX - rect.left,
        y: event.clientY - rect.top
      };
      this.dragEnd = { ...this.dragStart };
      this.updateMousePosition(event);
      
      // Clear existing region when starting new drag
      this.region = null;
    },
    
    onDrag(event) {
      if (!this.isDragging) return;
      
      const rect = event.target.getBoundingClientRect();
      this.dragEnd = {
        x: event.clientX - rect.left,
        y: event.clientY - rect.top
      };

      // Update mouse position for coordinate display
      this.updateMousePosition(event);
    },
    
    updateMousePosition(event) {
      const rect = event.target.getBoundingClientRect();
      const x = Math.round(event.clientX - rect.left);
      const y = Math.round(event.clientY - rect.top);
      this.mousePosition = { x, y };
    },
    
    endDrag() {
      if (!this.isDragging) return;
      
      this.isDragging = false;
      
      // Only create region if we have valid coordinates
      if (this.dragStart.x !== 0 && this.dragStart.y !== 0 && 
          this.dragEnd.x !== 0 && this.dragEnd.y !== 0) {
        // Get pixel coordinates with corrections
        const left = Math.round(Math.min(this.dragStart.x, this.dragEnd.x)) + 1;  // Add 1px correction
        const top = Math.round(Math.min(this.dragStart.y, this.dragEnd.y));
        const right = Math.round(Math.max(this.dragStart.x, this.dragEnd.x));
        const bottom = Math.round(Math.max(this.dragStart.y, this.dragEnd.y)) + 1;  // Add 1px correction
        
        // Create a single region with pixel coordinates
        this.region = {
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
        };
        
        console.log('Region coordinates:', {
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
      // Convert pixel coordinates to percentages for display
      const leftPercent = Math.round((zone.left / this.videoContainerWidth) * 100);
      const topPercent = Math.round((zone.top / this.videoContainerHeight) * 100);
      const rightPercent = Math.round((zone.right / this.videoContainerWidth) * 100);
      const bottomPercent = Math.round((zone.bottom / this.videoContainerHeight) * 100);
      
      return {
        position: 'absolute',
        left: leftPercent + '%',
        top: topPercent + '%',
        width: (rightPercent - leftPercent) + '%',
        height: (bottomPercent - topPercent) + '%',
        border: '2px solid rgba(255, 255, 255, 0.5)',
        backgroundColor: 'rgba(255, 255, 255, 0.1)',
        pointerEvents: 'none'
      };
    }
  },
  async mounted() {
    try {
      // 화면 진입시 updateInPageZone 호출 (1)
      await updateInPageZone(1);
      
      const response = await getCameras();
      for (const camera of response.data.result) {
        const settings = await getCameraSettings(camera.name);
        camera.settings = settings.data.settings;
        camera.favourite = camera.settings.camview.favourite;
        camera.live = camera.settings.camview.live || false;
        camera.refreshTimer = camera.settings.camview.refreshTimer || 60;
        camera.url = camera.videoConfig.source.replace(/\u00A0/g, ' ').split('-i ')[1];
        if (!camera.url.startsWith('/')) {
          const protocol = camera.url.split('://')[0];
          const url = new URL(camera.url.replace(protocol, 'http'));
          camera.url = `${protocol}://${url.hostname}:${url.port || 80}${url.pathname}`;
        }
      }
      this.cameraList = response.data.result;
      if (this.cameraList.length > 0) {
        this.selectedCameraName = this.cameraList[0].name;
        this.updateSelectedCamera(this.selectedCameraName);
      }
      // detectionZoneType 초기값을 object로 설정
      if (this.detectionZoneTypes.length > 0) {
        this.detectionZoneType = this.detectionZoneTypes[0];
      }
    } catch (err) {
      this.$toast.error(err.message);
    }
    // 전역 cleanup 함수 등록
    window.cleanupEventDetectionZone = () => {
      this.cleanupResources();
    };
    await this.loadEventDetectionZone();
    window.addEventListener('resize', this.updateVideoContainerSize);
  },
  beforeDestroy() {
    // 화면 나갈때 updateInPageZone 호출 (0)
    updateInPageZone(0);
    window.removeEventListener('resize', this.updateVideoContainerSize);
  }
};
</script>

<style lang="scss">
.event-area {
  padding: 20px;

  .video-container {
    position: relative;
    width: 640px;
    height: 480px;
    overflow: hidden;
    margin: 0 auto 20px auto;
    background-color: #000;

  .video-card {
      width: 640px;
      height: 480px;
    }

    .selection-overlay {
      position: absolute;
      top: 0;
      left: 0;
      width: 640px;
      height: 480px;
      cursor: crosshair;
      
      .selection-box {
        position: absolute;
        border: 2px solid rgba(255, 255, 255, 0.8);
        background-color: rgba(255, 255, 255, 0.1);
        pointer-events: none;
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
        z-index: 1000;
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
}
</style> 
