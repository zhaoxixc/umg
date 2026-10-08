<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { InfoFilled } from '@element-plus/icons-vue'
import { errMsg, getRackView, rackOff } from '../api'
import { hasAny } from '../auth'

const ROW = 30
const props = defineProps({ rackId: Number, rackName: String })
const emit = defineEmits(['manage', 'show-detail', 'changed', 'select-asset'])

const view = ref(null)
const selectedId = ref(null)
const hover = ref(null)
let leaveTimer = null

const occupiedSet = computed(() => {
  const s = new Set()
  for (const a of view.value?.assets || []) {
    for (let u = a.u_start; u < a.u_start + a.u_height; u++) s.add(u)
  }
  return s
})

const uList = computed(() => {
  const n = view.value?.u_count || 0
  return Array.from({ length: n }, (_, i) => n - i)
})

function deviceStyle(a) {
  const top = (view.value.u_count - (a.u_start + a.u_height - 1)) * ROW
  return { top: `${top}px`, height: `${a.u_height * ROW}px`, zIndex: a.u_height }
}

const TYPE_CLASS = {
  服务器: 't-server',
  交换机: 't-switch',
  路由器: 't-router',
  防火墙: 't-firewall',
  存储: 't-storage',
}

function typeClass(t) {
  return TYPE_CLASS[t] || 't-other'
}

function statusText(s) {
  return s === 'on_rack' ? '在架' : '在架下'
}

function posText(a) {
  const end = a.u_start + a.u_height - 1
  return `${a.u_start}U-${end}U`
}

function onEnter(a, e) {
  clearTimeout(leaveTimer)
  const x = Math.min(e.clientX + 14, window.innerWidth - 400)
  const y = Math.min(e.clientY + 10, window.innerHeight - 420)
  hover.value = { asset: a, x: Math.max(8, x), y: Math.max(8, y) }
}

function onLeave() {
  clearTimeout(leaveTimer)
  leaveTimer = setTimeout(() => (hover.value = null), 200)
}

function onPopEnter() {
  clearTimeout(leaveTimer)
}

function onSelect(a) {
  if (selectedId.value === a.id) {
    selectedId.value = null
    emit('select-asset', null)
  } else {
    selectedId.value = a.id
    emit('select-asset', a)
  }
}

async function load() {
  if (!props.rackId) return
  hover.value = null
  selectedId.value = null
  emit('select-asset', null)
  try {
    const { data } = await getRackView(props.rackId)
    view.value = data
  } catch {
    view.value = null
  }
}

async function offRack(a) {
  try {
    await rackOff(a.id)
    hover.value = null
    await load()
    emit('changed')
  } catch (e) {
    ElMessage.error(errMsg(e))
  }
}

watch(() => props.rackId, load)
defineExpose({ reload: load })
</script>

<template>
  <div class="panel center-panel">
    <div class="rack-head">
      <el-icon :size="18" color="#409eff"><InfoFilled /></el-icon>
      <span class="name">{{ view?.name || rackName || '请选择机柜' }}</span>
      <el-tag v-if="view" size="small" type="info">{{ view.u_count }}U</el-tag>
      <div style="flex: 1" />
      <slot name="toolbar" />
      <el-button
        v-if="view"
        size="small"
        round
        @click="emit('show-detail', view)"
      >
        机柜详情
      </el-button>
    </div>
    <div class="rack-scroll">
      <div v-if="view" class="rack-body">
        <div class="rack-slots" :style="{ height: view.u_count * ROW + 'px' }">
          <div
            v-for="a in view.assets"
            :key="a.id"
            class="device"
            :class="[typeClass(a.asset_type), { selected: selectedId === a.id }]"
            :style="deviceStyle(a)"
            @click="onSelect(a)"
            @mouseenter="onEnter(a, $event)"
            @mouseleave="onLeave"
          >
            <div class="face" />
            <span class="label">{{ a.name }}</span>
          </div>
        </div>
        <div class="u-num-col">
          <div
            v-for="u in uList"
            :key="u"
            class="u-num"
            :class="{ occupied: occupiedSet.has(u) }"
          >
            <span>{{ u }}</span>
          </div>
        </div>
      </div>
      <el-empty v-else description="请在左侧选择机柜" />
    </div>

    <!-- 资产悬浮信息 -->
    <teleport to="body">
      <div
        v-if="hover"
        class="asset-pop"
        :style="{ left: hover.x + 'px', top: hover.y + 'px' }"
        @mouseenter="onPopEnter"
        @mouseleave="onLeave"
      >
        <table>
          <tbody>
            <tr><td class="k">资产编号:</td><td class="v">{{ hover.asset.code }}</td></tr>
            <tr><td class="k">资产序列号:</td><td class="v">{{ hover.asset.serial || '-' }}</td></tr>
            <tr><td class="k">资产名称:</td><td class="v">{{ hover.asset.name }}</td></tr>
            <tr><td class="k">资产状态:</td><td class="v">{{ statusText(hover.asset.status) }}</td></tr>
            <tr><td class="k">资产类型:</td><td class="v">{{ hover.asset.asset_type }}</td></tr>
            <tr><td class="k">资产品牌:</td><td class="v">{{ hover.asset.brand || '-' }}</td></tr>
            <tr><td class="k">资产型号:</td><td class="v">{{ hover.asset.model || '-' }}</td></tr>
            <tr><td class="k">资产高度:</td><td class="v">{{ hover.asset.u_height }}U</td></tr>
            <tr><td class="k">资产位置:</td><td class="v">{{ posText(hover.asset) }}</td></tr>
            <tr v-if="hover.asset.ip_address">
              <td class="k">业务IP:</td><td class="v">{{ hover.asset.ip_address }}</td>
            </tr>
            <tr v-if="hover.asset.bmc_address">
              <td class="k">BMC地址:</td><td class="v">{{ hover.asset.bmc_address }}</td>
            </tr>
          </tbody>
        </table>
        <div v-if="hasAny('admin', 'operator')" class="ops">
          <el-button size="small" @click="emit('manage', hover.asset, 'edit')">编辑</el-button>
          <el-button size="small" type="primary" @click="emit('manage', hover.asset, 'place')">
            移位
          </el-button>
          <el-button size="small" type="warning" @click="offRack(hover.asset)">下架</el-button>
        </div>
      </div>
    </teleport>
  </div>
</template>
