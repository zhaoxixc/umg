<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { getRackStats } from '../api'

const props = defineProps({ rackId: Number })

const donutRef = ref()
const gaugeRef = ref()
const barRef = ref()
let charts = []

function render(donut, gauge, bar) {
  const [c1, c2, c3] = charts
  c1.setOption({
    tooltip: { trigger: 'item' },
    series: [
      {
        type: 'pie',
        radius: ['34%', '44%'],
        center: ['50%', '50%'],
        label: { show: false },
        silent: true,
        data: [
          { value: donut.used_u, name: '已用U位', itemStyle: { color: '#409eff' } },
          {
            value: donut.free_u,
            name: '空闲U位',
            itemStyle: { color: '#e8ebf0' },
          },
        ],
      },
      {
        type: 'pie',
        radius: ['50%', '66%'],
        center: ['50%', '50%'],
        label: { formatter: '{b} {c}', fontSize: 11 },
        labelLine: { length: 10, length2: 6 },
        data: [
          { value: donut.asset_count, name: '在架资产', itemStyle: { color: '#5ad8a6' } },
          { value: donut.free_u, name: '空闲U位', itemStyle: { color: '#d8dbe0' } },
        ],
      },
    ],
  })
  c2.setOption({
    series: [
      {
        type: 'gauge',
        startAngle: 210,
        endAngle: -30,
        min: 0,
        max: 100,
        radius: '95%',
        progress: { show: true, width: 14, itemStyle: { color: '#409eff' } },
        axisLine: { lineStyle: { width: 14, color: [[1, '#e8ebf0']] } },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        pointer: { show: false },
        anchor: { show: false },
        title: { show: true, offsetCenter: [0, '62%'], fontSize: 13, color: '#8a919c' },
        detail: {
          valueAnimation: true,
          offsetCenter: [0, '10%'],
          formatter: '{value}%',
          fontSize: 34,
          fontWeight: 700,
          color: '#333',
        },
        data: [{ value: gauge.utilization, name: '机柜空间利用率' }],
      },
    ],
  })
  c3.setOption({
    tooltip: {},
    grid: { left: 40, right: 20, top: 30, bottom: 30 },
    xAxis: { type: 'category', data: bar.map((b) => b.name) },
    yAxis: { type: 'value', name: '台', minInterval: 1 },
    series: [
      {
        type: 'bar',
        barWidth: 36,
        label: { show: true, position: 'top' },
        itemStyle: { color: '#409eff' },
        data: bar.map((b) => b.count),
      },
    ],
  })
}

async function load() {
  if (!props.rackId) return
  const { data } = await getRackStats(props.rackId)
  render(data, data, data.by_type)
}

function resize() {
  charts.forEach((c) => c.resize())
}

onMounted(() => {
  charts = [echarts.init(donutRef.value), echarts.init(gaugeRef.value), echarts.init(barRef.value)]
  window.addEventListener('resize', resize)
  load()
})

watch(() => props.rackId, load)

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  charts.forEach((c) => c.dispose())
})

defineExpose({ reload: load })
</script>

<template>
  <div class="stats-grid">
    <div class="panel stat-card">
      <h3>U位&amp;资产统计</h3>
      <div ref="donutRef" class="chart-box" />
    </div>
    <div class="panel stat-card">
      <h3>机柜空间利用率</h3>
      <div ref="gaugeRef" class="chart-box" />
    </div>
    <div class="panel stat-card">
      <h3>资产类型</h3>
      <div ref="barRef" class="chart-box" />
    </div>
  </div>
</template>
