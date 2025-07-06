<template>
  <div class="video-management">
    <v-container fluid>
      <v-row>
        <v-col cols="12">
          <v-card>
            <v-card-title>영상 관리</v-card-title>
            <v-card-text>
              <v-list>
                <v-list-item to="/video-management/surveillance-areas">
                  <v-list-item-icon>
                    <v-icon>mdi-cctv</v-icon>
                  </v-list-item-icon>
                  <v-list-item-content>
                    <v-list-item-title>감시구역 설정</v-list-item-title>
                  </v-list-item-content>
                </v-list-item>
              </v-list>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script>
export default {
  name: 'VideoManagement',
  data() {
    return {
      // 컴포넌트 데이터
    };
  },
  methods: {
    // 컴포넌트 메서드
  }
};
</script>

<style scoped>
.video-management {
  padding: 20px;
}
</style>
