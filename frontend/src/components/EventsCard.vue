<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { getRackEvents } from '../api'

const props = defineProps({ rackId: Number })
const emit = defineEmits(['changed'])

const tab = ref('realtime')
const realtime = ref([])
const history = ref([])
const total_loaded = ref(0)
let timer = null

const dotColor = { rack_on: '#5ad8a6', rack_off: '#f0a030', move: '#409eff' }

async function loadRealtime() {
  if (!props.rackId) return
  const { data } = await getRackEvents(props.rackId, 'realtime')
  realtime.value = data
}

async function loadHistory() {
  if (!props.rackId) return
  const { data } = await getRackEvents(props.rackId, 'history', {
    offset: total_loaded.value,
    limit: 50,
  })
  history.value = total_loaded.value ? history.value.concat(data) : data
  total_loaded.value = history.value.length
}

function fmt(ts) {
  return String(ts).replace('T', ' ').slice(0, 19)
}

function switchTab(name) {
  if (name === 'history') loadHistory()
}

watch(
  () => props.rackId,
  () => {
    history.value = []
    total_loaded.value = 0
    loadRealtime()
    if (tab.value === 'history') loadHistory()
  }
)

function refresh() {
  loadRealtime()
}

onMounted(() => {
  loadRealtime()
  timer = setInterval(loadRealtime, 15000)
})

onBeforeUnmount(() => clearInterval(timer))

defineExpose({ refresh })
</script>

<template>
  <div class="panel stat-card" style="flex: 1; display: flex; flex-direction: column">
    <el-tabs v-model="tab" @tab-change="switchTab">
      <el-tab-pane label="实时事件" name="realtime">
        <el-empty v-if="!realtime.length" description="暂无事件" :image-size="60" />
        <el-timeline v-else class="ev-list">
          <el-timeline-item
            v-for="e in realtime"
            :key="e.id"
            :color="dotColor[e.event_type] || '#909399'"
            :timestamp="fmt(e.created_at)"
            placement="top"
          >
            <div class="ev-msg">{{ e.message }}</div>
          </el-timeline-item>
        </el-timeline>
      </el-tab-pane>
      <el-tab-pane label="历史事件" name="history">
        <el-empty v-if="!history.length" description="暂无事件" :image-size="60" />
        <el-timeline v-else class="ev-list">
          <el-timeline-item
            v-for="e in history"
            :key="e.id"
            :color="dotColor[e.event_type] || '#909399'"
            :timestamp="fmt(e.created_at)"
            placement="top"
          >
            <div class="ev-msg">{{ e.message }}</div>
          </el-timeline-item>
        </el-timeline>
        <div style="text-align: center; padding: 8px 0">
          <el-button size="small" @click="loadHistory">加载更多</el-button>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.ev-list {
  max-height: 190px;
  overflow: auto;
  padding-left: 4px;
}

.ev-msg {
  font-size: 13px;
  color: #333;
  line-height: 1.5;
}
</style>
