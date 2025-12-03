<template>
  <div class="admin-result">
    <!-- Header -->
    <v-app-bar app color="white" elevation="1" height="64">
      <!-- Left side: Logo and Title -->
      <div class="logo-container" v-show="!sidebarDrawer">
        <v-img
          src="@/assets/img/logo.png"
          alt="Welcome to SDMS "
          width="160"
          max-height="80"
          class="mr-3"
        />
      </div>
      
      <v-spacer></v-spacer>
      
      <!-- Right side: Navigation, User, Logout -->
      <div class="d-flex align-center">
        <!-- Main Screen Navigation -->
        <div class="system-btn">
          <v-btn text class="system-btn-text" @click="goHome">
            <v-icon left class="system-btn-icon">{{ icons.arrowRight }}</v-icon>
            <span class="system-btn-label">메인화면 이동</span>
          </v-btn>
        </div>
        
        <v-divider vertical class="mx-3 system-divider"></v-divider>
        
        <!-- User Profile -->
        <div class="system-btn">
          <v-btn icon class="system-btn-icon-only">
            <v-icon class="system-btn-icon">{{ icons.account }}</v-icon>
          </v-btn>
          <span class="system-btn-label ml-2">{{ userName }}</span>
        </div>
        
        <v-divider vertical class="mx-3 system-divider"></v-divider>
        
        <!-- Logout -->
        <div class="system-btn">
          <v-btn icon class="system-btn-icon-only" @click="logout">
            <v-icon class="system-btn-icon">{{ icons.logout }}</v-icon>
          </v-btn>
        </div>
      </div>
    </v-app-bar>

    <!-- Main Content -->
    <v-main class="admin-main">
      <!-- Button Section -->
      <div class="button-section gradient-header">
        <div class="button-container">
          <div 
            class="header-section" 
            :class="{ 'active': activeTab === 'management-standard' }"
            @click="activeTab = 'management-standard'"
          >
            <v-btn text class="header-btn">
              <v-icon left class="header-icon">{{ icons.clipboardText }}</v-icon>
              <span class="header-text">관리기준관리</span>
            </v-btn>
          </div>
          
          <div 
            class="header-section" 
            :class="{ 'active': activeTab === 'analysis-area' }"
            @click="activeTab = 'analysis-area'"
          >
            <v-btn text class="header-btn">
              <v-icon left class="header-icon">{{ icons.cctv }}</v-icon>
              <span class="header-text">분석영역관리</span>
            </v-btn>
          </div>
          
          <div 
            class="header-section" 
            :class="{ 'active': activeTab === 'alarm-history' }"
            @click="activeTab = 'alarm-history'"
          >
            <v-btn text class="header-btn">
              <v-icon left class="header-icon">{{ icons.alertCircle }}</v-icon>
              <span class="header-text">경보이력조회</span>
            </v-btn>
          </div>
          
          <div 
            class="header-section" 
            :class="{ 'active': activeTab === 'alarm-notification' }"
            @click="activeTab = 'alarm-notification'"
          >
            <v-btn text class="header-btn">
              <v-icon left class="header-icon">{{ icons.bell }}</v-icon>
              <span class="header-text">경보알림관리</span>
            </v-btn>
          </div>
        </div>
      </div>

      <!-- Blue Background Bar -->
      <div class="blue-back-bar">
      </div>

      <!-- Content Area -->
      <div class="content-area">
        <v-window v-model="activeTab" class="content-window">
          <!-- 관리기준 관리 -->
            <v-window-item value="management-standard">
              <div class="content-container">
                <div class="content-header">
                  <h2 class="content-title mb-6">관리기준 관리</h2>
                </div>
                <div class="content-bottom-line"></div>
                <div class="content-body">
                  <!-- 시나리오 선택 및 저장 버튼 -->
                  <div class="scenario-control-section">
                    <div class="scenario-selection">
                      <label class="scenario-label">누수판단 시나리오 선택</label>
                      <div class="custom-tab-group">
                        <div 
                          class="custom-tab"
                          :class="{ 'active': selectedScenario === 'scenario1' }"
                          @click="selectedScenario = 'scenario1'"
                        >
                          시나리오 1
                        </div>
                        <div 
                          class="custom-tab"
                          :class="{ 'active': selectedScenario === 'scenario2' }"
                          @click="selectedScenario = 'scenario2'"
                        >
                          시나리오 2
                        </div>
                      </div>
                      <v-alert
                        v-if="selectedScenario"
                        type="info"
                        outlined
                        class="scenario-description"
                      >
                        {{ scenarioDescriptions[selectedScenario] }}
                      </v-alert>
                    </div>
                    <div class="save-button-section">
                      <v-btn
                        color="secondary"
                        @click="saveSettings"
                        :loading="isLoading"
                        :disabled="isLoading"
                        class="save-btn"
                      >
                        저장
                      </v-btn>
                    </div>
                  </div>

                  <v-data-table
                  :headers="tableHeaders"
                  :items="tableData"
                  :items-per-page="10"
                  class="elevation-1 mb-6"
                  hide-default-footer
                >
                  <template v-slot:item="{ item }">
                    <tr>
                      <td>{{ item.no }}</td>
                      <td>{{ item.scenarioType }}</td>
                      <td>
                        <div class="input-with-unit">
                          <v-text-field
                            v-model="item.stage1"
                            dense
                            outlined
                            hide-details
                            type="number"
                            class="standard-input"
                          ></v-text-field>
                          <span class="unit-symbol">°C</span>
                        </div>
                      </td>
                      <td>
                        <div class="input-with-unit">
                          <v-text-field
                            v-model="item.stage2"
                            dense
                            outlined
                            hide-details
                            type="number"
                            class="standard-input"
                          ></v-text-field>
                          <span class="unit-symbol">°C</span>
                        </div>
                      </td>
                      <td>
                        <div class="input-with-unit">
                          <v-text-field
                            v-model="item.stage3"
                            dense
                            outlined
                            hide-details
                            type="number"
                            class="standard-input"
                          ></v-text-field>
                          <span class="unit-symbol">°C</span>
                        </div>
                      </td>
                      <td>
                        <div class="input-with-unit">
                          <v-text-field
                            v-model="item.stage4"
                            dense
                            outlined
                            hide-details
                            type="number"
                            class="standard-input"
                          ></v-text-field>
                          <span class="unit-symbol">°C</span>
                        </div>
                      </td>

                    </tr>
                  </template>
                </v-data-table>
              </div>
            
            </div>
          </v-window-item>
          <!-- 분석영역관리 -->
          <v-window-item value="analysis-area">
            <div class="content-container">
              <div class="content-header">
                <h2 class="content-title mb-6">분석영역관리</h2>
              </div>
              <div class="content-bottom-line"></div>
              <div class="content-body">
                <!-- 상단 추가 버튼 -->
                <div class="add-button-section">
                  <v-btn
                    color="secondary"
                    @click="addRoiArea"
                    class="add-btn"
                  >
                    + 영역 추가
                  </v-btn>
                </div>

                <!-- ROI 테이블 -->
                <v-data-table
                  :headers="roiTableHeaders"
                  :items="roiTableData"
                  :items-per-page="10"
                  class="elevation-1 mb-6"
                  hide-default-footer
                  @click:row="onRoiRowClick"
                >
                  <template v-slot:item="{ item }">
                    <tr class="roi-table-row">
                      <td>{{ item.no }}</td>
                      <td>{{ item.areaNumber }}</td>
                      <td>{{ item.startX }}</td>
                      <td>{{ item.startY }}</td>
                      <td>{{ item.endX }}</td>
                      <td>{{ item.endY }}</td>
                      <td>
                        <v-btn
                          color="primary"
                          small
                          outlined
                          @click.stop="editRoiArea(item)"
                          class="edit-btn"
                          :loading="item.loading"
                        >
                          수정
                        </v-btn>
                        <v-btn
                          color="warning"
                          small
                          outlined
                          @click.stop="confirmDeleteRoiArea(item)"
                          class="delete-btn"
                        >
                          삭제
                        </v-btn>
                      </td>
                    </tr>
                  </template>
                </v-data-table>
              </div>
            </div>
          </v-window-item>

          <!-- 경보이력조회 -->
          <v-window-item value="alarm-history">
            <div class="content-container">
              <div class="content-header">
                <h2 class="content-title mb-6">경보이력 관리</h2>
              </div>
              <div class="content-bottom-line"></div>
              <div class="content-body">
                <!-- 필터 섹션 (UI 숨김) -->
                <div class="filter-section mb-4" style="display: none;">
                  <v-row>
                    <v-col cols="12" md="4">
                      <v-menu
                        ref="dateMenu"
                        v-model="alarmDateMenu"
                        :close-on-content-click="false"
                        transition="scale-transition"
                        offset-y
                        min-width="290px"
                      >
                        <template v-slot:activator="{ on, attrs }">
                          <v-text-field
                            v-model="alarmDateFilter"
                            label="경보발령 일자"
                            prepend-inner-icon="mdi-calendar"
                            readonly
                            v-bind="attrs"
                            v-on="on"
                            clearable
                            dense
                            outlined
                            hide-details
                            class="standard-input"
                            @click:clear="alarmDateFilter = null"
                          ></v-text-field>
                        </template>
                        <v-date-picker
                          v-model="alarmDateFilter"
                          @input="alarmDateMenu = false; applyAlarmFilters()"
                          no-title
                          scrollable
                        ></v-date-picker>
                      </v-menu>
                    </v-col>
                    <v-col cols="12" md="4">
                      <v-select
                        v-model="alarmRoiFilter"
                        :items="alarmRoiOptions"
                        label="ROI"
                        prepend-inner-icon="mdi-map-marker"
                        clearable
                        dense
                        outlined
                        hide-details
                        class="standard-input"
                        @change="applyAlarmFilters()"
                      ></v-select>
                    </v-col>
                    <v-col cols="12" md="4" class="d-flex align-center">
                      <v-btn
                        color="secondary"
                        @click="resetAlarmFilters()"
                        class="ml-auto"
                      >
                        필터 초기화
                      </v-btn>
                    </v-col>
                  </v-row>
                </div>
                <!-- 경보이력 테이블 -->
                <v-data-table
                  :headers="alarmTableHeaders"
                  :items="alarmTableData"
                  :items-per-page="10"
                  :page.sync="alarmPage"
                  :server-items-length="alarmTotalItems"
                  :loading="alarmLoading"
                  loading-text="경보이력을 불러오는 중..."
                  class="elevation-1 mb-6"
                  hide-default-footer
                >
                  <template v-slot:item="{ item }">
                    <tr>
                      <td>{{ item.no }}</td>
                      <td>{{ item.locationInfo }}</td>
                      <td>
                        <v-chip
                          :color="getAlarmLevelColor(item.alarmLevel)"
                          text-color="white"
                          small
                          class="alarm-level-chip"
                        >
                          <v-icon left small>{{ getAlarmLevelIcon(item.alarmLevel) }}</v-icon>
                          {{ getAlarmLevelText(item.alarmLevel) }}
                        </v-chip>
                      </td>
                      <td>{{ item.roi }}</td>
                      <td>{{ item.maxTemp }}°C</td>
                      <td>{{ item.minTemp }}°C</td>
                      <td>{{ item.avgTemp }}°C</td>
                      <td>{{ formatDateTime(item.alarmTime) }}</td>
                    </tr>
                  </template>
                  <template v-slot:no-data>
                    <div class="text-center pa-4">
                      <v-icon large color="grey lighten-1">mdi-alert-circle-outline</v-icon>
                      <div class="mt-2 grey--text">경보이력이 없습니다.</div>
                    </div>
                  </template>
                </v-data-table>

                <!-- 페이지네이션 -->
                <div class="pagination-section">
                  <div class="pagination-info">
                    <span class="pagination-text">
                      총 {{ alarmTotalItems }}개 중 {{ (alarmPage - 1) * 10 + 1 }}-{{ Math.min(alarmPage * 10, alarmTotalItems) }}개 표시 ({{ alarmPage }}/{{ alarmTotalPages }} 페이지)
                    </span>
                  </div>
                  
                  <div class="pagination-controls">
                    <!-- 첫 페이지 버튼 -->
                    <v-btn
                      icon
                      small
                      :disabled="alarmPage === 1"
                      @click="goToPage(1)"
                      class="pagination-btn"
                    >
                      <v-icon>{{ icons.chevronDoubleLeft }}</v-icon>
                    </v-btn>
                    
                    <!-- 이전 페이지 버튼 -->
                    <v-btn
                      icon
                      small
                      :disabled="alarmPage === 1"
                      @click="goToPage(alarmPage - 1)"
                      class="pagination-btn"
                    >
                      <v-icon>{{ icons.chevronLeft }}</v-icon>
                    </v-btn>
                    
                    <!-- 페이지 번호 버튼들 -->
                    <div class="page-numbers">
                      <template v-for="page in getVisiblePages()">
                        <v-btn
                          v-if="page !== '...'"
                          :key="page"
                          small
                          :color="page === alarmPage ? 'secondary' : 'default'"
                          :class="page === alarmPage ? 'active-page' : 'page-btn'"
                          @click="goToPage(page)"
                        >
                          {{ page }}
                        </v-btn>
                        <span v-else :key="`ellipsis-${page}`" class="ellipsis">...</span>
                      </template>
                    </div>
                    
                    <!-- 다음 페이지 버튼 -->
                    <v-btn
                      icon
                      small
                      :disabled="alarmPage === alarmTotalPages"
                      @click="goToPage(alarmPage + 1)"
                      class="pagination-btn"
                    >
                      <v-icon>{{ icons.chevronRight }}</v-icon>
                    </v-btn>
                    
                    <!-- 마지막 페이지 버튼 -->
                    <v-btn
                      icon
                      small
                      :disabled="alarmPage === alarmTotalPages"
                      @click="goToPage(alarmTotalPages)"
                      class="pagination-btn"
                    >
                      <v-icon>{{ icons.chevronDoubleRight }}</v-icon>
                    </v-btn>
                  </div>
                  
                  
                </div>
              </div>
            </div>
          </v-window-item>

          <!-- 경보알림관리 -->
          <v-window-item value="alarm-notification">
            <div class="content-container">
              <div class="content-header">
                <h2 class="content-title mb-6">경보 알림 관리</h2>
                <v-btn
                  color="secondary"
                  @click="saveNotificationSettings"
                  :loading="savingNotification"
                  class="save-button-top"
                >
                  저장
                </v-btn>
              </div>
              <div class="content-bottom-line"></div>
              <div class="content-body">
                <!-- 알림 종류 설정 테이블 -->
                <div class="notification-settings-section">
                  <h3 class="section-title">알림 종류 설정</h3>
                  <v-simple-table class="notification-table">
                    <thead>
                      <tr>
                        <th class="notification-type-header" style="color: #000000 !important; font-weight: 600 !important; text-align: center !important;">알림 종류</th>
                        <th class="notification-toggle-header" style="color: #000000 !important; font-weight: 600 !important; text-align: center !important;">경보 알림 활성/비활성</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td style="text-align: center !important; font-weight: 500 !important;">팝업 알림 설정</td>
                        <td style="text-align: center !important;">
                          <v-switch
                            v-model="notificationSettings.popupEnabled"
                            color="primary"
                            hide-details
                            class="notification-switch"
                          ></v-switch>
                        </td>
                      </tr>
                      <tr>
                        <td style="text-align: center !important; font-weight: 500 !important;">문자 알림 설정</td>
                        <td style="text-align: center !important;">
                          <v-switch
                            v-model="notificationSettings.smsEnabled"
                            color="primary"
                            hide-details
                            class="notification-switch"
                          ></v-switch>
                        </td>
                      </tr>
                    </tbody>
                  </v-simple-table>
                  
                  <!-- 담당자 문자 전송 번호 입력 -->
                  <div class="phone-input-section">
                    <div class="phone-input-header">
                      <label class="phone-label">담당자 문자 전송 번호 입력</label>
                      <div style="flex: 1;"></div>
                      <v-btn 
                        class="message-input-btn-save"
                        @click="openMessageDialog"
                      >
                        문자 직접 입력하기
                      </v-btn>
                    </div>
                    <v-text-field
                      v-model="notificationSettings.phoneNumber"
                      placeholder="전화번호를 입력하세요 (예: 010-1234-5678)"
                      outlined
                      dense
                      hide-details
                      class="phone-input standard-input"
                      :disabled="useSameNumber"
                    ></v-text-field>
                    <p v-if="useSameNumber" class="instruction-text">
                      같은 번호로 보내기 토글 버튼이 on이면 해당 번호 입력 칸 비활성화
                    </p>
                  </div>
                </div>

                <!-- 경보 알림 기준 설정 테이블 -->
                <div class="threshold-settings-section">
                  <h3 class="section-title">경보 알림 기준 설정</h3>
                  <v-simple-table class="threshold-table">
                    <thead>
                      <tr>
                        <th style="color: #000000 !important; font-weight: 600 !important; text-align: center !important;">No</th>
                        <th style="color: #000000 !important; font-weight: 600 !important; text-align: center !important;">경보 알림 기준 단계</th>
                        <th style="color: #000000 !important; font-weight: 600 !important; text-align: center !important;">경보 알림 기준 횟수 설정</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(threshold, index) in notificationSettings.thresholds" :key="index">
                        <td style="text-align: center !important; font-weight: 500 !important;">{{ index + 1 }}</td>
                        <td style="text-align: center !important; font-weight: 500 !important;">{{ index + 1 }}단계 경보 발령 알림 횟수</td>
                        <td style="text-align: center !important;">
                          <div class="threshold-input-container">
                            <v-text-field
                              v-model="threshold.count"
                              type="number"
                              min="0"
                              outlined
                              dense
                              hide-details
                              class="threshold-input standard-input"
                            ></v-text-field>
                            <span class="threshold-unit">회 이상</span>
                          </div>
                        </td>
                      </tr>
                    </tbody>
                  </v-simple-table>
                </div>
              </div>
            </div>
          </v-window-item>
        </v-window>
      </div>

      <!-- Footer -->
      <v-footer app class="text-center footer-copyright">
        <v-col class="text-center">
          ©ASINCNT. All rights reserved.
        </v-col>
      </v-footer>
    </v-main>

    <!-- ROI 추가/수정 팝업 다이얼로그 -->
    <RoiWindow
      v-model="showRoiDialog"
      :edit-data="selectedRoiData"
      :is-edit-mode="isEditMode"
      :roi-table-data="roiTableData"
      :check-duplicate="checkDuplicateRoiNumber"
      max-width="2000px"
      @saved="onRoiSaved"
    />

    <!-- ROI 삭제 확인 다이얼로그 -->
    <div v-if="showDeleteDialog" class="simple-delete-overlay" @click="showDeleteDialog = false">
      <div class="simple-delete-dialog" @click.stop>
        <h3>영역 삭제</h3>
        <p>영역 번호: {{ selectedDeleteItem && selectedDeleteItem.areaNumber }}</p>
        <p>좌표: ({{ selectedDeleteItem && selectedDeleteItem.startX }}, {{ selectedDeleteItem && selectedDeleteItem.startY }}) ~ ({{ selectedDeleteItem && selectedDeleteItem.endX }}, {{ selectedDeleteItem && selectedDeleteItem.endY }})</p>
        <div class="buttons">
          <button @click="showDeleteDialog = false" :disabled="isDeleting">취소</button>
          <button @click="deleteRoiArea" :disabled="isDeleting">{{ isDeleting ? '삭제 중...' : '삭제' }}</button>
        </div>
      </div>
    </div>

    <!-- 문자 직접 입력 다이얼로그 -->
    <v-dialog v-model="showMessageDialog" max-width="600px" width="600px" persistent class="message-dialog">
      <v-card class="message-dialog-card">
        <v-card-title class="message-dialog-title">
          <span>문자 직접 입력</span>
          <v-spacer></v-spacer>
          <v-btn icon @click="closeMessageDialog" class="close-btn">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>
        <v-card-text class="message-dialog-content">
          <v-container fluid>
            <!-- 담당자 번호와 같은 번호로 보내기 -->
            <v-row class="input-row">
              <v-col cols="12">
                <div class="custom-input-group-switch">
                  <label class="custom-label">담당자 번호와 같은 번호로 보내기</label>
                  <v-switch
                    v-model="useSameNumber"
                    color="red"
                    hide-details
                    class="custom-switch"
                  ></v-switch>
                </div>
              </v-col>
            </v-row>

            <!-- 담당자 문자 전송 번호 입력 -->
            <v-row class="input-row" v-if="!useSameNumber">
              <v-col cols="12">
                <div class="custom-input-group">
                  <label class="custom-label">담당자 문자 전송 번호 입력</label>
                  <input
                    v-model="messagePhoneNumber"
                    type="text"
                    class="custom-input"
                    placeholder="전화번호를 입력하세요 (예: 010-1234-5678)"
                  />
                </div>
              </v-col>
            </v-row>

            <!-- 안내 문구 -->
            <v-row class="input-row" v-if="useSameNumber">
              <v-col cols="12">
                <p class="instruction-text-red">
                  같은 번호로 보내기 토글 버튼이 on이면 해당 번호 입력 칸 비활성화
                </p>
              </v-col>
            </v-row>

            <!-- 문자 내용 입력 -->
            <v-row class="input-row">
              <v-col cols="12">
                <div class="custom-input-group">
                  <label class="custom-label">문자 내용 입력</label>
                  <textarea
                    v-model="messageContent"
                    class="custom-textarea"
                    placeholder="메시지를 입력하세요"
                    rows="8"
                  ></textarea>
                </div>
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>
        <v-card-actions class="message-dialog-actions">
          <v-btn text @click="closeMessageDialog" class="cancel-btn">취소</v-btn>
          <v-btn text @click="sendMessage" class="save-btn">전송</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
import { mdiArrowRight, mdiAccount, mdiLogout, mdiClipboardText, mdiChartNetwork, mdiAlertCircle, mdiCctv, mdiChevronDoubleLeft, mdiChevronDoubleRight, mdiChevronLeft, mdiChevronRight, mdiBell } from '@mdi/js';
import { getEventDetectionZone, deleteEventDetectionZone, updateInPageZone } from '@/api/eventDetectionZone.api';
import { getAlertSettings,getAlerts,saveAlertSettings } from '@/api/alerts.api';
import { getEventSetting } from '@/api/eventSetting.api';
import { getUser } from '@/api/users.api';
import { bus } from '@/main';
import RoiWindow from '@/components/roiWindow.vue';
import socket from '@/mixins/socket';

export default {
  name: 'AdminResult',
  
  components: {
    RoiWindow
  },
  
  mixins: [socket],
  
  data() {
    return {
      // 아이콘들
      icons: {
        arrowRight: mdiArrowRight,
        account: mdiAccount,
        logout: mdiLogout,
        clipboardText: mdiClipboardText,
        chartNetwork: mdiChartNetwork,
        alertCircle: mdiAlertCircle,
        cctv: mdiCctv,
        chevronDoubleLeft: mdiChevronDoubleLeft,
        chevronDoubleRight: mdiChevronDoubleRight,
        chevronLeft: mdiChevronLeft,
        chevronRight: mdiChevronRight,
        bell: mdiBell
      },
      activeTab: 'management-standard',
      tableHeaders: [
        { text: 'No', value: 'no', width: '80px' },
        { text: '시나리오 종류', value: 'scenarioType', width: '300px' },
        { text: '1단계-주의', value: 'stage1', width: '150px' },
        { text: '2단계-경고', value: 'stage2', width: '150px' },
        { text: '3단계-위험', value: 'stage3', width: '150px' },
        { text: '4단계-심각', value: 'stage4', width: '150px' },
      ],
      tableData: [
        {
          no: 1,
          scenarioType: '시나리오1: 온도차이(°C) 기준 + 온도변화량(%) 기준',
          stage1: 2,
          stage2: 5,
          stage3: 8,
          stage4: 10
        },
        {
          no: 2,
          scenarioType: '시나리오2: Pixel별 1시간 평균온도 C2M distance 기준',
          stage1: 6,
          stage2: 15,
          stage3: 20,
          stage4: 25
        }
      ],
      newStandard: {
        scenarioType: '',
        stage1: '',
        stage2: '',
        stage3: '',
        stage4: ''
      },
      selectedScenario: 'scenario1',
      isLoading: false,
      scenarioDescriptions: {
        scenario1: '온도차이(°C) 기준 + 온도변화량(%) 기준 통합 시나리오',
        scenario2: 'Pixel별 1시간 평균온도 C2M distance 5℃ 이상(95% 신뢰구간) 시 누수판단'
      },
      // ROI 테이블 데이터
      roiTableHeaders: [
        { text: 'No', value: 'no', width: '80px' },
        { text: '영역 번호', value: 'areaNumber', width: '120px' },
        { text: '시작지점 X좌표', value: 'startX', width: '150px' },
        { text: '시작지점 Y좌표', value: 'startY', width: '150px' },
        { text: '종료지점 X좌표', value: 'endX', width: '150px' },
        { text: '종료지점 Y좌표', value: 'endY', width: '150px' },
        { text: '작업', value: 'actions', width: '150px' }
      ],
      roiTableData: [
        {
          no: 1,
          areaNumber: 1,
          startX: 200,
          startY: 270,
          endX: 350,
          endY: 420
        },
        {
          no: 2,
          areaNumber: 2,
          startX: 350,
          startY: 270,
          endX: 500,
          endY: 420
        },
        {
          no: 3,
          areaNumber: 3,
          startX: 500,
          startY: 270,
          endX: 650,
          endY: 420
        },
        {
          no: 4,
          areaNumber: 4,
          startX: 650,
          startY: 200,
          endX: 750,
          endY: 300
        }
      ],
      alarmTableHeaders: [
        { text: 'No', value: 'no', width: '80px' },
        { text: '위치정보', value: 'locationInfo', width: '200px' },
        { text: '경보발령단계', value: 'alarmLevel', width: '150px' },
        { text: 'ROI', value: 'roi', width: '100px' },
        { text: '최대온도', value: 'maxTemp', width: '120px' },
        { text: '최소온도', value: 'minTemp', width: '120px' },
        { text: '평균온도', value: 'avgTemp', width: '120px' },
        { text: '경보발령시간', value: 'alarmTime', width: '200px' }
      ],
      alarmTableData: [],
      alarmPage: 1,
      alarmTotalItems: 0,
      alarmTotalPages: 1,
      alarmLoading: false,
      // 경보이력 필터
      alarmDateFilter: null,
      alarmDateMenu: false,
      alarmRoiFilter: null,
      alarmRoiOptions: [],
      jumpPage: null,
      sidebarDrawer: true,
      userName: 'system',
      showRoiDialog: false,
      selectedRoiData: null,
      isEditMode: false,
      showDeleteDialog: false,
      selectedDeleteItem: null,
      isDeleting: false,
      socketConnected: false,
      // 툴팁 관련 데이터
      showTooltip: false,
      tooltipStyle: {
        position: 'absolute',
        top: '0px',
        left: '0px',
        zIndex: 1000
      },
      tooltipData: {
        roiNumber: '',
        locationInfo: ''
      },
      // 경보알림관리 관련 데이터
      notificationSettings: {
        popupEnabled: true,
        smsEnabled: false,
        phoneNumber: '',
        thresholds: [
          { count: 1 },
          { count: 2 },
          { count: 3 },
          { count: 4 }
        ]
      },
      savingNotification: false,
      // 문자 직접 입력 다이얼로그 관련 데이터
      showMessageDialog: false,
      useSameNumber: false,
      messagePhoneNumber: '',
      messageContent: ''
    };
  },

  created() {
    // 진입 시 사이드바 닫기
    if (this.$sidebar) this.$sidebar.close();
    // 설정 로드
    this.loadSettings();
    // ROI 데이터 로드
    this.loadRoiData();
    // 경보이력 ROI 옵션 로드
    this.loadAlarmRoiOptions();
    this.loadAlarmHistory();
    // 알림 설정 로드
    this.loadNotificationSettings();
    // 사용자 정보 로드
    this.loadUserInfo();
    // 사이드바 상태 감지
    this.checkSidebarState();
    // bus 이벤트 리스너 등록
    bus.$on('sidebarToggled', this.handleSidebarToggle);
    
    // 소켓 연결 상태 초기화
    this.initializeSocketConnection();
  },

  async mounted() {
    console.log('AdminResult 페이지 로드됨');
    
    // 화면 진입시 updateInPageZone 호출 (1)
    try {
      await updateInPageZone(1);
    } catch (error) {
      console.error('updateInPageZone 호출 오류:', error);
    }
    
    // 사이드바 상태 초기화
    this.sidebarDrawer = this.$sidebar ? this.$sidebar.isOpen : false;
    
    // 소켓 연결 상태 모니터링
    this.monitorSocketConnection();
    
    // 초기 소켓 상태 확인
    setTimeout(() => {
      this.checkSocketStatus();
    }, 2000);
  },

  beforeDestroy() {
    // 화면 나갈때 updateInPageZone 호출 (0)
    try {
      updateInPageZone(0);
    } catch (error) {
      console.error('updateInPageZone 호출 오류:', error);
    }
    
    // bus 이벤트 리스너 정리
    bus.$off('sidebarToggled', this.handleSidebarToggle);
    
    // 소켓 이벤트 리스너 정리
    if (this.$socket && this.$socket.client) {
      this.$socket.client.off('connect', this.handleSocketConnect);
      this.$socket.client.off('disconnect', this.handleSocketDisconnect);
      this.$socket.client.off('unauthenticated', this.handleAuthenticationError);
      this.$socket.client.off('invalidToken', this.handleAuthenticationError);
    }
    
    // 소켓 모니터링 인터벌 정리
    if (this.socketMonitorInterval) {
      clearInterval(this.socketMonitorInterval);
      this.socketMonitorInterval = null;
    }
  },

  watch: {
    alarmPage: {
      handler(newPage, oldPage) {
        if (newPage !== oldPage) {
          console.log('alarmPage 변경 감지:', oldPage, '->', newPage);
          this.loadAlarmHistory();
        }
      },
      immediate: false
    },
    '$sidebar.isOpen': {
      handler(newVal) {
        this.sidebarDrawer = newVal;
      },
      immediate: true
    },
    // 소켓 연결 상태 감시
    '$socket.client.connected': {
      handler(newVal) {
        console.log('Socket connection status changed:', newVal);
        this.socketConnected = newVal;
        if (newVal) {
          this.handleSocketConnect();
        } else {
          this.handleSocketDisconnect();
        }
      },
      immediate: true
    }
  },

  methods: {
    goBack() {
      this.$router.go(-1);
    },
    
    goHome() {
      if (this.$sidebar) this.$sidebar.open();
      this.$router.push('/first-start');
    },
    
    changeStandard(item) {
      console.log('Change standard for item:', item);
      // 여기에 변경 로직 추가
    },
    
    addStandard() {
      if (this.newStandard.scenarioType) {
        const newItem = {
          no: this.tableData.length + 1,
          scenarioType: this.newStandard.scenarioType,
          stage1: Number(this.newStandard.stage1) || 0,
          stage2: Number(this.newStandard.stage2) || 0,
          stage3: Number(this.newStandard.stage3) || 0,
          stage4: Number(this.newStandard.stage4) || 0
        };
        this.tableData.push(newItem);
        this.clearForm();
      }
    },
    
    clearForm() {
      this.newStandard = {
        scenarioType: '',
        stage1: '',
        stage2: '',
        stage3: '',
        stage4: ''
      };
    },

    async loadSettings() {
      try {
        this.isLoading = true
        console.log('---------- loadSettings 시작 ----------')

        const response = await getAlertSettings()
        console.log('API 응답:', response)
        
        if (response && response.result) {
          const data = response.result
          
          if (data.alert_setting_json) {
            console.log('alert_setting_json 값 확인:', data.alert_setting_json)
            
            try {
              const parsedSettings = JSON.parse(data.alert_setting_json)
              console.log('JSON 파싱 결과:', parsedSettings)
              
              if (parsedSettings.alert && parsedSettings.alert.scenario) {
                this.selectedScenario = parsedSettings.alert.scenario
              }
              
              if (parsedSettings.alarmLevels) {
                this.updateTableData(parsedSettings.alarmLevels)
              }
            } catch (e) {
              console.error('JSON 파싱 오류:', e)
              await this.setDefaultSettings()
            }
          } else {
            console.log('alert_setting_json 필드가 없거나 빈 값입니다. 기본 설정을 사용합니다.')
            await this.setDefaultSettings()
          }
        } else {
          console.log('API 응답이 유효하지 않습니다. 기본 설정을 사용합니다.')
          await this.setDefaultSettings()
        }
        
        console.log('---------- loadSettings 종료 ----------')
      } catch (error) {
        console.error('설정 불러오기 오류:', error)
        await this.setDefaultSettings()
      } finally {
        this.isLoading = false
      }
    },

    async setDefaultSettings() {
      this.selectedScenario = 'scenario1'
      this.tableData = [
        {
          no: 1,
          scenarioType: '시나리오1: 온도차이(°C) 기준 + 온도변화량(%) 기준',
          stage1: 2,
          stage2: 5,
          stage3: 8,
          stage4: 10
        },
        {
          no: 2,
          scenarioType: '시나리오2: Pixel별 1시간 평균온도 C2M distance 기준',
          stage1: 6,
          stage2: 15,
          stage3: 20,
          stage4: 25
        }
      ]
    },

    updateTableData(alarmLevels) {
      if (alarmLevels.scenario1) {
        this.tableData[0].stage1 = alarmLevels.scenario1[0] || 2
        this.tableData[0].stage2 = alarmLevels.scenario1[1] || 5
        this.tableData[0].stage3 = alarmLevels.scenario1[2] || 8
        this.tableData[0].stage4 = alarmLevels.scenario1[3] || 10
      }
      if (alarmLevels.scenario2) {
        this.tableData[1].stage1 = alarmLevels.scenario2[0] || 6
        this.tableData[1].stage2 = alarmLevels.scenario2[1] || 15
        this.tableData[1].stage3 = alarmLevels.scenario2[2] || 20
        this.tableData[1].stage4 = alarmLevels.scenario2[3] || 25
      }
    },

    async saveSettings() {
      try {
        this.isLoading = true
        
        // 현재 선택한 시나리오 값 저장 (나중에 복원하기 위해)
        const currentScenario = this.selectedScenario
        
        const settings = {
          alert: {
            scenario: this.selectedScenario
          },
          alarmLevels: {
            scenario1: [
              Number(this.tableData[0].stage1),
              Number(this.tableData[0].stage2),
              Number(this.tableData[0].stage3),
              Number(this.tableData[0].stage4)
            ],
            scenario2: [
              Number(this.tableData[1].stage1),
              Number(this.tableData[1].stage2),
              Number(this.tableData[1].stage3),
              Number(this.tableData[1].stage4)
            ]
          }
        }
        
        const settingsJSON = JSON.stringify(settings)
        await saveAlertSettings({
          alert_setting_json: settingsJSON,
          fk_user_id: this.$store.state.auth.user?.id || 1
        })
        
        // 저장 후 현재 선택한 시나리오 값 유지
        this.selectedScenario = currentScenario
        
        this.$toast.success('설정이 성공적으로 저장되었습니다.')
      } catch (error) {
        console.error('설정 저장 오류:', error)
        this.$toast.error('설정 저장 중 오류가 발생했습니다.')
      } finally {
        this.isLoading = false
      }
    },

    async loadRoiData() {
      try {
        console.log('---------- loadRoiData 시작 ----------');
        const response = await getEventDetectionZone();
        console.log('ROI API 응답:', response);
        
        if (response && response.data) {
          const roiData = Array.isArray(response.data) ? response.data : [];
          this.roiTableData = roiData.map((item, index) => ({
            no: index + 1,
            id: item.id,
            areaNumber: item.type || index + 1,
            startX: item.regions && item.regions[0] ? item.regions[0].left || 0 : 0,
            startY: item.regions && item.regions[0] ? item.regions[0].top || 0 : 0,
            endX: item.regions && item.regions[0] ? item.regions[0].right || 100 : 100,
            endY: item.regions && item.regions[0] ? item.regions[0].bottom || 100 : 100,
            description: item.description || '',
            cameraId: item.cameraId || 0
          }));
        } else {
          console.log('ROI 데이터가 없습니다. 기본 데이터를 사용합니다.');
          this.setDefaultRoiData();
        }
        
        console.log('최종 ROI 데이터:', this.roiTableData);
        console.log('---------- loadRoiData 종료 ----------');
      } catch (error) {
        console.error('ROI 데이터 불러오기 오류:', error);
        this.setDefaultRoiData();
      }
    },

    setDefaultRoiData() {
      this.roiTableData = [
        {
          no: 1,
          id: null,
          areaNumber: 1,
          startX: 200,
          startY: 270,
          endX: 350,
          endY: 420
        },
        {
          no: 2,
          id: null,
          areaNumber: 2,
          startX: 350,
          startY: 270,
          endX: 500,
          endY: 420
        },
        {
          no: 3,
          id: null,
          areaNumber: 3,
          startX: 500,
          startY: 270,
          endX: 650,
          endY: 420
        },
        {
          no: 4,
          id: null,
          areaNumber: 4,
          startX: 650,
          startY: 200,
          endX: 750,
          endY: 300
        }
      ];
    },

    async addRoiArea() {
      this.isEditMode = false;
      this.selectedRoiData = null;
      this.showRoiDialog = true;
    },

    onRoiRowClick(item) {
      // row 클릭 시 수정 모드로 전환
      this.editRoiArea(item);
    },

    async editRoiArea(item) {
      try {
        console.log('editRoiArea 호출됨:', item);
        
        // 로딩 상태 설정
        this.$set(item, 'loading', true);
        
        // API 호출하여 상세 정보 가져오기
        const response = await getEventDetectionZone();
        console.log('API 응답:', response);
        
        const roiDetail = response.data.find(roi => roi.id === item.id);
        console.log('찾은 ROI 상세 정보:', roiDetail);
        
        if (roiDetail) {
          // roiWindow에 전달할 데이터 준비
          this.selectedRoiData = {
            id: roiDetail.id,
            roiId: roiDetail.type?.toString() || item.areaNumber.toString(),
            startPointX: roiDetail.regions?.[0]?.left?.toString() || item.startX.toString(),
            startPointY: roiDetail.regions?.[0]?.top?.toString() || item.startY.toString(),
            endPointX: roiDetail.regions?.[0]?.right?.toString() || item.endX.toString(),
            endPointY: roiDetail.regions?.[0]?.bottom?.toString() || item.endY.toString(),
            description: roiDetail.description || `영역 ${item.areaNumber}`,
            cameraId: roiDetail.cameraId || 0,
            options: roiDetail.options || {
              forceCloseTimer: 30,
              dwellTimer: 50,
              sensitivity: 75,
              difference: 50
            }
          };
          
          console.log('selectedRoiData 설정:', this.selectedRoiData);
          this.isEditMode = true;
          this.showRoiDialog = true;
          
          console.log('다이얼로그 열림, isEditMode:', this.isEditMode);
        } else {
          this.$toast.error('ROI 정보를 찾을 수 없습니다.');
        }
      } catch (error) {
        console.error('ROI 수정 데이터 로드 오류:', error);
        this.$toast.error('ROI 정보를 불러오는 중 오류가 발생했습니다.');
      } finally {
        // 로딩 상태 해제
        this.$set(item, 'loading', false);
      }
    },

    confirmDeleteRoiArea(item) {
      this.selectedDeleteItem = item;
      this.showDeleteDialog = true;
    },

    async deleteRoiArea() {
      if (!this.selectedDeleteItem) return;
      
      this.isDeleting = true;
      
      try {
        if (this.selectedDeleteItem.id) {
          // 삭제 후 남은 리스트로 roiEnable 계산 (EventDetectionZone.vue와 동일한 로직)
          const remainList = this.roiTableData.filter(area => area.id !== this.selectedDeleteItem.id);
          const roiEnableArr = Array(10).fill('0');
          remainList.forEach(zone => {
            const t = Number(zone.areaNumber);
            if (!isNaN(t) && t >= 0 && t <= 9) {
              roiEnableArr[9 - t] = '1';
            }
          });
          const roiEnable = roiEnableArr.join('');
          const roiIndex = Number(this.selectedDeleteItem.areaNumber);
          
          // 서버에서 삭제 (roiEnable과 roiIndex 파라미터 포함)
          await deleteEventDetectionZone(`${this.selectedDeleteItem.id}?roiEnable=${roiEnable}&roiIndex=${roiIndex}`);
          this.$toast.success('영역이 삭제되었습니다.');
        } else {
          // 로컬에서만 삭제 (새로 추가된 항목)
          const index = this.roiTableData.findIndex(area => area.no === this.selectedDeleteItem.no);
          if (index > -1) {
            this.roiTableData.splice(index, 1);
            // 번호 재정렬
            this.roiTableData.forEach((area, idx) => {
              area.no = idx + 1;
            });
            this.$toast.success('영역이 삭제되었습니다.');
          }
        }
        
        // 데이터 다시 로드
        await this.loadRoiData();
        
        // 다이얼로그 닫기
        this.showDeleteDialog = false;
        this.selectedDeleteItem = null;
      } catch (error) {
        console.error('ROI 삭제 오류:', error);
        this.$toast.error('영역 삭제 중 오류가 발생했습니다.');
      } finally {
        this.isDeleting = false;
      }
    },



    async loadAlarmHistory() {
      try {
        this.alarmLoading = true;
        console.log('경보이력 로딩 시작 - 페이지:', this.alarmPage);
        
        // 위치정보 가져오기
        let locationInfo = '알 수 없음';
        try {
          const eventSettingData = await getEventSetting();
          if (eventSettingData && eventSettingData.system_json) {
            const system = JSON.parse(eventSettingData.system_json);
            locationInfo = system.location_info || '알 수 없음';
          }
        } catch (e) {
          console.error('위치정보 로딩 오류:', e);
        }
        
        // 필터 파라미터 구성
        let params = `?page=${this.alarmPage}&pageSize=10&includeClosed=true`;
        
        // 경보발령 일자 필터
        if (this.alarmDateFilter) {
          const startDate = `${this.alarmDateFilter}T00:00:00`;
          const endDate = `${this.alarmDateFilter}T23:59:59`;
          params += `&startDate=${startDate}&endDate=${endDate}`;
        }
        
        // ROI 필터는 클라이언트 측에서 필터링 (API에 ROI 필터가 없을 수 있음)
        
        // 모든 경보이력 조회 (popup_close 조건 제거)
        const res = await getAlerts(params);
        
        console.log('경보이력 API 응답 전체:', res);
        console.log('경보이력 API 응답 data:', res?.data);
        console.log('경보이력 API 응답 data.result:', res?.data?.result);
        console.log('경보이력 API 응답 data.pagination:', res?.data?.pagination);
        
        // 응답 구조 확인: res.data.result 또는 res.data.items 또는 res.data
        let alerts = [];
        let pagination = null;
        
        if (res && res.data) {
          // PaginationMiddleware를 거친 경우
          if (res.data.result) {
            alerts = res.data.result;
            pagination = res.data.pagination;
          } else if (res.data.items) {
            alerts = res.data.items;
            pagination = res.data.pagination;
          } else if (Array.isArray(res.data)) {
            alerts = res.data;
          }
        }
        
        console.log('경보이력 추출된 데이터:', alerts);
        console.log('경보이력 페이지네이션:', pagination);
        
        // ROI 필터 적용 (클라이언트 측 필터링)
        let filteredAlerts = alerts;
        if (this.alarmRoiFilter && alerts && alerts.length > 0) {
          filteredAlerts = alerts.filter(alert => {
            try {
              if (alert.alert_info_json) {
                let alertInfo = {};
                if (typeof alert.alert_info_json === 'string') {
                  const jsonStr = alert.alert_info_json.trim();
                  if (jsonStr.endsWith('}') || jsonStr.endsWith(']')) {
                    alertInfo = JSON.parse(jsonStr);
                  } else {
                    const lastBrace = jsonStr.lastIndexOf('}');
                    if (lastBrace > 0) {
                      alertInfo = JSON.parse(jsonStr.substring(0, lastBrace + 1));
                    }
                  }
                } else if (typeof alert.alert_info_json === 'object') {
                  alertInfo = alert.alert_info_json;
                }
                
                // ROI 번호 추출
                let roi = null;
                if (alertInfo.roi_polygon && alertInfo.roi_polygon.main_roi) {
                  const zoneType = alertInfo.roi_polygon.main_roi.zone_type;
                  if (zoneType !== null && zoneType !== undefined && zoneType !== '') {
                    const match = zoneType.toString().match(/Z?0*(\d+)/);
                    if (match) {
                      roi = parseInt(match[1]);
                    } else {
                      // 매치되지 않으면 숫자로 직접 변환 시도
                      const num = parseInt(zoneType);
                      if (!isNaN(num)) {
                        roi = num;
                      }
                    }
                  }
                } else if (alertInfo.zone_type !== null && alertInfo.zone_type !== undefined && alertInfo.zone_type !== '') {
                  const match = alertInfo.zone_type.toString().match(/Z?0*(\d+)/);
                  if (match) {
                    roi = parseInt(match[1]);
                  } else {
                    // 매치되지 않으면 숫자로 직접 변환 시도
                    const num = parseInt(alertInfo.zone_type);
                    if (!isNaN(num)) {
                      roi = num;
                    }
                  }
                } else if (alert.alert_type) {
                  const match = alert.alert_type.toString().match(/S?0*(\d+)/);
                  if (match) {
                    roi = parseInt(match[1]) - 1;
                  }
                }
                
                // 필터와 비교
                const filterRoi = parseInt(this.alarmRoiFilter);
                return roi !== null && roi === filterRoi;
              }
            } catch (e) {
              console.error('ROI 필터링 오류:', e);
            }
            return false;
          });
        }
        
        if (filteredAlerts && filteredAlerts.length > 0) {
          this.alarmTableData = filteredAlerts.map((alert, idx) => {
            // alert_info_json 파싱하여 ROI 및 온도 정보 추출
            let roi = '정보 없음';
            let maxTemp = '--';
            let minTemp = '--';
            let avgTemp = '--';
            
            try {
              if (alert.alert_info_json) {
                let alertInfo = {};
                if (typeof alert.alert_info_json === 'string') {
                  const jsonStr = alert.alert_info_json.trim();
                  if (jsonStr.endsWith('}') || jsonStr.endsWith(']')) {
                    alertInfo = JSON.parse(jsonStr);
                  } else {
                    // JSON이 잘린 경우 처리
                    const lastBrace = jsonStr.lastIndexOf('}');
                    if (lastBrace > 0) {
                      alertInfo = JSON.parse(jsonStr.substring(0, lastBrace + 1));
                    }
                  }
                } else if (typeof alert.alert_info_json === 'object') {
                  alertInfo = alert.alert_info_json;
                }
                
                // ROI 번호 추출
                if (alertInfo.roi_polygon && alertInfo.roi_polygon.main_roi) {
                  const zoneType = alertInfo.roi_polygon.main_roi.zone_type;
                  if (zoneType !== null && zoneType !== undefined && zoneType !== '') {
                    // "Z1" -> "ROI 1", "Z001" -> "ROI 1", 0 -> "ROI 0" 형식으로 변환
                    const match = zoneType.toString().match(/Z?0*(\d+)/);
                    if (match) {
                      roi = `ROI ${parseInt(match[1])}`;
                    } else {
                      // 매치되지 않으면 숫자로 직접 변환 시도
                      const num = parseInt(zoneType);
                      if (!isNaN(num)) {
                        roi = `ROI ${num}`;
                      } else {
                        roi = zoneType;
                      }
                    }
                  }
                } else if (alertInfo.zone_type !== null && alertInfo.zone_type !== undefined && alertInfo.zone_type !== '') {
                  const match = alertInfo.zone_type.toString().match(/Z?0*(\d+)/);
                  if (match) {
                    roi = `ROI ${parseInt(match[1])}`;
                  } else {
                    // 매치되지 않으면 숫자로 직접 변환 시도
                    const num = parseInt(alertInfo.zone_type);
                    if (!isNaN(num)) {
                      roi = `ROI ${num}`;
                    } else {
                      roi = alertInfo.zone_type;
                    }
                  }
                } else if (alert.alert_type) {
                  // alert_type에서 추출 (예: "S001" -> "ROI 0")
                  const match = alert.alert_type.toString().match(/S?0*(\d+)/);
                  if (match) {
                    const roiNum = parseInt(match[1]) - 1;
                    roi = `ROI ${roiNum}`;
                  } else {
                    roi = alert.alert_type;
                  }
                }
                
                // 온도 정보 추출
                if (alertInfo.temperature_stats) {
                  maxTemp = typeof alertInfo.temperature_stats.max === 'number' 
                    ? alertInfo.temperature_stats.max.toFixed(1) 
                    : '--';
                  minTemp = typeof alertInfo.temperature_stats.min === 'number' 
                    ? alertInfo.temperature_stats.min.toFixed(1) 
                    : '--';
                  avgTemp = typeof alertInfo.temperature_stats.average === 'number' 
                    ? alertInfo.temperature_stats.average.toFixed(1) 
                    : '--';
                } else if (alertInfo.max_temp !== undefined || alertInfo.min_temp !== undefined || alertInfo.avg_temp !== undefined) {
                  maxTemp = typeof alertInfo.max_temp === 'number' 
                    ? alertInfo.max_temp.toFixed(1) 
                    : '--';
                  minTemp = typeof alertInfo.min_temp === 'number' 
                    ? alertInfo.min_temp.toFixed(1) 
                    : '--';
                  avgTemp = typeof alertInfo.avg_temp === 'number' 
                    ? alertInfo.avg_temp.toFixed(1) 
                    : '--';
                }
              }
            } catch (e) {
              console.error('alert_info_json 파싱 오류:', e, 'alert:', alert);
            }
            
            // level4인 경우 정보 없음 -> ROI 0으로 표현
            const alarmLevel = parseInt(alert.alert_level) || 1;
            // roi가 '정보 없음' 또는 '정보없음'인 경우 모두 처리
            if (alarmLevel === 4 && (roi === '정보 없음' || roi === '정보없음' || !roi || roi.trim() === '')) {
              const originalRoi = roi; // 원본 값 저장
              roi = 'ROI 0';
              console.log('level4 ROI 변환:', {
                alert_level: alert.alert_level,
                alarmLevel: alarmLevel,
                originalRoi: originalRoi,
                convertedRoi: 'ROI 0',
                alert_id: alert.id || alert.alert_id
              });
            }
            
            return {
              no: (this.alarmPage - 1) * 10 + idx + 1,
              locationInfo: locationInfo,
              alarmLevel: alarmLevel,
              roi: roi,
              maxTemp: maxTemp,
              minTemp: minTemp,
              avgTemp: avgTemp,
              alarmTime: alert.alert_accur_time || alert.created_at || '',
              alert_info_json: alert.alert_info_json || null
            };
          });
          
          // 페이지네이션 정보 업데이트 (필터링된 결과 기준)
          if (pagination) {
            // ROI 필터가 적용된 경우 필터링된 개수 사용
            if (this.alarmRoiFilter) {
              this.alarmTotalItems = filteredAlerts.length;
              this.alarmTotalPages = Math.ceil(this.alarmTotalItems / 10);
            } else {
              this.alarmTotalItems = pagination.totalItems || 0;
              this.alarmTotalPages = pagination.totalPages || 1;
              this.alarmPage = pagination.currentPage || this.alarmPage;
            }
          } else {
            this.alarmTotalItems = filteredAlerts.length;
            this.alarmTotalPages = Math.ceil(this.alarmTotalItems / 10);
          }
          
          console.log('경보이력 데이터 매핑 완료:', this.alarmTableData);
          console.log('페이지네이션 정보:', {
            totalItems: this.alarmTotalItems,
            totalPages: this.alarmTotalPages,
            currentPage: this.alarmPage
          });
        } else {
          console.log('경보이력 데이터가 없습니다.');
          this.alarmTableData = [];
          this.alarmTotalItems = 0;
          this.alarmTotalPages = 1;
        }
      } catch (error) {
        console.error('경보이력 로딩 오류:', error);
        this.$toast.error('경보이력을 불러오는 중 오류가 발생했습니다.');
        this.alarmTableData = [];
        this.alarmTotalItems = 0;
        this.alarmTotalPages = 1;
      } finally {
        this.alarmLoading = false;
      }
    },

    applyAlarmFilters() {
      // 필터 적용 시 첫 페이지로 이동하고 데이터 다시 로드
      this.alarmPage = 1;
      this.loadAlarmHistory();
    },

    resetAlarmFilters() {
      // 필터 초기화
      this.alarmDateFilter = null;
      this.alarmRoiFilter = null;
      this.alarmPage = 1;
      this.loadAlarmHistory();
    },

    async loadAlarmRoiOptions() {
      // ROI 옵션 로드 (getRoiDataList API 사용)
      try {
        const { getRoiDataList } = await import('@/api/statistic.api');
        const response = await getRoiDataList();
        
        if (response && response.data && response.data.success && response.data.result) {
          this.alarmRoiOptions = response.data.result
            .map(zone => {
              // zone_type에서 ROI 번호 추출
              let roiNumber = null;
              if (zone.zone_type !== null && zone.zone_type !== undefined && zone.zone_type !== '') {
                const match = zone.zone_type.toString().match(/Z?0*(\d+)/);
                if (match) {
                  roiNumber = parseInt(match[1]);
                } else {
                  // 매치되지 않으면 숫자로 직접 변환 시도
                  const num = parseInt(zone.zone_type);
                  if (!isNaN(num)) {
                    roiNumber = num;
                  }
                }
              } else if (zone.zone_desc) {
                const match = zone.zone_desc.toString().match(/ROI[-\s]?(\d+)/i);
                if (match) {
                  roiNumber = parseInt(match[1]);
                }
              }
              
              if (roiNumber !== null) {
                return {
                  text: `ROI ${roiNumber}`,
                  value: roiNumber
                };
              }
              return null;
            })
            .filter(option => option !== null)
            .sort((a, b) => a.value - b.value);
        }
      } catch (error) {
        console.error('ROI 옵션 로드 오류:', error);
        // 기본 ROI 옵션 설정 (0-9)
        this.alarmRoiOptions = Array.from({ length: 10 }, (_, i) => ({
          text: `ROI ${i}`,
          value: i
        }));
      }
    },

    // 툴팁 관련 메서드
    showRoiTooltip(event, item) {
      // ROI 번호 추출 (alert_info_json에서 zone_type 가져오기)
      let roiNumber = '정보 없음';
      try {
        if (item.alert_info_json) {
          const alertInfo = JSON.parse(item.alert_info_json);
          // zone_type이 0이어도 유효한 값이므로 처리
          if (alertInfo.zone_type !== null && alertInfo.zone_type !== undefined && alertInfo.zone_type !== '') {
            const match = alertInfo.zone_type.toString().match(/Z?0*(\d+)/);
            if (match) {
              roiNumber = `ROI ${parseInt(match[1])}`;
            } else {
              // 매치되지 않으면 숫자로 직접 변환 시도
              const num = parseInt(alertInfo.zone_type);
              if (!isNaN(num)) {
                roiNumber = `ROI ${num}`;
              } else {
                roiNumber = alertInfo.zone_type.toString();
              }
            }
          } else if (alertInfo.roi_polygon && alertInfo.roi_polygon.main_roi) {
            const zoneType = alertInfo.roi_polygon.main_roi.zone_type;
            if (zoneType !== null && zoneType !== undefined && zoneType !== '') {
              const match = zoneType.toString().match(/Z?0*(\d+)/);
              if (match) {
                roiNumber = `ROI ${parseInt(match[1])}`;
              } else {
                const num = parseInt(zoneType);
                if (!isNaN(num)) {
                  roiNumber = `ROI ${num}`;
                } else {
                  roiNumber = zoneType.toString();
                }
              }
            }
          }
        }
      } catch (e) {
        console.error('ROI 정보 파싱 오류:', e);
      }

      // 툴팁 데이터 설정
      this.tooltipData = {
        roiNumber: roiNumber,
        locationInfo: item.locationInfo
      };

      // 툴팁 위치 계산 - 마우스 위치 기준
      this.tooltipStyle = {
        position: 'fixed',
        top: `${event.clientY - 80}px`,
        left: `${event.clientX + 10}px`,
        zIndex: 1000
      };

      // 툴팁 표시
      this.showTooltip = true;
    },

    hideRoiTooltip() {
      this.showTooltip = false;
    },

    updateTooltipPosition(event) {
      if (this.showTooltip) {
        this.tooltipStyle = {
          position: 'fixed',
          top: `${event.clientY - 80}px`,
          left: `${event.clientX + 10}px`,
          zIndex: 1000
        };
      }
    },

    // 경보알림관리 관련 메서드
    async saveNotificationSettings() {
      try {
        this.savingNotification = true;
        
        // 현재 설정 가져오기
        const currentSettings = await getAlertSettings();
        let alertSettingJson = {};
        
        if (currentSettings && currentSettings.result && currentSettings.result.alert_setting_json) {
          try {
            alertSettingJson = JSON.parse(currentSettings.result.alert_setting_json);
          } catch (e) {
            console.error('기존 설정 파싱 오류:', e);
          }
        }
        
        // 알림 설정 추가/업데이트
        alertSettingJson.notification = {
          popupEnabled: this.notificationSettings.popupEnabled,
          smsEnabled: this.notificationSettings.smsEnabled,
          phoneNumber: this.notificationSettings.phoneNumber,
          thresholds: this.notificationSettings.thresholds.map((t, index) => ({
            level: index + 1,
            count: parseInt(t.count) || 0
          }))
        };
        
        // 설정 저장
        await saveAlertSettings({
          alert_setting_json: JSON.stringify(alertSettingJson)
        });
        
        this.$toast.success('경보 알림 설정이 저장되었습니다.');
      } catch (error) {
        console.error('경보 알림 설정 저장 오류:', error);
        this.$toast.error('경보 알림 설정 저장 중 오류가 발생했습니다.');
      } finally {
        this.savingNotification = false;
      }
    },

    async loadNotificationSettings() {
      try {
        const currentSettings = await getAlertSettings();
        
        if (currentSettings && currentSettings.result && currentSettings.result.alert_setting_json) {
          try {
            const alertSettingJson = JSON.parse(currentSettings.result.alert_setting_json);
            
            if (alertSettingJson.notification) {
              const notification = alertSettingJson.notification;
              
              this.notificationSettings.popupEnabled = notification.popupEnabled !== undefined ? notification.popupEnabled : true;
              this.notificationSettings.smsEnabled = notification.smsEnabled !== undefined ? notification.smsEnabled : false;
              this.notificationSettings.phoneNumber = notification.phoneNumber || '';
              
              if (notification.thresholds && Array.isArray(notification.thresholds)) {
                notification.thresholds.forEach((threshold, index) => {
                  if (index < this.notificationSettings.thresholds.length) {
                    this.notificationSettings.thresholds[index].count = threshold.count || 0;
                  }
                });
              }
            }
          } catch (e) {
            console.error('알림 설정 파싱 오류:', e);
          }
        }
      } catch (error) {
        console.error('알림 설정 로딩 오류:', error);
      }
    },

    getAlarmLevelColor(level) {
      const levelNum = parseInt(level);
      // 예시: 심각(4단계) 빨강, 경고(3단계) 주황, 주의(2단계) 노랑, 정보(1단계) 파랑
      if (levelNum === 4) return 'red';
      if (levelNum === 3) return 'orange';
      if (levelNum === 2) return 'yellow';
      if (levelNum === 1) return 'blue';
      return 'grey';
    },
    
    getAlarmLevelIcon(level) {
      const levelNum = parseInt(level);
      if (levelNum === 4) return 'mdi-alert-octagon';
      if (levelNum === 3) return 'mdi-alert-circle';
      if (levelNum === 2) return 'mdi-alert';
      if (levelNum === 1) return 'mdi-information';
      return 'mdi-block-helper';
    },
    
    getAlarmLevelText(level) {
      const levelNum = parseInt(level);
      if (levelNum === 4) return '심각(4단계)';
      if (levelNum === 3) return '위험(3단계)';
      if (levelNum === 2) return '경고(2단계)';
      if (levelNum === 1) return '주의(1단계)';
      return '알수없음';
    },
    
    formatDateTime(dt) {
      if (!dt) return '';
      
      try {
        // ISO 문자열이면 포맷팅
        if (typeof dt === 'string') {
          return dt.replace('T', ' ').substring(0, 19);
        }
        
        // Date 객체인 경우
        if (dt instanceof Date) {
          return dt.toISOString().replace('T', ' ').substring(0, 19);
        }
        
        return String(dt);
      } catch (error) {
        console.error('날짜 포맷팅 오류:', error);
        return String(dt);
      }
    },
    checkSidebarState() {
      // 사이드바 상태 확인
      if (this.$sidebar) {
        this.sidebarDrawer = this.$sidebar.isOpen;
      }
    },

    handleSidebarToggle(isOpen) {
      this.sidebarDrawer = isOpen;
    },

    async loadUserInfo() {
      try {
        // 사용자 정보 로드 로직
        const user = await getUser(this.$store.state.auth.user.id);
        if (user.data && user.data.userName) {
          this.userName = user.data.userName;
        }
      } catch (error) {
        console.error('사용자 정보를 불러오는데 실패했습니다:', error);
        this.userName = 'system';
      }
    },

    async logout() {
      await this.$store.dispatch('auth/logout');
      this.$router.push('/');
    },







    onRoiSaved() {
      // ROI 저장 후 리스트 갱신
      this.loadRoiData();
      this.isEditMode = false;
      this.selectedRoiData = null;
      this.showRoiDialog = false;
    },

    // ROI 영역 번호 중복 체크 메서드 추가
    checkDuplicateRoiNumber(roiId, excludeId = null) {
      return this.roiTableData.some(roi => {
        // 수정 모드일 때는 현재 편집 중인 항목은 제외
        if (excludeId && roi.id === excludeId) {
          return false;
        }
        return Number(roi.areaNumber) === Number(roiId);
      });
    },

    jumpToPage() {
      if (this.jumpPage && this.jumpPage >= 1 && this.jumpPage <= this.alarmTotalPages) {
        console.log('페이지로 이동:', this.jumpPage);
        this.alarmPage = this.jumpPage;
        this.loadAlarmHistory();
        this.jumpPage = null; // 입력 필드 초기화
      }
    },

    goToPage(page) {
      if (page >= 1 && page <= this.alarmTotalPages) {
        this.alarmPage = page;
        this.loadAlarmHistory();
      }
    },

    getVisiblePages() {
      const pages = [];
      const totalPages = this.alarmTotalPages;
      const currentPage = this.alarmPage;

      if (totalPages <= 7) {
        for (let i = 1; i <= totalPages; i++) {
          pages.push(i);
        }
      } else {
        // 현재 페이지가 중앙에 위치하도록 페이지 번호 배열 구성
        if (currentPage <= 4) {
          pages.push(1, 2, 3, 4, 5, '...', totalPages);
        } else if (currentPage >= totalPages - 3) {
          pages.push(1, '...', totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages);
        } else {
          pages.push(1, '...', currentPage - 1, currentPage, currentPage + 1, '...', totalPages);
        }
      }
      return pages;
    },

    // 소켓 연결 초기화
    initializeSocketConnection() {
      console.log('Initializing socket connection...');
      
      // 현재 사용자 토큰 확인
      const currentUser = this.$store.state.auth.user;
      if (!currentUser?.access_token) {
        console.warn('No access token available, cannot connect to socket');
        return;
      }
      
      // 소켓이 사용 가능할 때까지 대기
      const initSocket = () => {
        if (this.$socket && this.$socket.client) {
          this.$socket.client.io.opts.extraHeaders = {
            Authorization: `Bearer ${currentUser.access_token}`,
          };
          
          // 소켓 이벤트 리스너 등록
          this.$socket.client.on('connect', this.handleSocketConnect);
          this.$socket.client.on('disconnect', this.handleSocketDisconnect);
          this.$socket.client.on('unauthenticated', this.handleAuthenticationError);
          this.$socket.client.on('invalidToken', this.handleAuthenticationError);
          
          // 소켓 연결 시도
          if (!this.$socket.client.connected) {
            console.log('Attempting to connect to socket...');
            this.$socket.client.connect();
          }
        } else {
          console.log('Socket not available yet, retrying in 500ms...');
          setTimeout(initSocket, 500);
        }
      };
      
      initSocket();
    },
    
    // 소켓 연결 상태 모니터링
    monitorSocketConnection() {
      // 주기적으로 소켓 연결 상태 확인
      this.socketMonitorInterval = setInterval(() => {
        if (this.$socket && this.$socket.client) {
          const isConnected = this.$socket.client.connected;
          if (isConnected !== this.socketConnected) {
            console.log('Socket connection status changed:', isConnected);
            this.socketConnected = isConnected;
          }
          
          // 연결이 끊어진 경우 재연결 시도
          if (!isConnected && this.$store.state.auth.user?.access_token) {
            console.log('Socket disconnected, attempting to reconnect...');
            this.reconnectSocket();
          }
        }
      }, 5000); // 5초마다 확인
    },
    
    // 소켓 연결 성공 핸들러
    handleSocketConnect() {
      console.log('Socket connected successfully');
      this.socketConnected = true;
      
      // 연결 후 필요한 초기화 작업 수행
      this.afterSocketConnect();
    },
    
    // 소켓 연결 해제 핸들러
    handleSocketDisconnect() {
      console.log('Socket disconnected');
      this.socketConnected = false;
    },
    
    // 소켓 연결 후 초기화 작업
    afterSocketConnect() {
      console.log('Performing post-connection initialization...');
      
      // 필요한 경우 여기에 추가 초기화 로직 추가
      // 예: 스트림 재연결, 데이터 동기화 등
    },
    
    // 소켓 재연결
    reconnectSocket() {
      console.log('Attempting to reconnect socket...');
      
      const currentUser = this.$store.state.auth.user;
      if (!currentUser?.access_token) {
        console.warn('No access token available for reconnection');
        return;
      }
      
      if (this.$socket && this.$socket.client) {
        // 기존 연결 정리
        this.$socket.client.close();
        
        // 헤더 재설정
        this.$socket.client.io.opts.extraHeaders = {
          Authorization: `Bearer ${currentUser.access_token}`,
        };
        
        // 재연결 시도
        setTimeout(() => {
          this.$socket.client.open();
        }, 1000);
      }
    },
    
    // 인증 오류 처리
    handleAuthenticationError() {
      console.log('Authentication error detected, attempting to refresh token...');
      
      // 토큰 갱신 시도 또는 로그아웃 처리
      this.$store.dispatch('auth/logout').then(() => {
        this.$router.push('/login');
      });
    },
    
    // 소켓 연결 상태 확인
    checkSocketStatus() {
      if (this.$socket && this.$socket.client) {
        const isConnected = this.$socket.client.connected;
        const currentUser = this.$store.state.auth.user;
        
        console.log('Socket Status Check:', {
          connected: isConnected,
          hasToken: !!currentUser?.access_token,
          username: currentUser?.username || 'unknown'
        });
        
        return {
          connected: isConnected,
          hasToken: !!currentUser?.access_token,
          username: currentUser?.username || 'unknown'
        };
      }
      return { connected: false, hasToken: false, username: 'unknown' };
    },
    
    // 문자 직접 입력 다이얼로그 관련 메서드
    openMessageDialog() {
      this.showMessageDialog = true;
      this.useSameNumber = false;
      this.messagePhoneNumber = '';
      this.messageContent = '';
    },
    
    closeMessageDialog() {
      this.showMessageDialog = false;
      this.messagePhoneNumber = '';
      this.messageContent = '';
    },
    
    sendMessage() {
      // TODO: 실제 메시지 전송 로직 구현
      console.log('메시지 전송:', {
        useSameNumber: this.useSameNumber,
        phoneNumber: this.messagePhoneNumber,
        content: this.messageContent
      });
      
      // 전송 성공 후 다이얼로그 닫기
      this.$toast.success('메시지가 전송되었습니다.');
      this.closeMessageDialog();
    }
  }
};
</script>

<style scoped>
.admin-result {
  min-height: 100vh;
}

.v-card {
  margin: 20px;
}

/* Header Styles */
.header-section {
  display: flex;
  align-items: center;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 4px;
  transition: background-color 0.3s ease;
}

.header-section:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.header-section.active {
  background-color: rgba(255, 255, 255, 0.2);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.header-btn {
  color: white !important;
  text-transform: none;
  font-weight: normal;
}

.header-btn:hover {
  background-color: transparent !important;
}

.header-icon {
  color: white !important;
}

.header-text {
  color: white;
  font-size: 14px;
  font-weight: normal;
}

.header-divider {
  height: 24px;
  color: #e0e0e0;
}

/* System Button Styles */
.system-btn {
  display: flex;
  align-items: center;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 4px;
  transition: background-color 0.3s ease;
}

.system-btn:hover {
  background-color: rgba(0, 0, 0, 0.04);
}

.system-btn-text {
  color: #757575 !important;
  text-transform: none;
  font-weight: normal;
}

.system-btn-text:hover {
  background-color: transparent !important;
}

.system-btn-icon-only {
  color: #757575 !important;
}

.system-btn-icon-only:hover {
  background-color: transparent !important;
}

.system-btn-icon {
  color: #757575 !important;
}

.system-btn-label {
  color: #757575;
  font-size: 14px;
  font-weight: normal;
}

.system-divider {
  height: 24px;
  color: #e0e0e0;
}

/* Logo container styles */
.logo-container {
  display: flex;
  align-items: center;
  margin-left: 20px;
}

@media (min-width: 1200px) {
  .logo-container {
    margin-left: calc((100vw - 1500px) / 2 + 20px);
  }
}

@media (max-width: 1199px) {
  .logo-container {
    margin-left: 20px;
  }
}

/* App Bar specific styles */
::v-deep .v-app-bar {
  border-bottom: 1px solid #e0e0e0;
}

::v-deep .v-app-bar .v-toolbar__content {
  padding: 0 16px;
}

/* Main content area styles */
.admin-main {
  background-color: #f5f5f5;
  padding: 0 !important;
  min-height: calc(100vh - 64px);
}

.gradient-header {
  background: linear-gradient(135deg, #1976d2 0%, #1565c0 100%);
  color: white;
  padding: 20px 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.header-content {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 120px;
  max-width: 900px;
  margin: 0 auto;
  padding: 0 20px;
}

.menu-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  padding: 20px 30px;
  border-radius: 8px;
  transition: all 0.3s ease;
  min-width: 120px;
}

.menu-item:hover {
  background-color: rgba(255, 255, 255, 0.1);
  transform: translateY(-2px);
}

.menu-icon {
  font-size: 28px;
  margin-bottom: 12px;
  color: white;
  height: 28px;
  width: 28px;
}

.menu-text {
  font-size: 14px;
  font-weight: 500;
  color: white;
  text-align: center;
  line-height: 1.2;
  white-space: nowrap;
}

/* Button section styles */
.button-section {
  background: linear-gradient(135deg, #1976d2 0%, #1565c0 100%);
  padding: 16px 0;
  border-bottom: none;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  width: 100vw;
  margin-left: calc(-50vw + 50%);
  margin-right: calc(-50vw + 50%);
}

.button-container {
  display: flex;
  align-items: center;
  max-width: 1450px;
  margin: 0 auto;
  padding: 0 30px;
}

.content-area {
  flex: 1;
  padding: 40px 20px;
  min-height: calc(100vh - 200px);
}

@media (min-width: 1200px) {
  .button-container {
    margin: 0 auto;
    padding: 0 30px;
  }
  
  .content-area {
    padding: 40px 20px;
  }
}

@media (max-width: 1199px) {
  .button-container {
    margin: 0 auto;
    padding: 0 30px;
  }
  
  .content-area {
    padding: 40px 20px;
  }
}

.content-container {
  background-color: white;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  margin: 0 auto;
  max-width: 1400px;
  min-height: 1000px !important;
  position: relative;
  z-index: 2;
}

.content-title {
  color: #6a6a6a;
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 30px;
  text-align: left;
  padding: 20px 30px;
}

.standard-input {
  max-width: 100px;
  background: white !important;
  text-align: center !important;
}

/* 필터 섹션의 standard-input은 max-width 제한 없음 */
.filter-section .standard-input {
  max-width: none;
  text-align: left !important;
  background: white !important;
}

/* 필터 섹션의 v-select 스타일 */
.filter-section .standard-input ::v-deep .v-select__selection {
  background: white !important;
  color: #333 !important;
}

.filter-section .standard-input ::v-deep .v-select__slot {
  background: white !important;
}

.filter-section .standard-input ::v-deep .v-input__slot {
  background: white !important;
  border: 1px solid #d0d0d0 !important;
  border-radius: 2px !important;
}

.filter-section .standard-input ::v-deep .v-input__control {
  background: white !important;
}

.filter-section .standard-input ::v-deep .v-input__prepend-inner {
  background: white !important;
}

.filter-section .standard-input ::v-deep .v-input__prepend-outer {
  background: white !important;
}

.filter-section .standard-input ::v-deep .v-input__append-inner {
  background: white !important;
}

.filter-section .standard-input ::v-deep .v-input__append-outer {
  background: white !important;
}

.filter-section .standard-input ::v-deep .v-text-field__slot {
  background: white !important;
  color: #333 !important;
}

.filter-section .standard-input ::v-deep .v-text-field__slot input {
  background: white !important;
  color: #333 !important;
}

.filter-section .standard-input ::v-deep .v-select__selections {
  background: white !important;
  color: #333 !important;
}

.filter-section .standard-input ::v-deep .v-select__selection--comma {
  color: #333 !important;
}

.filter-section .standard-input ::v-deep .v-label {
  color: rgba(0, 0, 0, 0.6) !important;
}

.filter-section .standard-input ::v-deep .v-label--active {
  color: rgba(0, 0, 0, 0.87) !important;
}

.filter-section .standard-input ::v-deep * {
  background-color: white !important;
}

.filter-section .standard-input ::v-deep .v-input {
  background: white !important;
}

.filter-section .standard-input ::v-deep .v-input__icon {
  background: transparent !important;
}

.filter-section .standard-input ::v-deep .v-input__icon--prepend-inner {
  background: transparent !important;
}

.filter-section .standard-input ::v-deep .v-input__icon--prepend-outer {
  background: transparent !important;
}

.filter-section .standard-input ::v-deep .v-input__icon--append-inner {
  background: transparent !important;
}

.filter-section .standard-input ::v-deep .v-input__icon--append-outer {
  background: transparent !important;
}

.filter-section .standard-input ::v-deep .v-input__icon i {
  color: rgba(0, 0, 0, 0.54) !important;
}

.filter-section .standard-input ::v-deep .v-select__selection--placeholder {
  color: #333 !important;
}

.filter-section .standard-input ::v-deep .v-input__slot input::placeholder {
  color: rgba(0, 0, 0, 0.38) !important;
}

.filter-section .standard-input ::v-deep .v-text-field__slot input::placeholder {
  color: rgba(0, 0, 0, 0.38) !important;
}

.filter-section .standard-input ::v-deep .v-select__selection {
  color: #333 !important;
}

.filter-section .standard-input ::v-deep .v-select__selection--comma {
  color: #333 !important;
}

.standard-input ::v-deep .v-input__control {
  min-height: 32px;
  background: white !important;
}

.standard-input ::v-deep .v-text-field__details {
  display: none;
}

.standard-input ::v-deep .v-text-field__slot {
  margin-bottom: 0 !important;
  padding: 0 0px !important;
}

.standard-input ::v-deep .v-input__slot {
  margin-bottom: 0 !important;
  border: 1px solid #d0d0d0 !important;
  border-radius: 2px !important;
  background: white !important;
}

.standard-input ::v-deep .v-text-field__slot input {
  text-align: center !important;
  font-size: 14px !important;
  color: #333 !important;
  background: white !important;
}

.standard-input ::v-deep .v-text-field {
  background: white !important;
}

.standard-input ::v-deep .v-text-field__slot {
  background: white !important;
}

.standard-input ::v-deep .v-input__slot {
  background: white !important;
}

.standard-input ::v-deep .v-input__control {
  background: white !important;
}

.standard-input ::v-deep .v-text-field__slot input {
  background-color: white !important;
  background-image: none !important;
}

.standard-input ::v-deep .v-input__control {
  min-height: 32px !important;
  background: white !important;
}

.standard-input ::v-deep .v-text-field__slot {
  background: white !important;
  margin: 0 !important;
  padding: 0 !important;
}

.standard-input ::v-deep .v-input__slot {
  background: white !important;
  margin: 0 !important;
  padding: 0 !important;
}

.standard-input ::v-deep .v-text-field {
  background: white !important;
  margin: 0 !important;
  padding: 0 !important;
}

.standard-input ::v-deep .v-input {
  background: white !important;
  margin: 0 !important;
  padding: 0 !important;
}

.standard-input ::v-deep .v-text-field__slot input {
  background-color: white !important;
  background-image: none !important;
  margin: 0 !important;
  padding: 0 8px !important;
}

/* 입력 필드와 단위 기호 스타일 */
.input-with-unit {
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 5px !important;
  width: 100% !important;
}

.unit-symbol {
  color: #666 !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  white-space: nowrap !important;
  margin-left: 2px !important;
}



.standard-input ::v-deep .v-text-field__details {
  display: none !important;
}

.footer-copyright {
  background-color: transparent;
  color: #757575;
  font-size: 12px;
  padding: 15px 0;
  border-top: 1px solid #e0e0e0;
}

/* Data table styles */
::v-deep .v-data-table {
  .v-data-table__wrapper {
    border: 1px solid #d0d0d0 !important;
    border-radius: 0 !important;
    overflow: hidden;
  }
  
  th {
    background: #f5f5f5 !important;
    font-weight: 600 !important;
    color: #000000 !important;
    padding: 12px 16px !important;
    border-bottom: 1px solid #d0d0d0 !important;
    border-right: 1px solid #d0d0d0 !important;
    font-size: 14px !important;
  }
  
  th:last-child {
    border-right: none !important;
  }
  
  td {
    padding: 8px 16px !important;
    border-bottom: 1px solid #d0d0d0 !important;
    border-right: 1px solid #d0d0d0 !important;
    vertical-align: middle !important;
    background: white !important;
    color: #000000 !important;
    text-align: center !important;
  }
  
  td .standard-input {
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    width: 100% !important;
    margin: 0 auto !important;
  }
  
  td .standard-input ::v-deep .v-text-field {
    margin: 0 auto !important;
    display: flex !important;
    justify-content: center !important;
  }
  
  td .standard-input ::v-deep .v-input {
    margin: 0 auto !important;
    display: flex !important;
    justify-content: center !important;
  }
  
  td .standard-input ::v-deep .v-input__slot {
    margin: 0 auto !important;
    display: flex !important;
    justify-content: center !important;
  }
  
  td:last-child {
    border-right: none !important;
  }
  
  tr:hover {
    background-color: #f9f9f9 !important;
  }
  
  .v-data-table-header {
    color: #3f3f3f !important;
    
  }
  
  .v-data-table-header th {
    color: #000000 !important;
    text-align: center !important;
  }
}

/* Input form styles */
.input-form-section {
  background: #fafafa;
  padding: 24px;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
}

.form-title {
  color: #1976d2;
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 16px;
}

.form-actions {
  display: flex;
  justify-content: flex-start;
  align-items: center;
}
.blue-back-bar {
  display: flex;
  background: linear-gradient(135deg, #1976d2 0%, #1565c0 100%);
  min-height: 80px;
  width: 100vw;
  margin-left: calc(-50vw + 50%);
  margin-right: calc(-50vw + 50%);
  margin-top: 0;
  margin-bottom: 0;
  box-shadow: 0 4px 12px rgba(0, 124, 248, 0.3);
  position: relative;
  z-index: 1;
}
.content-window{
  margin-top: -100px;
}

.content-header {
  background-color: rgb(198, 247, 247);
  min-height: 60px;
  margin: 0;
}
.content-body{
  padding: 0 30px;
}
.content-bottom-line{
  border-bottom: 4px solid #333;
  margin: 0 30px;
}

.change-btn {
  min-width: 60px !important;
  height: 28px !important;
  font-size: 12px !important;
  text-transform: none !important;
  border-radius: 3px !important;
  border-color: #FF8C00 !important;
  color: #FF8C00 !important;
}

.change-btn ::v-deep .v-btn__content {
  font-weight: 500;
  color: #FF8C00 !important;
}

.change-btn:hover {
  background-color: #FF8C00 !important;
  color: white !important;
}

.change-btn:hover ::v-deep .v-btn__content {
  color: white !important;
}

/* 시나리오 선택 및 저장 버튼 스타일 */
.scenario-control-section {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 30px;
  padding: 20px;
  background: white;
  border-radius: 8px;
  border: 1px solid #e9ecef;
  
}

.scenario-selection {
  flex: 1;
  
}

.scenario-label {
  display: block;
  font-weight: 600;
  font-size: 16px;
  color: #000000;
  margin-bottom: 15px;
}

.scenario-radio-group {
  margin-bottom: 15px;
}

.scenario-radio {
  margin-right: 20px;
  
}

.scenario-description {
  margin-top: 10px;
  font-size: 14px;
  color: #666;
  
}

.save-button-section {
  margin-left: 20px;

}

.save-btn {
  min-width: 80px;
  height: 40px;
  font-weight: 500;
  background-color: #e7e7e7 !important;
  color: rgb(0, 0, 0) !important ;
}

/* 커스텀 탭 스타일 */
.custom-tab-group {
  display: flex;
  background: white;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #e0e0e0;
  margin-bottom: 15px;
}

.custom-tab {
  flex: 1;
  padding: 12px 20px;
  text-align: center;
  cursor: pointer;
  font-weight: 500;
  font-size: 14px;
  color: #000000;
  background: white;
  transition: all 0.3s ease;
  position: relative;
  border-right: 1px solid #e0e0e0;
}

.custom-tab:last-child {
  border-right: none;
}

.custom-tab:hover {
  background: #f5f5f5;
}

.custom-tab.active {
  background: #c4c3c3;
  color: white;
}

.custom-tab.active::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: #424242;
  z-index: -1;
}

/* ROI 테이블 스타일 */
.add-button-section {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 20px;
}

.add-btn {
  min-width: 120px;
  height: 40px;
  font-weight: 500;
  margin-top: 10px;
  background-color: #ffffff !important;
  color: rgb(49, 49, 49) !important;
}

.delete-btn {
  min-width: 60px !important;
  height: 28px !important;
  font-size: 12px !important;
  text-transform: none !important;
  border-radius: 3px !important;
  border-color: #FF9800 !important;
  color: #FF9800 !important;
}

.delete-btn ::v-deep .v-btn__content {
  font-weight: 500;
  color: #FF9800 !important;
}

.delete-btn:hover {
  background-color: #FF9800 !important;
  color: white !important;
}

.delete-btn:hover ::v-deep .v-btn__content {
  color: white !important;
}

.edit-btn {
  min-width: 60px !important;
  height: 28px !important;
  font-size: 12px !important;
  text-transform: none !important;
  border-radius: 3px !important;
  border-color: #1976d2 !important;
  color: #1976d2 !important;
  margin-right: 8px !important;
}

.edit-btn ::v-deep .v-btn__content {
  font-weight: 500;
  color: #1976d2 !important;
}

.edit-btn:hover {
  background-color: #1976d2 !important;
  color: white !important;
}

.edit-btn:hover ::v-deep .v-btn__content {
  color: white !important;
}

.roi-table-row {
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.roi-table-row:hover {
  background-color: #f5f5f5 !important;
}

/* 간단한 삭제 다이얼로그 스타일 */
.simple-delete-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.simple-delete-dialog {
  background: white;
  padding: 20px;
  border-radius: 8px;
  max-width: 400px;
  width: 90%;
}

.simple-delete-dialog h3 {
  margin: 0 0 15px 0;
  color: #333;
}

.simple-delete-dialog p {
  margin: 8px 0;
  color: #666;
}

.simple-delete-dialog .warning {
  color: #ffffff;
  font-weight: bold;
  margin: 15px 0;
}

.simple-delete-dialog .buttons {
  text-align: right;
  margin-top: 20px;
}

.simple-delete-dialog button {
  padding: 8px 16px;
  margin-left: 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  cursor: pointer;
}

.simple-delete-dialog button:first-child {
  background: white;
  color: #666;
}

.simple-delete-dialog button:last-child {
  background: #d32f2f;
  color: white;
  border-color: #d32f2f;
}

.simple-delete-dialog button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* ROI 추가 다이얼로그 스타일 */
.video-container {
  position: relative;
  width: 100%;
  height: 300px; /* 영상 컨테이너 높이 */
  border: 1px solid #d0d0d0;
  border-radius: 4px;
  overflow: hidden;
  background-color: #000; /* 영상 컨테이너 배경 */
  display: flex;
  justify-content: center;
  align-items: center;
  cursor: crosshair; /* 마우스 커서 변경 */
}

.video-placeholder {
  text-align: center;
  color: #888;
  font-size: 18px;
}

.selection-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none; /* 영상 영역 위에 표시 */
}

.selection-box {
  position: absolute;
  border: 2px dashed #FF8C00;
  box-shadow: 0 0 10px rgba(255, 140, 0, 0.5);
  z-index: 1000;
}

.coordinate-display {
  position: absolute;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 5px 10px;
  border-radius: 4px;
  font-size: 12px;
  z-index: 1000;
}

/* 페이지네이션 스타일 */
.pagination-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
  margin-top: 20px;
}

.pagination-info {
  text-align: center;
  margin-bottom: 10px;
}

.pagination-text {
  color: #333;
  font-size: 14px;
  font-weight: 500;
  background-color: #f8f9fa;
  padding: 8px 16px;
  border-radius: 6px;
  border: 1px solid #e9ecef;
  display: inline-block;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 15px;
  flex-wrap: wrap;
  justify-content: center;
}

.pagination-btn {
  min-width: 36px !important;
  height: 36px !important;
  padding: 0 !important;
  font-size: 14px !important;
  color: #333 !important;
  border: 1px solid #d0d0d0 !important;
  border-radius: 4px !important;
  background-color: #ffffff !important;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.pagination-btn:hover:not(:disabled) {
  background-color: #f5f5f5 !important;
  color: #1976d2 !important;
  border-color: #1976d2 !important;
  box-shadow: 0 2px 6px rgba(25, 118, 210, 0.2);
}

.pagination-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  color: #ccc !important;
  background-color: #f9f9f9 !important;
}

.page-numbers {
  display: flex;
  align-items: center;
  gap: 4px;
}

.page-btn {
  min-width: 36px !important;
  height: 36px !important;
  padding: 0 8px !important;
  font-size: 14px !important;
  font-weight: 500;
  color: #333 !important;
  border: 1px solid #d0d0d0 !important;
  border-radius: 4px !important;
  background-color: #ffffff !important;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.page-btn:hover:not(:disabled) {
  background-color: #f5f5f5 !important;
  color: #1976d2 !important;
  border-color: #1976d2 !important;
  box-shadow: 0 2px 6px rgba(25, 118, 210, 0.2);
}

.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  color: #ccc !important;
  background-color: #f9f9f9 !important;
}

.active-page {
  background-color: #1976d2 !important;
  color: white !important;
  border-color: #1976d2 !important;
  box-shadow: 0 2px 6px rgba(25, 118, 210, 0.3);
  font-weight: 600;
}

.active-page:hover {
  background-color: #1565c0 !important;
  border-color: #1565c0 !important;
  color: white !important;
}

.ellipsis {
  color: #666;
  font-size: 14px;
  padding: 0 5px;
}

.pagination-jump {
  display: flex;
  align-items: center;
  gap: 10px;
}

.jump-text {
  color: #666;
  font-size: 14px;
  white-space: nowrap;
}

.jump-input {
  width: 80px;
  max-width: 80px;
}

.jump-input ::v-deep .v-text-field__slot {
  min-height: 32px;
}

.jump-input ::v-deep .v-input__slot {
  min-height: 32px;
}

/* 툴팁 스타일 */
.roi-tooltip {
  position: fixed;
  background: #2a3042;
  border: 1px solid #555;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  padding: 12px;
  min-width: 200px;
  z-index: 1000;
  animation: fadeIn 0.2s ease-in-out;
}

.tooltip-content {
  color: white;
}

.tooltip-title {
  font-size: 14px;
  font-weight: bold;
  margin-bottom: 8px;
  color: #ff6b6b;
  border-bottom: 1px solid #555;
  padding-bottom: 4px;
}

.tooltip-body {
  font-size: 12px;
}

.tooltip-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
  padding: 2px 0;
}

.tooltip-item:last-child {
  margin-bottom: 0;
}

.tooltip-label {
  color: #ccc;
  font-weight: 500;
  margin-right: 8px;
}

.tooltip-value {
  color: #fff;
  font-weight: bold;
}

.location-cell {
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.location-cell:hover {
  background-color: rgba(25, 118, 210, 0.1);
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-5px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 경보알림관리 스타일 */
.notification-settings-section,
.threshold-settings-section {
  margin-bottom: 30px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin-bottom: 15px;
  padding-bottom: 8px;
  border-bottom: 2px solid #e0e0e0;
}

.notification-table,
.threshold-table {
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
}

.notification-table th,
.threshold-table th {
  background-color: #f5f5f5 !important;
  color: #000000 !important;
  font-weight: 600 !important;
  padding: 12px !important;
  text-align: left !important;
  border-bottom: 1px solid #e0e0e0 !important;
  border-right: 1px solid #e0e0e0 !important;
}

.notification-table th:last-child,
.threshold-table th:last-child {
  border-right: none !important;
}

/* Vuetify 스타일을 덮어쓰기 위한 더 강력한 선택자 */
::v-deep .notification-table th,
::v-deep .threshold-table th {
  background-color: #f5f5f5 !important;
  color: #000000 !important;
  font-weight: 600 !important;
  padding: 12px !important;
  text-align: left !important;
  border-bottom: 1px solid #e0e0e0 !important;
}

::v-deep .notification-table thead th,
::v-deep .threshold-table thead th {
  color: #000000 !important;
  font-weight: 600 !important;
}

.notification-type-header {
  width: 70%;
  color: #000000 !important;
}

.notification-toggle-header {
  width: 30%;
  color: #000000 !important;
}

/* 특정 헤더 클래스에 대한 더 강력한 스타일 */
::v-deep .notification-type-header,
::v-deep .notification-toggle-header {
  color: #000000 !important;
  font-weight: 600 !important;
}

/* 토글 스위치 스타일 개선 */
::v-deep .notification-switch {
  margin: 0 auto !important;
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
}

::v-deep .notification-switch .v-input__slot {
  margin: 0 auto !important;
  border: 2px solid #e0e0e0 !important;
  border-radius: 8px !important;
  padding: 8px 12px !important;
  background-color: #f8f9fa !important;
  min-width: 80px !important;
  justify-content: center !important;
}

::v-deep .notification-switch .v-input__control {
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
}

::v-deep .notification-switch .v-input__slot .v-input--selection-controls__input {
  margin: 0 auto !important;
}

/* 테이블 셀 스타일 개선 */
.notification-table td,
.threshold-table td {
  padding: 16px 12px !important;
  border-bottom: 1px solid #e0e0e0 !important;
  border-right: 1px solid #e0e0e0 !important;
  vertical-align: middle !important;
  background-color: #ffffff !important;
}

.notification-table td:last-child,
.threshold-table td:last-child {
  border-right: none !important;
}

/* 테이블 행 호버 효과 */
.notification-table tr:hover,
.threshold-table tr:hover {
  background-color: #f8f9fa !important;
}

/* 테이블 테두리 강화 */
.notification-table,
.threshold-table {
  border: 2px solid #e0e0e0 !important;
  border-radius: 8px !important;
  overflow: hidden !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1) !important;
}

/* 입력 필드 컨테이너 중앙 정렬 */
.threshold-input-container {
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 10px !important;
}

.notification-table td,
.threshold-table td {
  padding: 12px;
  border-bottom: 1px solid #e0e0e0;
  vertical-align: middle;
}

.notification-table tr:last-child td,
.threshold-table tr:last-child td {
  border-bottom: none;
}

.phone-input-section {
  margin-top: 20px;
  padding: 20px;
  background-color: #f9f9f9;
  border-radius: 4px;
}

.phone-label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-bottom: 10px;
}

.phone-input {
  max-width: 400px;
}

.threshold-input-container {
  display: flex;
  align-items: center;
  gap: 10px;
}

.threshold-input {
  max-width: 100px;
}

.threshold-unit {
  color: #666;
  font-size: 14px;
  white-space: nowrap;
}

.save-button-section {
  display: flex;
  justify-content: flex-end;
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #e0e0e0;
}

.save-button {
  min-width: 120px;
  height: 40px;
  font-weight: 600;
}

.save-button-top {
  position: absolute;
  top: 20px;
  right: 30px;
  min-width: 100px;
  height: 36px;
  font-weight: 600;
}

.content-header {
  position: relative;
}

/* phone-input-header 스타일 */
.phone-input-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  margin-bottom: 15px;
}

.phone-label {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

/* 문자 직접 입력 다이얼로그 스타일 */
.message-dialog-title {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-bottom: 1px solid #e0e0e0;
  font-weight: bold;
}

.close-btn {
  color: white !important;
}

.message-dialog-content {
  padding: 20px;
  background-color: white;
  overflow-x: hidden !important;
  max-width: 100% !important;
  box-sizing: border-box !important;
}

.message-dialog-content .container {
  max-width: 100% !important;
  overflow-x: hidden !important;
}

.input-row {
  margin-bottom: 0;
  padding: 0;
  max-width: 100% !important;
  overflow-x: hidden !important;
}

::v-deep .message-dialog .v-input {
  max-width: 100% !important;
  overflow-x: hidden !important;
}

::v-deep .message-dialog .row {
  max-width: 100% !important;
  overflow-x: hidden !important;
}

::v-deep .message-dialog .col {
  max-width: 100% !important;
  overflow-x: hidden !important;
  box-sizing: border-box !important;
}

.custom-input-group {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  margin-bottom: 20px;
  padding: 0;
  width: 100%;
}

.custom-input-group-switch {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 0;
  width: 100%;
}

.custom-label {
  font-size: 14px;
  color: black;
  margin-right: 0;
  margin-bottom: 8px;
  font-weight: 500;
  width: 100%;
}

.custom-input-group-switch .custom-label {
  margin-bottom: 0;
}

.custom-input {
  width: 100%;
  padding: 8px 12px;
  border: 2px solid #e0e0e0;
  border-radius: 4px;
  background-color: white;
  color: black;
  font-size: 14px;
  outline: none;
  transition: border-color 0.3s ease;
  box-sizing: border-box;
  min-height: 36px;
  line-height: 1.5;
}

.custom-input:focus {
  border-color: #1976d2;
  box-shadow: 0 0 0 2px rgba(25, 118, 210, 0.2);
}

.custom-input::placeholder {
  color: #999;
}

.custom-textarea {
  width: 100%;
  padding: 8px 12px;
  border: 2px solid #e0e0e0;
  border-radius: 4px;
  background-color: white;
  color: black;
  font-size: 14px;
  outline: none;
  transition: border-color 0.3s ease;
  box-sizing: border-box;
  resize: vertical;
  font-family: inherit;
}

.custom-textarea:focus {
  border-color: #1976d2;
  box-shadow: 0 0 0 2px rgba(25, 118, 210, 0.2);
}

.custom-textarea::placeholder {
  color: #999;
}

.custom-switch {
  flex-shrink: 0;
}

.instruction-text-red {
  color: red;
  font-size: 12px;
  margin: 5px 0;
}

.message-dialog-actions {
  padding: 0 24px 20px 24px;
  display: flex;
  justify-content: center;
  gap: 10px;
}

.cancel-btn {
  background-color: #9e9e9e;
  color: white;
  min-width: 80px;
  font-weight: 500;
  text-transform: none;
}

.save-btn {
  background-color: #ff9800;
  color: white;
  min-width: 80px;
  font-weight: 500;
  text-transform: none;
}

/* v-card 스타일 */
::v-deep .message-dialog-card {
  background-color: white !important;
  overflow-x: hidden !important;
  margin: 0 !important;
  padding: 0 !important;
}

::v-deep .message-dialog .v-card {
  background-color: white !important;
  overflow-x: hidden !important;
  margin: 0 !important;
  padding: 0 !important;
  box-shadow: none !important;
}

::v-deep .message-dialog .v-card__text {
  background-color: white !important;
  overflow-x: hidden !important;
  padding: 20px !important;
}

::v-deep .message-dialog {
  overflow-x: hidden !important;
}

::v-deep .message-dialog .v-dialog {
  overflow-x: hidden !important;
  overflow-y: hidden !important;
}

/* v-dialog overlay 숨기기 */
::v-deep .message-dialog .v-dialog__container {
  overflow: hidden !important;
}

::v-deep .message-dialog .v-overlay__content {
  overflow: hidden !important;
  max-width: 100% !important;
}

/* v-menu와 overlay 관련 */
::v-deep .v-menu__content {
  max-width: 100% !important;
  overflow-x: hidden !important;
}

::v-deep .v-overlay {
  max-width: 100% !important;
  overflow-x: hidden !important;
}

/* v-overlay__content 너비 제한 */
::v-deep .message-dialog .v-overlay__content {
  max-width: 600px !important;
  width: 600px !important;
  overflow: hidden !important;
  margin: 0 auto !important;
  padding: 0 !important;
}

/* v-dialog 전체 컨테이너 */
::v-deep .v-dialog__container {
  max-width: 100% !important;
  overflow: hidden !important;
}

/* v-overlay 스크린 */
::v-deep .v-overlay__scrim {
  max-width: 100% !important;
  overflow: hidden !important;
}

/* message-dialog 관련 요소들의 overflow 숨기기 */
.message-dialog,
.message-dialog *,
.message-dialog .v-overlay__content,
.message-dialog .v-dialog__container,
.message-dialog .v-overlay__scrim {
  overflow-x: hidden !important;
}

/* v-dialog 관련 요소 */
::v-deep .v-dialog.v-dialog--active,
::v-deep .v-dialog__container {
  overflow-x: hidden !important;
  max-width: 100vw !important;
  margin: 0 !important;
  padding: 0 !important;
}

/* message-dialog의 v-dialog */
::v-deep .message-dialog.v-dialog {
  max-width: 600px !important;
  width: 600px !important;
  margin: 0 auto !important;
  padding: 0 !important;
  overflow: hidden !important;
}

/* v-overlay 관련 */
::v-deep .v-overlay.v-overlay--active {
  overflow-x: hidden !important;
  max-width: 100vw !important;
}

/* v-card 내용 */
::v-deep .message-dialog-card * {
  max-width: 100% !important;
}

/* 제목 영역 패딩 최소화 */
::v-deep .message-dialog .v-card__title {
  padding: 12px 16px !important;
}

/* 액션 버튼 영역 패딩 최소화 */
::v-deep .message-dialog .v-card__actions {
  padding: 8px 16px 12px 16px !important;
}

/* 모든 여백과 패딩 최소화 */
::v-deep .message-dialog-card > * {
  margin: 0 !important;
}

/* 오버레이 여백 최소화 */
::v-deep .message-dialog .v-overlay__content {
  margin: 24px auto !important;
}
</style>
