<script setup>
import { onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Delete, Download, Plus, Refresh, Upload,
} from '@element-plus/icons-vue'
import {
  createBackup, deleteAsset, deleteBackup, downloadBackup,
  downloadImportTemplate, errMsg, exportAssets, importAssets, listAssets,
  listBackups, rackOff, restoreBackup,
} from '../api'
import { hasAny } from '../auth'
import AssetDialog from '../components/AssetDialog.vue'
import AssetHistoryDialog from '../components/AssetHistoryDialog.vue'

const tab = ref('list')
const canEdit = hasAny('admin', 'operator')

// ---------- 资产列表 ----------
const keyword = ref('')
const status = ref('')
const assetType = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const rows = ref([])
const loading = ref(false)

const typeOptions = ['服务器', '交换机', '路由器', '存储', '防火墙', '其他']

async function load() {
  if (tab.value !== 'list') return
  loading.value = true
  try {
    const { data } = await listAssets({
      q: keyword.value,
      status: status.value,
      asset_type: assetType.value,
      limit: pageSize.value,
      offset: (page.value - 1) * pageSize.value,
    })
    rows.value = data.items
    total.value = data.total
  } catch (e) {
    ElMessage.error(errMsg(e))
  } finally {
    loading.value = false
  }
}

let timer = null
function onSearch() {
  clearTimeout(timer)
  timer = setTimeout(() => {
    page.value = 1
    load()
  }, 300)
}

// ---------- 编辑 / 轨迹 ----------
const dlgVisible = ref(false)
const dlgMode = ref('edit')
const dlgAsset = ref(null)
const histVisible = ref(false)
const histAsset = ref(null)

function openEdit(row) {
  dlgMode.value = 'edit'
  dlgAsset.value = row
  dlgVisible.value = true
}

function openPlace(row) {
  dlgMode.value = 'place'
  dlgAsset.value = row
  dlgVisible.value = true
}

function openHistory(row) {
  histAsset.value = row
  histVisible.value = true
}

async function off(row) {
  try {
    await rackOff(row.id)
    ElMessage.success('已下架')
    load()
  } catch (e) {
    ElMessage.error(errMsg(e))
  }
}

async function remove(row) {
  try {
    await deleteAsset(row.id)
    ElMessage.success('已删除')
    load()
  } catch (e) {
    ElMessage.error(errMsg(e))
  }
}

// ---------- 导入 / 导出 ----------
const importResult = ref(null)
const importing = ref(false)

async function doExport() {
  try {
    await exportAssets({ q: keyword.value, status: status.value })
  } catch {
    ElMessage.error('导出失败')
  }
}

async function doTemplate() {
  try {
    await downloadImportTemplate()
  } catch {
    ElMessage.error('模板下载失败')
  }
}

async function onImportFile(file) {
  importing.value = true
  importResult.value = null
  try {
    const { data } = await importAssets(file)
    importResult.value = data
    ElMessage.success(`导入完成：成功 ${data.success} 条，失败 ${data.failed.length} 条`)
    load()
  } catch (e) {
    ElMessage.error(errMsg(e))
  } finally {
    importing.value = false
  }
  return false
}

// ---------- 备份 ----------
const backups = ref([])
const backupLoading = ref(false)
const restoring = ref('')

async function loadBackups() {
  backupLoading.value = true
  try {
    const { data } = await listBackups()
    backups.value = data
  } catch (e) {
    ElMessage.error(errMsg(e))
  } finally {
    backupLoading.value = false
  }
}

async function doBackup() {
  try {
    await createBackup()
    ElMessage.success('备份已创建')
    loadBackups()
  } catch (e) {
    ElMessage.error(errMsg(e))
  }
}

async function doDownload(name) {
  try {
    await downloadBackup(name)
  } catch {
    ElMessage.error('下载失败')
  }
}

async function doRestore(name) {
  try {
    await ElMessageBox.confirm(
      `确定用备份「${name}」覆盖当前数据库吗？恢复后，备份之后所做的数据修改将丢失！`,
      '恢复确认',
      { type: 'warning', confirmButtonText: '确认恢复', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  restoring.value = name
  try {
    const { data } = await restoreBackup(name)
    ElMessage.success(data.message)
  } catch (e) {
    ElMessage.error(errMsg(e))
  } finally {
    restoring.value = ''
  }
}

async function doDeleteBackup(name) {
  try {
    await deleteBackup(name)
    ElMessage.success('已删除')
    loadBackups()
  } catch (e) {
    ElMessage.error(errMsg(e))
  }
}

function fmtSize(n) {
  return n > 1024 * 1024 ? (n / 1024 / 1024).toFixed(1) + ' MB' : (n / 1024).toFixed(1) + ' KB'
}

function fmt(ts) {
  return ts ? String(ts).replace('T', ' ').slice(0, 19) : '-'
}

function posText(row) {
  if (row.status !== 'on_rack' || !row.rack_id) return '-'
  const end = row.u_start + row.u_height - 1
  return `${row.u_start}U-${end}U`
}

onMounted(() => {
  load()
  if (hasAny('admin')) loadBackups()
})

watch(tab, (v) => {
  if (v === 'backups' && hasAny('admin')) loadBackups()
})
</script>

<template>
  <div class="asset-list-page">
    <div class="panel page-card">
      <el-tabs v-model="tab">
        <el-tab-pane label="资产列表" name="list">
          <div class="toolbar">
            <el-input
              v-model="keyword"
              placeholder="编号 / 名称 / 序列号"
              clearable
              style="width: 220px"
              @input="onSearch"
            />
            <el-select
              v-model="status"
              placeholder="状态"
              clearable
              style="width: 130px"
              @change="() => { page = 1; load() }"
            >
              <el-option label="在架" value="on_rack" />
              <el-option label="待上架" value="off_rack" />
            </el-select>
            <el-select
              v-model="assetType"
              placeholder="类型"
              clearable
              style="width: 130px"
              @change="() => { page = 1; load() }"
            >
              <el-option v-for="t in typeOptions" :key="t" :label="t" :value="t" />
            </el-select>
            <div style="flex: 1" />
            <template v-if="canEdit">
              <el-button :icon="Download" @click="doExport">导出 Excel</el-button>
              <el-upload :show-file-list="false" accept=".xlsx" :before-upload="onImportFile">
                <el-button :icon="Upload" :loading="importing">导入 Excel</el-button>
              </el-upload>
              <el-button link type="primary" @click="doTemplate">下载导入模板</el-button>
            </template>
          </div>

          <el-alert
            v-if="importResult"
            :title="`导入完成：成功 ${importResult.success} 条，失败 ${importResult.failed.length} 条`"
            :type="importResult.failed.length ? 'warning' : 'success'"
            show-icon
            closable
            style="margin-bottom: 10px"
            @close="importResult = null"
          >
            <div v-if="importResult.failed.length" class="imp-errors">
              <div v-for="f in importResult.failed" :key="f.row">
                第 {{ f.row }} 行：{{ f.error }}
              </div>
            </div>
          </el-alert>

          <el-table :data="rows" size="small" border v-loading="loading">
            <el-table-column prop="code" label="资产编号" width="130" />
            <el-table-column prop="name" label="资产名称" min-width="150" show-overflow-tooltip />
            <el-table-column prop="asset_type" label="类型" width="80" />
            <el-table-column prop="brand" label="品牌" width="80" />
            <el-table-column prop="model" label="型号" width="130" show-overflow-tooltip />
            <el-table-column label="业务IP" width="120" show-overflow-tooltip>
              <template #default="{ row }">{{ row.ip_address || '-' }}</template>
            </el-table-column>
            <el-table-column label="BMC地址" width="120" show-overflow-tooltip>
              <template #default="{ row }">{{ row.bmc_address || '-' }}</template>
            </el-table-column>
            <el-table-column prop="u_height" label="高度" width="60">
              <template #default="{ row }">{{ row.u_height }}U</template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="row.status === 'on_rack' ? 'success' : 'info'">
                  {{ row.status === 'on_rack' ? '在架' : '待上架' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="U位" width="90">
              <template #default="{ row }">{{ posText(row) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="230" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="openHistory(row)">轨迹</el-button>
                <template v-if="canEdit">
                  <el-button v-if="row.status === 'off_rack'" link type="success" size="small"
                    @click="openPlace(row)">上架</el-button>
                  <el-button v-else link type="warning" size="small" @click="off(row)">下架</el-button>
                  <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
                  <el-button link type="danger" size="small" :disabled="row.status === 'on_rack'"
                    @click="remove(row)">删除</el-button>
                </template>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination
            v-model:current-page="page"
            v-model:page-size="pageSize"
            :total="total"
            layout="total, prev, pager, next, sizes"
            :page-sizes="[20, 50, 100]"
            style="margin-top: 12px; justify-content: flex-end"
            @current-change="load"
            @size-change="() => { page = 1; load() }"
          />
        </el-tab-pane>

        <el-tab-pane v-if="hasAny('admin')" label="备份与恢复" name="backups">
          <div class="toolbar">
            <el-alert
              type="info"
              :closable="false"
              style="flex: 1"
              title="备份文件保存在服务器 backups 目录（docker 卷挂载到宿主机 ./backups）。恢复会用备份覆盖当前数据库，请谨慎操作。"
            />
            <el-button type="primary" :icon="Plus" @click="doBackup">立即备份</el-button>
            <el-button :icon="Refresh" @click="loadBackups" />
          </div>
          <el-table :data="backups" size="small" border v-loading="backupLoading">
            <el-table-column prop="name" label="备份文件" min-width="220" />
            <el-table-column label="大小" width="100">
              <template #default="{ row }">{{ fmtSize(row.size) }}</template>
            </el-table-column>
            <el-table-column label="创建时间" width="170">
              <template #default="{ row }">{{ fmt(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="220" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="doDownload(row.name)">下载</el-button>
                <el-button link type="warning" size="small" :loading="restoring === row.name"
                  @click="doRestore(row.name)">恢复</el-button>
                <el-button link type="danger" size="small"
                  @click="doDeleteBackup(row.name)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>

    <AssetDialog v-model="dlgVisible" :mode="dlgMode" :asset="dlgAsset" @saved="load" />
    <AssetHistoryDialog v-model="histVisible" :asset="histAsset" />
  </div>
</template>

<style scoped>
.asset-list-page {
  height: 100%;
  padding: 12px;
  box-sizing: border-box;
  overflow: auto;
}

.page-card {
  padding: 6px 16px 16px;
  min-height: 100%;
}

.toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
  margin: 10px 0;
}

.imp-errors {
  font-size: 12px;
  color: #b88230;
  max-height: 120px;
  overflow: auto;
}
</style>
