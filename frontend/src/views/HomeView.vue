<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { getAllEvents, getHomeStats, getOverview } from '../api'

const ov = ref(null)
const stats = ref(null)
const events = ref([])
const donutRef = ref()
const barRef = ref()
let charts = []

const cards = [
  ['datacenters', '数据中心'],
  ['rooms', '机房'],
  ['racks', '机柜'],
  ['assets_on_rack', '在架资产'],
  ['assets_off_rack', '待上架资产'],
  ['total_u', '总U位'],
  ['used_u', '已用U位'],
]

const TYPE_COLORS = ['#409eff', '#52c41a', '#9254de', '#f5222d', '#fa8c16', '#909399']
const dotColor = { rack_on: '#5ad8a6', rack_off: '#f0a030', move: '#409eff' }

function utilization() {
  return ov.value && ov.value.total_u
    ? ((ov.value.used_u / ov.value.total_u) * 100).toFixed(2)
    : '0.00'
}

function renderCharts() {
  if (!stats.value) return
  const [c1, c2] = charts
  c1.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} 台 ({d}%)' },
    legend: { bottom: 0, icon: 'circle', itemWidth: 8, itemHeight: 8 },
    series: [
      {
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['50%', '44%'],
        label: { show: false },
        itemStyle: { borderRadius: 4 },
        data: stats.value.by_type.map((t, i) => ({
          ...t,
          itemStyle: { color: TYPE_COLORS[i % TYPE_COLORS.length] },
        })),
      },
    ],
  })
  const rooms = stats.value.by_room.slice(0, 8)
  c2.setOption({
    tooltip: {
      trigger: 'item',
      formatter: (p) =>
        `${p.name}<br/>利用率: ${p.value}%<br/>已用 ${rooms[p.dataIndex].used_u}U / ${rooms[p.dataIndex].total_u}U · 资产 ${rooms[p.dataIndex].asset_count} 台`,
    },
    grid: { left: 10, right: 50, top: 10, bottom: 10, containLabel: true },
    xAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' }, splitLine: { show: false } },
    yAxis: {
      type: 'category',
      inverse: true,
      data: rooms.map((r) => r.room),
      axisLabel: {
        width: 110,
        overflow: 'truncate',
        formatter: (v) => `{v|${v}}`,
        rich: { v: { color: '#555', fontSize: 12 } },
      },
    },
    series: [
      {
        type: 'bar',
        barWidth: 14,
        itemStyle: { borderRadius: 7, color: '#409eff' },
        label: { show: true, position: 'right', formatter: '{c}%', color: '#8a919c' },
        data: rooms.map((r) => r.utilization),
      },
    ],
  })
}

function fmt(ts) {
  return ts ? String(ts).replace('T', ' ').slice(0, 19) : ''
}

function resize() {
  charts.forEach((c) => c.resize())
}

onMounted(async () => {
  charts = [echarts.init(donutRef.value), echarts.init(barRef.value)]
  window.addEventListener('resize', resize)
  try {
    const [o, h, e] = await Promise.all([
      getOverview(),
      getHomeStats(),
      getAllEvents('realtime'),
    ])
    ov.value = o.data
    stats.value = h.data
    events.value = e.data
    renderCharts()
  } catch { /* 由拦截器处理 */ }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  charts.forEach((c) => c.dispose())
})
</script>

<template>
  <div class="home">
    <div class="home-head">
      <h2>资源总览</h2>
      <el-tag v-if="ov" type="primary" effect="plain">
        整体空间利用率 {{ utilization() }}%
      </el-tag>
    </div>

    <div v-if="ov" class="home-cards">
      <div v-for="[key, label] in cards" :key="key" class="home-card">
        <div class="num">{{ ov[key] }}</div>
        <div class="lbl">{{ label }}</div>
      </div>
    </div>
    <el-skeleton v-else :rows="3" animated style="margin-top: 10px" />

    <div class="home-charts">
      <div class="panel chart-card">
        <h3>资产类型分布 <span class="sub">在架资产</span></h3>
        <div ref="donutRef" class="chart" />
      </div>
      <div class="panel chart-card">
        <h3>机房空间利用率 <span class="sub">按机房汇总（TOP 8）</span></h3>
        <div ref="barRef" class="chart" />
      </div>
    </div>

    <div class="panel chart-card">
      <h3>最近动态 <span class="sub">全局上下架事件</span></h3>
      <el-empty v-if="!events.length" description="暂无事件" :image-size="60" />
      <el-timeline v-else class="home-events">
        <el-timeline-item
          v-for="e in events"
          :key="e.id"
          :color="dotColor[e.event_type] || '#909399'"
          :timestamp="fmt(e.created_at)"
        >
          <span class="ev-msg">{{ e.message }}</span>
        </el-timeline-item>
      </el-timeline>
    </div>
  </div>
</template>

<style scoped>
.home {
  padding: 16px 20px;
  overflow: auto;
  height: 100%;
  box-sizing: border-box;
}

.home-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 0;
}

.home-head h2 {
  margin: 0 0 6px;
}

.home-cards {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 12px;
  margin-bottom: 14px;
}

.home-card {
  padding: 14px;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.home-card .num {
  font-size: 26px;
  font-weight: 700;
  color: #409eff;
}

.home-card .lbl {
  color: #8a919c;
  font-size: 12px;
  margin-top: 4px;
}

.home-charts {
  display: grid;
  grid-template-columns: 1fr 1.4fr;
  gap: 12px;
  margin-bottom: 12px;
}

.chart-card {
  padding: 14px 18px;
}

.chart-card h3 {
  margin: 0 0 4px;
  font-size: 15px;
  color: #333;
}

.chart-card .sub {
  font-size: 12px;
  color: #a0a6af;
  font-weight: 400;
  margin-left: 6px;
}

.chart {
  width: 100%;
  height: 240px;
}

.home-events {
  max-height: 280px;
  overflow: auto;
  padding-left: 4px;
}

.ev-msg {
  font-size: 13px;
  color: #333;
}
</style>
