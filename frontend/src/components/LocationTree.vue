<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Cpu, Delete, Edit, Folder, House, OfficeBuilding, Plus, Refresh, Search,
} from '@element-plus/icons-vue'
import {
  createDataCenter, createGroup, createRack, createRoom, deleteLocation,
  errMsg, getTree, updateDataCenter, updateGroup, updateRack, updateRoom,
} from '../api'
import { hasAny } from '../auth'

const emit = defineEmits(['select-rack', 'changed'])
const keyword = ref('')
const treeData = ref([])
const expanded = ref([])

const iconMap = {
  datacenter: OfficeBuilding,
  room: House,
  group: Folder,
  rack: Cpu,
}
const typeNames = { datacenter: '数据中心', room: '机房', group: '机柜列', rack: '机柜' }
const childType = { datacenter: 'room', room: 'group', group: 'rack' }

// ---------- 对话框 ----------
const dlg = ref({
  visible: false,
  mode: 'create', // create / edit
  type: 'datacenter',
  node: null,
  form: { name: '', u_count: 42 },
})
const dlgRef = ref()
const saving = ref(false)

const dlgTitle = computed(() => {
  const t = typeNames[dlg.value.type]
  return dlg.value.mode === 'create'
    ? (dlg.value.node ? `在「${dlg.value.node.name}」下新增${t}` : `新增${t}`)
    : `编辑${t}`
})

const dlgRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  u_count: [{ required: true, message: '请选择机柜规格', trigger: 'change' }],
}

const PRESET_U = [42, 47, 48, 52]

function openCreate(node = null, type = 'datacenter') {
  dlg.value = {
    visible: true, mode: 'create', type, node,
    form: { name: '', u_choice: 42, u_count_custom: 46 },
  }
}

function openEdit(node) {
  dlg.value = {
    visible: true, mode: 'edit', type: node.type, node,
    form: {
      name: node.name,
      u_choice: node.u_count && PRESET_U.includes(node.u_count) ? node.u_count : 'custom',
      u_count_custom: node.u_count && !PRESET_U.includes(node.u_count)
        ? node.u_count : 46,
    },
  }
}

async function saveDlg() {
  await dlgRef.value.validate().catch(() => Promise.reject())
  saving.value = true
  try {
    const { mode, type, node, form } = dlg.value
    if (mode === 'create') {
      if (type === 'datacenter') await createDataCenter({ name: form.name })
      else if (type === 'room') await createRoom({ name: form.name, datacenter_id: node.id })
      else if (type === 'group') await createGroup({ name: form.name, room_id: node.id })
      else
        await createRack({
          name: form.name, group_id: node.id,
          u_count: form.u_choice === 'custom' ? form.u_count_custom : form.u_choice,
        })
      ElMessage.success('新增成功')
    } else {
      if (type === 'datacenter') await updateDataCenter(node.id, { name: form.name })
      else if (type === 'room') await updateRoom(node.id, { name: form.name })
      else if (type === 'group') await updateGroup(node.id, { name: form.name })
      else
        await updateRack(node.id, {
          name: form.name,
          u_count: form.u_choice === 'custom' ? form.u_count_custom : form.u_choice,
        })
      ElMessage.success('已保存')
    }
    dlg.value.visible = false
    await load()
    emit('changed')
  } catch (e) {
    ElMessage.error(errMsg(e))
  } finally {
    saving.value = false
  }
}

async function remove(node) {
  const tips = {
    datacenter: '将同时删除其下机房、机柜列与机柜',
    room: '将同时删除其下机柜列与机柜',
    group: '将同时删除其下机柜',
    rack: '',
  }
  try {
    await ElMessageBox.confirm(
      `确定删除${typeNames[node.type]}「${node.name}」吗？${tips[node.type]}`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  try {
    await deleteLocation(`${node.type}s`, node.id)
    ElMessage.success('已删除')
    await load()
    emit('changed')
  } catch (e) {
    ElMessage.error(errMsg(e))
  }
}

// ---------- 树 ----------
async function load() {
  const { data } = await getTree(keyword.value)
  treeData.value = data
  expanded.value = collectIds(data)
}

function collectIds(nodes, acc = []) {
  for (const n of nodes) {
    acc.push(n.id)
    if (n.children?.length) collectIds(n.children, acc)
  }
  return acc
}

function onClick(data) {
  if (data.type === 'rack') {
    emit('select-rack', { id: data.id, name: data.name })
  }
}

let timer = null
function onSearch() {
  clearTimeout(timer)
  timer = setTimeout(load, 300)
}

onMounted(load)
defineExpose({ reload: load })
</script>

<template>
  <div class="panel tree-panel">
    <div class="search-row">
      <el-input
        v-model="keyword"
        placeholder="请输入名称或编码"
        clearable
        @input="onSearch"
      />
      <el-button type="primary" :icon="Search" @click="load" />
    </div>

    <div class="tree-toolbar">
      <el-button v-if="hasAny('admin')" type="primary" size="small" :icon="Plus"
        @click="openCreate()">
        新增数据中心
      </el-button>
      <el-button size="small" :icon="Refresh" @click="load" />
    </div>

    <div class="tree-scroll">
      <el-tree
        :data="treeData"
        :default-expanded-keys="expanded"
        node-key="id"
        :props="{ label: 'name', children: 'children' }"
        :expand-on-click-node="false"
        highlight-current
        @node-click="onClick"
      >
        <template #default="{ data }">
          <span class="tree-node-label">
            <el-icon><component :is="iconMap[data.type]" /></el-icon>
            <span>{{ data.name }}</span>
            <span v-if="hasAny('admin')" class="node-ops">
              <el-tooltip v-if="childType[data.type]" content="新增下级" placement="top">
                <el-icon @click.stop="openCreate(data, childType[data.type])"><Plus /></el-icon>
              </el-tooltip>
              <el-tooltip content="编辑" placement="top">
                <el-icon @click.stop="openEdit(data)"><Edit /></el-icon>
              </el-tooltip>
              <el-tooltip content="删除" placement="top">
                <el-icon @click.stop="remove(data)"><Delete /></el-icon>
              </el-tooltip>
            </span>
          </span>
        </template>
      </el-tree>
    </div>

    <el-dialog
      v-model="dlg.visible"
      :title="dlgTitle"
      width="440px"
      destroy-on-close
      append-to-body
    >
      <el-form ref="dlgRef" :model="dlg.form" :rules="dlgRules" label-width="90px">
        <el-form-item :label="typeNames[dlg.type] + '名称'" prop="name">
          <el-input v-model="dlg.form.name" :placeholder="dlg.type === 'rack' ? '如 CPJF-S-24P' : ''" />
        </el-form-item>
        <el-form-item v-if="dlg.type === 'rack'" label="机柜规格">
          <el-radio-group v-model="dlg.form.u_choice">
            <el-radio-button v-for="u in PRESET_U" :key="u" :value="u">{{ u }}U</el-radio-button>
            <el-radio-button value="custom">自定义</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="dlg.type === 'rack' && dlg.form.u_choice === 'custom'" label="U 数"
          prop="u_count_custom"
          :rules="[{ required: true, message: '请输入 U 数' }]">
          <el-input-number v-model="dlg.form.u_count_custom" :min="1" :max="60" style="width: 100%" />
          <div class="u-tip">支持 1-60U 任意规格（如 22U、26U、38U 壁挂机柜等）</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dlg.visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveDlg">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>
