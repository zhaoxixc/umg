<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  createAsset,
  errMsg,
  getTree,
  rackOff,
  rackOn,
  updateAsset,
} from '../api'

const props = defineProps({
  modelValue: Boolean, // visible
  mode: String, // create / edit / place
  asset: Object,
  defaultRackId: Number,
})
const emit = defineEmits(['update:modelValue', 'saved'])

const formRef = ref()
const saving = ref(false)
const racks = ref([])
const form = ref({})

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const title = computed(
  () => ({ create: '新增资产', edit: '编辑资产', place: '上架 / 移位' }[props.mode] || '')
)

const rules = computed(() => ({
  code: [{ required: true, message: '请输入资产编号', trigger: 'blur' }],
  name: [{ required: true, message: '请输入资产名称', trigger: 'blur' }],
  u_height: [{ required: true, message: '请选择资产高度', trigger: 'change' }],
  // 上架/移位必须选机柜；新增时不选机柜 = 放入待上架库
  rack_id: props.mode === 'place'
    ? [{ required: true, message: '请选择机柜', trigger: 'change' }]
    : [],
  u_start: (props.mode === 'place' || form.value.rack_id)
    ? [{ required: true, message: '请输入起始U位', trigger: 'blur' }]
    : [],
}))

async function loadRacks() {
  const { data } = await getTree()
  const list = []
  for (const dc of data)
    for (const room of dc.children || [])
      for (const g of room.children || [])
        for (const r of g.children || [])
          list.push({ id: r.id, label: `${dc.name} / ${r.name}`, uCount: r.u_count })
  racks.value = list
}

function reset() {
  const a = props.asset || {}
  form.value = {
    id: a.id,
    code: a.code || '',
    name: a.name || '',
    serial: a.serial || '',
    tag_id: a.tag_id || '',
    asset_type: a.asset_type || '服务器',
    brand: a.brand || '',
    model: a.model || '',
    ip_address: a.ip_address || '',
    bmc_address: a.bmc_address || '',
    remark: a.remark || '',
    u_height: a.u_height || 1,
    rack_id: props.mode === 'create' ? props.defaultRackId || null : a.rack_id || null,
    u_start: props.mode === 'place' ? a.u_start : a.u_start || null,
  }
}

watch(visible, (v) => {
  if (v) {
    reset()
    loadRacks()
  }
})

async function save() {
  await formRef.value.validate().catch(() => Promise.reject())
  saving.value = true
  try {
    const f = form.value
    if (props.mode === 'create') {
      await createAsset({
        code: f.code, name: f.name, serial: f.serial, tag_id: f.tag_id,
        asset_type: f.asset_type, brand: f.brand, model: f.model,
        ip_address: f.ip_address, bmc_address: f.bmc_address, remark: f.remark,
        u_height: f.u_height,
        rack_id: f.rack_id, u_start: f.rack_id ? f.u_start : null,
      })
      ElMessage.success('新增成功')
    } else if (props.mode === 'edit') {
      await updateAsset(f.id, {
        name: f.name, serial: f.serial,
        asset_type: f.asset_type, brand: f.brand, model: f.model,
        ip_address: f.ip_address, bmc_address: f.bmc_address, remark: f.remark,
        u_height: f.u_height,
      })
      // 位置变更：换了机柜或U位 -> 上架/移位；清空机柜 -> 下架
      const old = props.asset || {}
      const changed = (f.rack_id || null) !== (old.rack_id || null)
        || (f.rack_id && Number(f.u_start) !== Number(old.u_start))
      if (f.rack_id && f.u_start && changed) {
        await rackOn(f.id, { rack_id: f.rack_id, u_start: f.u_start })
      } else if (!f.rack_id && old.rack_id) {
        await rackOff(f.id)
      }
      ElMessage.success('已保存')
    } else {
      await rackOn(f.id, { rack_id: f.rack_id, u_start: f.u_start })
      ElMessage.success('操作成功')
    }
    visible.value = false
    emit('saved')
  } catch (e) {
    ElMessage.error(errMsg(e))
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <el-dialog v-model="visible" :title="title" width="520px" destroy-on-close>
    <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
      <template v-if="mode !== 'place'">
        <el-form-item label="资产编号" prop="code">
          <el-input v-model="form.code" :disabled="mode === 'edit'" placeholder="如 SM2026050101" />
        </el-form-item>
        <el-form-item label="资产名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="序列号">
          <el-input v-model="form.serial" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="资产类型">
              <el-select v-model="form.asset_type" style="width: 100%">
                <el-option v-for="t in ['服务器', '交换机', '路由器', '存储', '防火墙', '其他']"
                  :key="t" :label="t" :value="t" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="资产高度">
              <el-select v-model="form.u_height" style="width: 100%">
                <el-option v-for="h in 10" :key="h" :label="h + 'U'" :value="h" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="资产品牌">
              <el-input v-model="form.brand" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="资产型号">
              <el-input v-model="form.model" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="业务IP">
              <el-input v-model="form.ip_address" placeholder="服务器IP地址" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="BMC地址">
              <el-input v-model="form.bmc_address" placeholder="远程管理地址" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="255" />
        </el-form-item>
      </template>

      <div>
        <el-form-item :label="mode === 'edit' ? '所在机柜' : '目标机柜'" prop="rack_id">
          <el-select
            v-model="form.rack_id"
            filterable
            clearable
            :placeholder="mode === 'create' ? '不选则放入待上架库' : ''"
            style="width: 100%"
            @change="form.u_start = null"
          >
            <el-option v-for="r in racks" :key="r.id" :value="r.id"
              :label="`${r.label}（${r.uCount}U）`" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.rack_id" label="起始U位" prop="u_start">
          <el-input-number v-model="form.u_start" :min="1" :max="60" style="width: 100%" />
          <div class="tip">自下而上编号，1U 为最底部；资产将占据 {{ form.u_start }}U ~
            {{ (form.u_start || 1) + form.u_height - 1 }}U</div>
        </el-form-item>
      </div>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">确定</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.tip {
  font-size: 12px;
  color: #a0a6af;
  line-height: 1.4;
  width: 100%;
}
</style>
