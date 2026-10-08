<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { errMsg, rackOff } from '../api'
import { hasAny } from '../auth'

const props = defineProps({
  rack: Object, // RackViewOut
  modelValue: Boolean,
})
const emit = defineEmits(['update:modelValue', 'manage', 'changed'])

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const busy = ref(0)

const usedU = computed(() =>
  (props.rack?.assets || []).reduce((s, a) => s + a.u_height, 0)
)

async function off(a) {
  busy.value++
  try {
    await rackOff(a.id)
    ElMessage.success('已下架')
    emit('changed')
  } catch (e) {
    ElMessage.error(errMsg(e))
  } finally {
    busy.value--
  }
}
</script>

<template>
  <el-drawer v-model="visible" :title="`机柜详情：${rack?.name || ''}`" size="720px">
    <template v-if="rack">
      <el-descriptions :column="4" border size="small" style="margin-bottom: 14px">
        <el-descriptions-item label="数据中心">{{ rack.datacenter_name }}</el-descriptions-item>
        <el-descriptions-item label="机房">{{ rack.room_name }}</el-descriptions-item>
        <el-descriptions-item label="机柜列">{{ rack.group_name }}</el-descriptions-item>
        <el-descriptions-item label="规格">{{ rack.u_count }}U</el-descriptions-item>
        <el-descriptions-item label="在架资产">{{ rack.assets.length }} 台</el-descriptions-item>
        <el-descriptions-item label="已用U位">{{ usedU }}U</el-descriptions-item>
        <el-descriptions-item label="空闲U位">{{ rack.u_count - usedU }}U</el-descriptions-item>
        <el-descriptions-item label="利用率">
          {{ rack.u_count ? ((usedU / rack.u_count) * 100).toFixed(2) : 0 }}%
        </el-descriptions-item>
      </el-descriptions>
      <el-table :data="rack.assets" size="small" border v-loading="busy > 0">
        <el-table-column prop="code" label="资产编号" width="130" />
        <el-table-column prop="name" label="资产名称" min-width="150" show-overflow-tooltip />
        <el-table-column prop="asset_type" label="类型" width="80" />
        <el-table-column prop="brand" label="品牌" width="70" />
        <el-table-column prop="model" label="型号" width="130" show-overflow-tooltip />
        <el-table-column label="U位" width="80">
          <template #default="{ row }">{{ row.u_start }}U-{{ row.u_start + row.u_height - 1 }}U</template>
        </el-table-column>
        <el-table-column v-if="hasAny('admin', 'operator')" label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small"
              @click="emit('manage', row, 'edit')">编辑</el-button>
            <el-button link type="primary" size="small"
              @click="emit('manage', row, 'place')">移位</el-button>
            <el-button link type="warning" size="small" @click="off(row)">下架</el-button>
          </template>
        </el-table-column>
      </el-table>
    </template>
  </el-drawer>
</template>
