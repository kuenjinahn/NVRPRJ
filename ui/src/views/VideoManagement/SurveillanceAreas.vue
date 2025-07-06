<template>
  <div class="surveillance-areas">
    <v-container fluid>
      <v-row>
        <v-col cols="12">
          <v-card>
            <v-card-title>
              감시구역 설정
            </v-card-title>
            <v-card-text>
              <v-row>
                <v-col cols="12" md="6">
                  <v-card outlined>
                    <v-card-title>감시구역 목록</v-card-title>
                    <v-card-text>
                      <v-list>
                        <v-list-item v-for="(area, index) in surveillanceAreas" :key="index">
                          <v-list-item-content>
                            <v-list-item-title>{{ area.name }}</v-list-item-title>
                            <v-list-item-subtitle>{{ area.description }}</v-list-item-subtitle>
                          </v-list-item-content>
                          <v-list-item-action>
                            <v-btn icon @click="editArea(area)">
                              <v-icon>mdi-pencil</v-icon>
                            </v-btn>
                          </v-list-item-action>
                        </v-list-item>
                      </v-list>
                    </v-card-text>
                    <v-card-actions>
                      <v-btn color="primary" @click="addNewArea">
                        새 감시구역 추가
                      </v-btn>
                    </v-card-actions>
                  </v-card>
                </v-col>
                <v-col cols="12" md="6">
                  <v-card outlined>
                    <v-card-title>감시구역 상세 설정</v-card-title>
                    <v-card-text>
                      <v-form v-if="selectedArea">
                        <v-text-field
                          v-model="selectedArea.name"
                          label="감시구역 이름"
                          required
                        ></v-text-field>
                        <v-textarea
                          v-model="selectedArea.description"
                          label="설명"
                        ></v-textarea>
                        <v-select
                          v-model="selectedArea.camera"
                          :items="cameras"
                          label="연결된 카메라"
                          item-text="name"
                          item-value="id"
                        ></v-select>
                      </v-form>
                      <div v-else class="text-center pa-4">
                        감시구역을 선택하거나 새로 추가해주세요.
                      </div>
                    </v-card-text>
                    <v-card-actions v-if="selectedArea">
                      <v-spacer></v-spacer>
                      <v-btn color="primary" @click="saveArea">
                        저장
                      </v-btn>
                    </v-card-actions>
                  </v-card>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script>
export default {
  name: 'SurveillanceAreas',
  data() {
    return {
      surveillanceAreas: [],
      selectedArea: null,
      cameras: [],
      // 임시 데이터
      tempAreas: [
        { id: 1, name: '입구', description: '건물 입구 감시구역', camera: 1 },
        { id: 2, name: '주차장', description: '주차장 감시구역', camera: 2 }
      ],
      tempCameras: [
        { id: 1, name: '카메라 1' },
        { id: 2, name: '카메라 2' }
      ]
    };
  },
  created() {
    // 실제 API 호출로 대체 필요
    this.surveillanceAreas = this.tempAreas;
    this.cameras = this.tempCameras;
  },
  methods: {
    addNewArea() {
      this.selectedArea = {
        id: null,
        name: '',
        description: '',
        camera: null
      };
    },
    editArea(area) {
      this.selectedArea = { ...area };
    },
    saveArea() {
      if (this.selectedArea.id) {
        // 기존 항목 업데이트
        const index = this.surveillanceAreas.findIndex(a => a.id === this.selectedArea.id);
        if (index !== -1) {
          this.surveillanceAreas[index] = { ...this.selectedArea };
        }
      } else {
        // 새 항목 추가
        this.selectedArea.id = this.surveillanceAreas.length + 1;
        this.surveillanceAreas.push({ ...this.selectedArea });
      }
      this.selectedArea = null;
    }
  }
};
</script>

<style scoped>
.surveillance-areas {
  padding: 20px;
}
</style>
