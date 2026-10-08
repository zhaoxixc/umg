<script setup>
import { computed } from 'vue'
import { Close, Position } from '@element-plus/icons-vue'
import { hasAny } from '../auth'

const props = defineProps({
  asset: Object,
  rackName: String,
})
const emit = defineEmits(['close', 'manage', 'off', 'history'])

const canEdit = computed(() => hasAny('admin', 'operator'))

const posText = computed(() => {
  const a = props.asset
  if (!a?.u_start) return '-'
  return `${a.u_start}U-${a.u_start + a.u_height - 1}U`
})

const fields = computed(() => {
  const a = props.asset || {}
  return [
    ['资产编号', a.code],
    ['资产序列号', a.serial || '-'],
    ['机柜', props.rackName || '-'],
    ['U位', posText.value],
    ['资产类型', a.asset_type],
    ['品牌 / 型号', [a.brand, a.model].filter(Boolean).join(' / ') || '-'],
    ['业务IP', a.ip_address || '-'],
    ['BMC地址', a.bmc_address || '-'],
    ['备注', a.remark || '-'],
  ]
})
</script>

<template>
  <div class="panel selected-card">
    <div class="sc-head">
      <h3>设备信息</h3>
      <el-button v-if="asset" link :icon="Close" @click="emit('close')" />
    </div>
    <el-empty v-if="!asset" :image-size="44" description="点击机柜中的设备，在此查看详情" />
    <div v-else>
      <div class="sc-title-row">
        <span class="sc-title">
          {{ asset.name }}
          <el-tag size="small" type="success">在架</el-tag>
          <el-tag size="small" type="info" effect="plain">{{ asset.u_height }}U</el-tag>
        </span>
      </div>
      <div class="sc-body">
      <div class="sc-fields">
        <div v-for="[k, v] in fields" :key="k" class="sc-field">
          <span class="k">{{ k }}</span>
          <span class="v" :title="String(v)">{{ v }}</span>
        </div>
      </div>
        <div class="sc-ops">
          <el-button size="small" @click="emit('history', asset)">轨迹</el-button>
          <template v-if="canEdit">
            <el-button size="small" type="primary" :icon="Position"
              @click="emit('manage', asset, 'edit')">编辑</el-button>
            <el-button size="small" type="primary" plain
              @click="emit('manage', asset, 'place')">移位</el-button>
            <el-button size="small" type="warning" @click="emit('off', asset)">下架</el-button>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.selected-card {
  padding: 8px 12px;
  flex: none;
}

.sc-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sc-head h3 {
  margin: 0;
  font-size: 14px;
  color: #333;
}

.sc-title-row {
  margin-bottom: 4px;
}

.sc-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.sc-body {
  display: flex;
  gap: 12px;
  margin-top: 6px;
  align-items: flex-start;
}

.sc-fields {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 2px 16px;
}

.sc-field {
  display: flex;
  gap: 6px;
  font-size: 12px;
  line-height: 1.7;
  min-width: 0;
}

.sc-field .k {
  color: #a0a6af;
  flex: none;
}

.sc-field .v {
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sc-ops {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: stretch;
  flex: none;
}

.sc-ops .el-button {
  margin-left: 0;
}
</style>
