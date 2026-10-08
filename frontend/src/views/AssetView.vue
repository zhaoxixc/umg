<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import AssetDialog from '../components/AssetDialog.vue'
import AssetHistoryDialog from '../components/AssetHistoryDialog.vue'
import EventsCard from '../components/EventsCard.vue'
import LocationTree from '../components/LocationTree.vue'
import RackDetailDrawer from '../components/RackDetailDrawer.vue'
import RackPanel from '../components/RackPanel.vue'
import SelectedAssetCard from '../components/SelectedAssetCard.vue'
import StatsPanel from '../components/StatsPanel.vue'
import { hasAny } from '../auth'
import { errMsg, rackOff } from '../api'

const treeRef = ref()
const rackRef = ref()
const statsRef = ref()
const eventsRef = ref()

const current = ref(null) // { id, name }
const selectedAsset = ref(null)
const histVisible = ref(false)
const histAsset = ref(null)
const dialogVisible = ref(false)
const dialogMode = ref('create')
const dialogAsset = ref(null)
const drawerVisible = ref(false)
const drawerRack = ref(null)

function selectRack(node) {
  current.value = node
  selectedAsset.value = null
}

function onSelectAsset(a) {
  selectedAsset.value = a
}

async function offSelected(a) {
  try {
    await rackOff(a.id)
    ElMessage.success('已下架')
    refreshAll()
  } catch (e) {
    ElMessage.error(errMsg(e))
  }
}

function showHistory(a) {
  histAsset.value = a
  histVisible.value = true
}

function refreshAll() {
  rackRef.value?.reload()
  statsRef.value?.reload()
  eventsRef.value?.refresh()
  treeRef.value?.reload()
}

function openCreate() {
  if (!current.value) {
    dialogMode.value = 'create'
    dialogAsset.value = null
    dialogVisible.value = true
    return
  }
  dialogMode.value = 'create'
  dialogAsset.value = null
  dialogVisible.value = true
}

function openManage(asset, mode) {
  dialogMode.value = mode
  dialogAsset.value = asset
  dialogVisible.value = true
}

function openDrawer(rackView) {
  drawerRack.value = rackView
  drawerVisible.value = true
}
</script>

<template>
  <div class="asset-view">
    <LocationTree ref="treeRef" @select-rack="selectRack" @changed="refreshAll" />

    <RackPanel
      ref="rackRef"
      :rack-id="current?.id"
      :rack-name="current?.name"
      @manage="openManage"
      @show-detail="openDrawer"
      @changed="refreshAll"
      @select-asset="onSelectAsset"
    >
      <template #toolbar>
        <el-button v-if="hasAny('admin', 'operator')" type="primary" size="small"
          @click="openCreate">新增资产</el-button>
      </template>
    </RackPanel>

    <div class="right-area">
      <SelectedAssetCard
        :asset="selectedAsset"
        :rack-name="current?.name"
        @close="selectedAsset = null"
        @manage="openManage"
        @off="offSelected"
        @history="showHistory"
      />
      <StatsPanel ref="statsRef" :rack-id="current?.id" />
      <EventsCard ref="eventsRef" :rack-id="current?.id" />
    </div>

    <AssetHistoryDialog v-model="histVisible" :asset="histAsset" />

    <AssetDialog
      v-model="dialogVisible"
      :mode="dialogMode"
      :asset="dialogAsset"
      :default-rack-id="current?.id"
      @saved="refreshAll"
    />

    <RackDetailDrawer
      v-model="drawerVisible"
      :rack="drawerRack"
      @manage="openManage"
      @changed="refreshAll"
    />
  </div>
</template>
