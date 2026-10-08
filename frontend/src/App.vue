<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { SwitchButton, UserFilled } from '@element-plus/icons-vue'
import PasswordDialog from './components/PasswordDialog.vue'
import UsersDialog from './components/UsersDialog.vue'
import { clearAuth, getAuth, hasAny, ROLE_NAMES } from './auth'
import HomeView from './views/HomeView.vue'
import AssetView from './views/AssetView.vue'
import AssetListView from './views/AssetListView.vue'
import LoginView from './views/LoginView.vue'

const { token, user } = getAuth()
const logged = ref(!!token.value)

const tab = ref('asset')
const usersVisible = ref(false)
const pwdVisible = ref(false)

function logout() {
  clearAuth()
  logged.value = false
  ElMessage.success('已退出登录')
}
</script>

<template>
  <LoginView v-if="!logged" @logged-in="logged = true" />

  <div v-else class="page">
    <div class="topbar">
      <div class="tab" :class="{ active: tab === 'home' }" @click="tab = 'home'">首页</div>
      <div class="tab" :class="{ active: tab === 'asset' }" @click="tab = 'asset'">
        资产视图
      </div>
      <div class="tab" :class="{ active: tab === 'list' }" @click="tab = 'list'">
        资产管理
      </div>
      <div class="topbar-right">
        <span class="ver">v1.3.1</span>
        <el-dropdown>
          <span class="user-chip">
            <el-icon><UserFilled /></el-icon>
            {{ user.display_name || user.username }}
            <el-tag size="small" :type="user.role === 'admin' ? 'danger' : user.role === 'operator' ? 'primary' : 'info'">
              {{ ROLE_NAMES[user.role] }}
            </el-tag>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-if="hasAny('admin')" @click="usersVisible = true">
                用户管理
              </el-dropdown-item>
              <el-dropdown-item @click="pwdVisible = true">修改密码</el-dropdown-item>
              <el-dropdown-item divided @click="logout">
                <el-icon><SwitchButton /></el-icon> 退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
    <div class="page-body">
      <HomeView v-if="tab === 'home'" />
      <AssetView v-else-if="tab === 'asset'" />
      <AssetListView v-else />
    </div>

    <UsersDialog v-model="usersVisible" />
    <PasswordDialog v-model="pwdVisible" />
  </div>
</template>
