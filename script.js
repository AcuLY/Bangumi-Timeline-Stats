// ==UserScript==
// @name         Bangumi-Timeline-Stats
// @description  统计时间线的 24 小时分布数据
// @version      1.1
// @author       AcuL
// ==/UserScript==

if (window.location.pathname.match(/^\/user\/[^\/]+$/)) {
	// Chart.js
	const script = document.createElement('script')
	script.src = 'https://cdn.jsdelivr.net/npm/chart.js'
	document.head.appendChild(script)

	// style
	const pathname = location.pathname
	const userId = pathname.split('/').pop()
	const height = 258

	// Container
	const container = document.createElement('div')
	container.className = 'SidePanel'
	container.style.position = 'relative'
	const pinnedLayout = document.getElementById('pinnedLayout')
	pinnedLayout.parentNode.insertBefore(container, pinnedLayout)

	// chart
	const chartContainer = document.createElement('div')
    chartContainer.style.position = 'relative'
	chartContainer.style.height = `${height}px`
	container.appendChild(chartContainer)

	// canvas
	const canvas = document.createElement('canvas')
	canvas.id = 'anime-routine'
	canvas.style.borderRadius = '8px'
	canvas.style.marginBottom = '8px'
	chartContainer.appendChild(canvas)

	// select
	const selector = document.createElement('select')
	selector.id = 'selector'
	selector.style.borderRadius = '6px'
	selector.style.padding = '2px'
	selector.style.color = 'rgba(54, 162, 235)'
	selector.style.borderColor = 'rgba(54, 162, 235, 0.2)'
	const options = [
		{ value: '7d', text: '最近一周' },
		{ value: '1m', text: '最近一个月' },
		{ value: '3m', text: '最近三个月' },
		{ value: '6m', text: '最近半年' },
		{ value: '1y', text: '最近一年' },
		{ value: '1', text: '最近 20 次' },
		{ value: '3', text: '最近 60 次' },
		{ value: '5', text: '最近 100 次' },
		{ value: '10', text: '最近 200 次' },
	]

	options.forEach((o) => {
		const el = document.createElement('option')
		el.value = o.value
		el.text = o.text
		selector.appendChild(el)
	})

	selector.addEventListener('input', () => {
		fetchDataAndCreateChart()
	})
	container.appendChild(selector)

	// loading
	// 外层遮罩
	const loaderWrapper = document.createElement('div')
	Object.assign(loaderWrapper.style, {
		position: 'absolute',
		top: 0,
		left: 0,
        inset: '0', 
		backgroundColor: 'rgba(120, 120, 120, 0.26)',
		zIndex: 10,
		display: 'flex',
		alignItems: 'center',
		justifyContent: 'center',
	})

	// 内层旋转圈
	const spinner = document.createElement('div')
	Object.assign(spinner.style, {
		position: 'relative',
		width: '50px',
		height: '50px',
		left: `calc(50% - 15px)`,
		top: `${height / 2 - 25}px`,
		border: '3px solid #f3f3f3',
		borderTopColor: '#FF6384',
		borderRadius: '50%',
		animation: 'spin 1s linear infinite',
		boxSizing: 'border-box',
	})

	const style = document.createElement('style')
	style.textContent = `
@keyframes spin {
from { transform: rotate(0deg); }
to { transform: rotate(360deg); }
}
`

	loaderWrapper.appendChild(spinner)
	document.head.appendChild(style)
	chartContainer.appendChild(loaderWrapper)

    // title
	const title = document.createElement('h2')
	title.textContent = `${userId} ${selector.options[selector.selectedIndex].text}的点格子作息`
	container.insertBefore(title, chartContainer)

	// fetch failed
	const failed = document.createElement('div')
	failed.textContent = '查询失败，可能是服务器暂时关闭了'
	failed.style.position = 'absolute'
	failed.style.width = `100%`
	failed.style.height = `${height}px`
	failed.style.top = '40px'
	failed.style.textAlign = 'center'
	failed.style.lineHeight = `${height}px`
	failed.style.fontWeight = 'bold'
	failed.style.fontSize = '14px'
	failed.style.display = 'none'
	chartContainer.appendChild(failed)

	// create chart
	let chart = null
	function createChart(hours) {
		if (chart) {
			chart.destroy()
		}

		const ctx = document.getElementById('anime-routine').getContext('2d')
		const gradient = ctx.createLinearGradient(0, 0, canvas.width, 0)
		gradient.addColorStop(0, 'rgba(255, 99, 132, 0.7)')
		gradient.addColorStop(1, 'rgba(54, 162, 235, 0.7)')

		chart = new Chart(ctx, {
			type: 'bar',
			data: {
				labels: [
					'0 点',
					'1 点',
					'2 点',
					'3 点',
					'4 点',
					'5 点',
					'6 点',
					'7 点',
					'8 点',
					'9 点',
					'10 点',
					'11 点',
					'12 点',
					'13 点',
					'14 点',
					'15 点',
					'16 点',
					'17 点',
					'18 点',
					'19 点',
					'20 点',
					'21 点',
					'22 点',
					'23 点',
				],
				datasets: [
					{
						label: `点格子数（共${hours.reduce((sum, value) => sum + value, 0)}次）`,
						data: hours,
						backgroundColor: gradient,
					},
				],
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				scales: {
					x: {
						ticks: {
							callback: function (value, index, ticks) {
								const label = this.getLabelForValue(value)
								return label === '0 点' ||
									label === '6 点' ||
									label === '12 点' ||
									label === '18 点'
									? label
									: ''
							},
							autoSkip: false,
							maxRotation: 0,
							align: 'center',
						},
						grid: {
							color: function (context) {
								const index = context.index
								if (index === 3 || index === 9 || index === 15 || index === 21) {
									return 'rgba(0, 0, 0, 0.05)'
								}
								if (index === 0 || index === 6 || index === 12 || index === 18) {
									return 'rgba(0, 0, 0, 0.1)'
								}
								return 'transparent'
							},
							drawTicks: true,
						},
					},
				},
			},
		})
	}

	// fetch
	async function fetchDataAndCreateChart() {
		showLoader()
		title.textContent = `${userId} ${selector.options[selector.selectedIndex].text}的点格子作息`

		const url = `https://search.bgmss.fun/timeline?userid=${userId}&range=${
			selector.options[selector.selectedIndex].value
		}`

		if (sessionStorage.getItem(url)) {
			const hours = JSON.parse(sessionStorage.getItem(url))
			createChart(hours)
			hideLoader()
			return
		}

		for (let retry = 0; retry < 3; retry++) {
			try {
				const resp = await fetch(url)
				const result = await resp.json()

				sessionStorage.setItem(url, JSON.stringify(result.hours))
				createChart(result.hours)
			} catch (e) {
				console.log('点格子作息表：' + e.message)

				if (retry < 2) {
					continue
				}

				if (chart) {
					chart.destroy()
				}

				failed.style.display = 'block'
			}
		}

		hideLoader()
	}

	script.onload = fetchDataAndCreateChart

	function showLoader() {
		loaderWrapper.style.display = 'block'
		selector.disabled = true
	}

	function hideLoader() {
		loaderWrapper.style.display = 'none'
		selector.disabled = false
		failed.style.display = 'none'
	}
}
