<template lang="pug">
.user-list

  v-card
    .search-bar.tw-p-4
      .tw-flex.tw-items-center.tw-justify-between
        .search-field-container.tw-flex-1.tw-mr-4
          v-text-field(
            v-model="search"
            prepend-inner-icon="mdi-magnify"
            placeholder="검색어를 입력하세요"
            hide-details
            dense
            class="search-field"
            @input="handleSearch"
            filled
            background-color="var(--cui-bg-card)"
          )
        v-btn(
          color="white"
          @click="showAddUserDialog"
          outlined
        )
          v-icon(left size="20") {{ icons['mdiPlus'] }}
          span 사용자 추가
    
    v-data-table(
      :headers="headers"
      :items="filteredUsers"
      :items-per-page="10"
      :loading="loading"
      loading-text="데이터를 불러오는 중..."
      no-data-text="데이터가 없습니다"
      class="elevation-1"
    )
      template(v-slot:item.role="{ item }")
        v-chip(
          :color="getRoleColor(item.role)"
          small
          label
          text-color="white"
        ) {{ item.role }}
      
      template(v-slot:item.actions="{ item }")
        .tw-flex.tw-items-center.tw-gap-2.tw-justify-center
          v-btn.edit-btn(
            color="white"
            @click.stop="editUser(item)"
            outlined
          )
            v-icon(left size="20") {{ icons['mdiPencil'] }}
            span 수정
          v-btn.delete-btn(
            color="primary"
            @click.stop="deleteUser(item)"
            outlined
          )
            v-icon(left size="20") {{ icons['mdiDelete'] }}
            span 삭제

    // 사용자 추가/수정 다이얼로그
    v-dialog(
      v-model="dialog"
      max-width="500px"
    )
      v-card
        v-card-title
          span.headline {{ dialogTitle }}
        v-card-text
          v-form(
            ref="form"
            v-model="valid"
          )
            v-text-field(
              v-model="editedItem.userId"
              label="아이디"
              :rules="[v => !!v || '아이디는 필수입니다']"
              required
            )
            v-text-field(
              v-model="editedItem.userName"
              label="이름"
              :rules="[v => !!v || '이름은 필수입니다']"
              required
            )
            v-text-field(
              v-model="editedItem.userDept"
              label="직급"
              :rules="[v => !!v || '직급은 필수입니다']"
              required
            )
            v-text-field(
              v-model="editedItem.password"
              label="비밀번호"
              type="password"
              :rules="[v => (!editedItem.id && !v) ? '비밀번호는 필수입니다' : true]"
              :required="!editedItem.id"
            )
            v-text-field(
              v-model="editedItem.passwordConfirm"
              label="비밀번호 확인"
              type="password"
              :rules="passwordConfirmRules"
              :required="!editedItem.id"
            )
        v-card-actions.dialog-actions
          v-spacer
          v-btn.cancel-btn(
            outlined
            color="white"
            @click="closeDialog"
            :disabled="isProcessing"
          ) 취소
          v-btn.confirm-btn(
            outlined
            color="white"
            :disabled="!valid || isProcessing"
            @click="saveUser"
          )
            v-progress-circular.tw-mr-2(
              v-if="isProcessing"
              indeterminate
              size="20"
              width="2"
              color="white"
            )
            v-icon.tw-mr-2(v-else size="20") {{ editedIndex === -1 ? icons['mdiPlus'] : icons['mdiContentSave'] }}
            span {{ editedIndex === -1 ? '추가하기' : '수정하기' }}

    // 삭제 확인 다이얼로그
    v-dialog(
      v-model="deleteDialog"
      max-width="400px"
    )
      v-card
        v-card-title.headline 삭제 확인
        v-card-text
          p.text-white 정말로 이 사용자를 삭제하시겠습니까?
        v-card-actions
          v-spacer
          v-btn(
            color="white"
            text
            @click="deleteDialog = false"
          ) 취소
          v-btn(
            color="primary"
            text
            @click="confirmDelete"
          ) 삭제
</template>

<script>
import { mdiDelete, mdiPencil, mdiPlus } from '@mdi/js';
import { getUsers, addUser, changeUser, removeUser } from '@/api/users.api';

export default {
  name: 'UserList',

  data: () => ({
    icons: {
      mdiDelete,
      mdiPencil,
      mdiPlus
    },
    search: '',
    loading: false,
    dialog: false,
    deleteDialog: false,
    valid: false,
    headers: [
      { text: 'No', value: 'id', align: 'center', width: '80px' },
      { text: '아이디', value: 'userId', align: 'center' },
      { text: '이름', value: 'userName', align: 'center' },
      { text: '직급', value: 'userDept', align: 'center' },
      { text: '관리', value: 'actions', sortable: false, align: 'center', width: '400px' }
    ],
    users: [],
    editedIndex: -1,
    editedItem: {
      userId: '',
      userName: '',
      userDept: '',
      password: '',
      passwordConfirm: ''
    },
    defaultItem: {
      userId: 'akj2995',
      userName: '안근진2',
      userDept: '경영기획실실',
      password: 'test1234',
      passwordConfirm: 'test1234'
    },
    isProcessing: false
  }),

  computed: {
    dialogTitle() {
      return this.editedIndex === -1 ? '사용자 추가' : '사용자 수정'
    },
    filteredUsers() {
      return this.users.filter(user => {
        const matchesSearch = !this.search || 
          user.userId.toLowerCase().includes(this.search.toLowerCase()) ||
          user.userName.toLowerCase().includes(this.search.toLowerCase()) ||
          user.userDept.toLowerCase().includes(this.search.toLowerCase());
        
        return matchesSearch;
      });
    },
    passwordConfirmRules() {
      return [
        v => !!v || '비밀번호 확인은 필수입니다',
        v => v === this.editedItem.password || '비밀번호가 일치하지 않습니다'
      ]
    }
  },

  created() {
    this.fetchUsers()
  },

  methods: {
    async fetchUsers() {
      try {
        this.loading = true
        const response = await getUsers()
        this.users = response.data.result.map(user => ({
          id: user.id,
          userId: user.userId,
          userName: user.userName || '-',
          userDept: user.userDept || '-',
          permissionLevel: user.permissionLevel,
          sessionTimer: user.sessionTimer
        }))
      } catch (error) {
        console.error('Error fetching users:', error)
        this.$toast.error('사용자 목록을 불러오는데 실패했습니다.')
      } finally {
        this.loading = false
      }
    },

    handleSearch() {
      // 검색 로직은 computed의 filteredUsers에서 처리
    },

    showAddUserDialog() {
      this.editedIndex = -1
      this.editedItem = Object.assign({}, this.defaultItem)
      this.dialog = true
    },

    editUser(item) {
      this.editedIndex = this.users.indexOf(item)
      this.editedItem = {
        ...item,
        password: '****',
        passwordConfirm: '****'
      }
      this.dialog = true
    },

    closeDialog() {
      this.dialog = false
      this.$nextTick(() => {
        this.editedItem = Object.assign({}, this.defaultItem)
        this.editedIndex = -1
        if (this.$refs.form) {
          this.$refs.form.reset()
        }
      })
    },

    async saveUser() {
      if (!this.$refs.form.validate()) return

      this.isProcessing = true
      try {
        if (this.editedIndex > -1) {
          // 수정
          const payload = {
            userName: this.editedItem.userName,
            userDept: this.editedItem.userDept
          }
          if (this.editedItem.password && this.editedItem.password !== '****') {
            payload.password = this.editedItem.password
          }
          await changeUser(this.editedItem.userId, payload)
          this.$toast.success('사용자가 수정되었습니다.')
        } else {
          // 추가
          await addUser({
            userId: this.editedItem.userId,
            userName: this.editedItem.userName,
            userDept: this.editedItem.userDept,
            password: this.editedItem.password
          })
          this.$toast.success('사용자가 추가되었습니다.')
        }
        this.closeDialog()
        await this.fetchUsers()
      } catch (error) {
        this.$toast.error('사용자 저장에 실패했습니다.')
        console.error(error)
      } finally {
        this.isProcessing = false
      }
    },

    deleteUser(item) {
      this.editedIndex = this.users.indexOf(item)
      this.editedItem = Object.assign({}, item)
      this.deleteDialog = true
    },

    async confirmDelete() {
      try {
        await removeUser(this.editedItem.userId)
        this.deleteDialog = false
        this.$toast.success('사용자가 삭제되었습니다.')
        await this.fetchUsers()
      } catch (error) {
        this.$toast.error('사용자 삭제에 실패했습니다.')
        console.error(error)
      }
    },

    getRoleColor(role) {
      const colors = {
        '관리자': 'error',
        '매니저': 'warning',
        '일반사용자': 'success'
      }
      return colors[role] || 'grey'
    }
  }
}
</script>

<style lang="scss" scoped>
.user-list {
  .v-card {
    background-color: var(--cui-bg-dark);
    border-radius: 8px;
  }

  .search-bar {
    background-color: var(--cui-bg-darker);
    border-bottom: 1px solid var(--cui-border-color);
    border-radius: 8px 8px 0 0;
  }

  .search-field-container {
    max-width: 400px;
  }

  .search-field {
    ::v-deep {
      .v-input__slot {
        background-color: var(--cui-bg-card) !important;
        border-radius: 4px !important;
        min-height: 40px !important;

        &:before,
        &:after {
          display: none;
        }

        .v-input__prepend-inner {
          margin-top: 8px;
          margin-right: 8px;
          
          .v-icon {
            color: var(--cui-text-muted);
            font-size: 20px;
          }
        }

        input {
          color: var(--cui-text);
          font-size: 14px;

          &::placeholder {
            color: var(--cui-text-muted);
          }
        }
      }
    }
  }

  .action-btn {
    width: 24px !important;
    height: 24px !important;
    margin: 0 2px !important;
    background-color: var(--cui-bg-card) !important;
    border: 1px solid var(--cui-border-color) !important;
    
    &:hover {
      opacity: 0.8;
      background-color: var(--cui-bg-hover) !important;
    }
    
    &:first-child {
      .v-icon {
        color: var(--cui-primary) !important;
      }
      
      &:hover {
        border-color: var(--cui-primary) !important;
      }
    }
    
    &:last-child {
      .v-icon {
        color: var(--cui-danger) !important;
      }
      
      &:hover {
        border-color: var(--cui-danger) !important;
      }
    }
    
    .v-icon {
      font-size: 16px !important;
    }
  }

  .v-data-table {
    background: transparent;
    
    ::v-deep {
      .v-data-table__wrapper {
        border-radius: 0 0 8px 8px;
      }
      
      th {
        font-weight: bold !important;
        background-color: var(--cui-bg-darker) !important;
        color: var(--cui-text) !important;
        font-size: 14px !important;
        white-space: nowrap;
      }
      
      td {
        padding: 8px 16px !important;
        color: var(--cui-text) !important;
        font-size: 14px !important;
        height: 48px !important;
        vertical-align: middle;
      }

      .v-chip {
        font-weight: 500;
      }

      tbody {
        tr {
          &:hover {
            background-color: var(--cui-bg-hover) !important;
          }
        }
      }
    }
  }
}

.text-white {
  color: #fff !important;
}
</style> 
