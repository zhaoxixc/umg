<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { createUser, deleteUser, errMsg, listUsers, updateUser } from '../api'
import { ROLE_NAMES } from '../auth'

const props = defineProps({ modelValue: Boolean })
const emit = defineEmits(['update:modelValue'])

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const users = ref([])
const loading = ref(false)
const meId = Number(JSON.parse(localStorage.getItem('user') || '{}')?.id)

const dlg = reactive({ visible: false, form: { username: '', password: '', display_name: '', role: 'viewer' } })
const dlgRef = ref()
const saving = ref(false)

const dlgRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少 6 位', trigger: 'blur' },
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
}

async function load() {
  loading.value = true
  try {
    const { data } = await listUsers()
    users.value = data
  } catch (e) {
    ElMessage.error(errMsg(e))
  } finally {
    loading.value = false
  }
}

watch(visible, (v) => v && load())

async function save() {
  await dlgRef.value.validate().catch(() => Promise.reject())
  saving.value = true
  try {
    await createUser(dlg.form)
    ElMessage.success('用户已创建')
    dlg.visible = false
    Object.assign(dlg.form, { username: '', password: '', display_name: '', role: 'viewer' })
    load()
  } catch (e) {
    ElMessage.error(errMsg(e))
  } finally {
    saving.value = false
  }
}

async function changeRole(u, role) {
  try {
    await updateUser(u.id, { role })
    ElMessage.success(`已将 ${u.username} 设为${ROLE_NAMES[role]}`)
  } catch (e) {
    ElMessage.error(errMsg(e))
    load()
  }
}

async function toggleActive(u) {
  try {
    await updateUser(u.id, { is_active: u.is_active })
    ElMessage.success(u.is_active ? '已启用' : '已禁用')
  } catch (e) {
    ElMessage.error(errMsg(e))
    load()
  }
}

async function resetPwd(u) {
  try {
    const { value } = await ElMessageBox.prompt(
      `为用户「${u.username}」设置新密码（至少 6 位）`, '重置密码',
      { inputPattern: /^.{6,}$/, inputErrorMessage: '密码长度至少 6 位', type: 'warning' }
    )
    await updateUser(u.id, { password: value })
    ElMessage.success('密码已重置')
  } catch (e) {
    if (e !== 'cancel' && e?.message !== 'cancel') {
      if (e?.response) ElMessage.error(errMsg(e))
    }
  }
}

async function remove(u) {
  try {
    await ElMessageBox.confirm(`确定删除用户「${u.username}」吗？`, '删除确认', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteUser(u.id)
    ElMessage.success('已删除')
    load()
  } catch (e) {
    ElMessage.error(errMsg(e))
  }
}

function fmt(ts) {
  return ts ? String(ts).replace('T', ' ').slice(0, 19) : '-'
}
</script>

<template>
  <el-dialog v-model="visible" title="用户管理" width="760px" destroy-on-close>
    <div style="margin-bottom: 10px; display: flex; gap: 8px">
      <el-button type="primary" size="small" :icon="Plus" @click="dlg.visible = true">
        新增用户
      </el-button>
      <el-button size="small" :icon="Refresh" @click="load" />
    </div>
    <el-table :data="users" size="small" border v-loading="loading">
      <el-table-column prop="username" label="用户名" width="110" />
      <el-table-column prop="display_name" label="姓名" width="110" />
      <el-table-column label="角色" width="150">
        <template #default="{ row }">
          <el-select
            :model-value="row.role"
            size="small"
            :disabled="row.id === meId"
            @change="(v) => changeRole(row, v)"
          >
            <el-option label="管理员" value="admin" />
            <el-option label="运维" value="operator" />
            <el-option label="只读" value="viewer" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-switch
            v-model="row.is_active"
            :disabled="row.id === meId"
            @change="() => toggleActive(row)"
          />
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="160">
        <template #default="{ row }">{{ fmt(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="最后登录" width="160">
        <template #default="{ row }">{{ fmt(row.last_login_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="130" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="resetPwd(row)">重置密码</el-button>
          <el-button link type="danger" size="small" :disabled="row.id === meId"
            @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dlg.visible" title="新增用户" width="420px" append-to-body destroy-on-close>
      <el-form ref="dlgRef" :model="dlg.form" :rules="dlgRules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="dlg.form.username" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="dlg.form.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="dlg.form.display_name" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-radio-group v-model="dlg.form.role">
            <el-radio-button value="admin">管理员</el-radio-button>
            <el-radio-button value="operator">运维</el-radio-button>
            <el-radio-button value="viewer">只读</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dlg.visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">确定</el-button>
      </template>
    </el-dialog>
  </el-dialog>
</template>
