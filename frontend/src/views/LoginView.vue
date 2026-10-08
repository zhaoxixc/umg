<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'
import { errMsg, login } from '../api'
import { ROLE_NAMES, setAuth } from '../auth'

const emit = defineEmits(['logged-in'])
const formRef = ref()
const loading = ref(false)
const form = reactive({ username: '', password: '' })

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function submit() {
  await formRef.value.validate().catch(() => Promise.reject())
  loading.value = true
  try {
    const { data } = await login(form)
    setAuth(data.access_token, {
      id: data.id, username: data.username,
      display_name: data.display_name, role: data.role,
    })
    ElMessage.success(`欢迎，${ROLE_NAMES[data.role]} ${data.display_name}`)
    emit('logged-in')
  } catch (e) {
    ElMessage.error(errMsg(e))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-wrap">
    <div class="login-card">
      <h1>U位资产管理系统</h1>
      <p class="sub">机房机柜 U 位资产智能化管理</p>
      <el-form ref="formRef" :model="form" :rules="rules" size="large" @keyup.enter="submit">
        <el-form-item prop="username">
          <el-input v-model="form.username" :prefix-icon="User" placeholder="用户名" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            :prefix-icon="Lock"
            placeholder="密码"
            show-password
          />
        </el-form-item>
        <el-button type="primary" class="login-btn" :loading="loading" @click="submit">
          登 录
        </el-button>
      </el-form>
      <p class="tip">默认管理员：admin / admin123，登录后请及时修改密码</p>
    </div>
  </div>
</template>

<style scoped>
.login-wrap {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1f2d3d 0%, #2d5f8b 100%);
}

.login-card {
  width: 400px;
  background: #fff;
  border-radius: 10px;
  padding: 40px 36px 28px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.25);
}

.login-card h1 {
  margin: 0;
  font-size: 22px;
  text-align: center;
  color: #1f2d3d;
}

.login-card .sub {
  text-align: center;
  color: #8a919c;
  font-size: 13px;
  margin: 8px 0 26px;
}

.login-btn {
  width: 100%;
  margin-top: 4px;
}

.tip {
  margin: 16px 0 0;
  font-size: 12px;
  color: #a0a6af;
  text-align: center;
}
</style>
