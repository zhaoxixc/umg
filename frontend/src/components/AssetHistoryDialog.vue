<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getAssetHistory } from '../api'

const props = defineProps({ modelValue: Boolean, asset: Object })
const emit = defineEmits(['update:modelValue'])

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const events = ref([])
const loading = ref(false)

const dotColor = { rack_on: '#5ad8a6', rack_off: '#f0a030', move: '#409eff' }
const actionName = { rack_on: '上架', rack_off: '下架', move: '移位' }

function fmt(ts) {
  return ts ? String(ts).replace('T', ' ').slice(0, 19) : '-'
}

watch(visible, async (v) => {
  if (!v || !props.asset) return
  loading.value = true
  events.value = []
  try {
    const { data } = await getAssetHistory(props.asset.id)
    events.value = data
  } catch (e) {
    ElMessage.error(String(e))
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <el-dialog
    v-model="visible"
    :title="`资产轨迹：${asset?.code || ''} ${asset?.name || ''}`"
    width="620px"
    destroy-on-close
  >
    <el-empty v-if="!loading && !events.length" description="暂无轨迹记录" :image-size="70" />
    <el-timeline v-else v-loading="loading" style="max-height: 420px; overflow: auto; padding-left: 6px">
      <el-timeline-item
        v-for="e in events"
        :key="e.id"
        :color="dotColor[e.event_type] || '#909399'"
        :timestamp="fmt(e.created_at)"
        placement="top"
      >
        <div style="font-size: 13px; color: #333; line-height: 1.5">
          <el-tag size="small" :type="e.event_type === 'rack_off' ? 'warning' : 'success'">
            {{ actionName[e.event_type] || e.event_type }}
          </el-tag>
          <span style="margin-left: 6px">{{ e.message.split('|').pop() }}</span>
        </div>
        <div style="font-size: 12px; color: #a0a6af; margin-top: 2px">{{ e.message }}</div>
      </el-timeline-item>
    </el-timeline>
  </el-dialog>
</template>
