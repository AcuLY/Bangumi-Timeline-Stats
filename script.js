// ==UserScript==
// @name         Bangumi-Timeline-Stats
// @description  统计时间线的 24 小时分布数据
// @version      1.0
// @author       AcuL
// @match        *://bgm.tv/user/*
// ==/UserScript==

if (window.location.pathname.match(/^\/user\/[^\/]+$/)) {
    // 动态加载 Chart.js
    const script = document.createElement("script");
    script.src = "https://cdn.jsdelivr.net/npm/chart.js";
    script.onload = () => {
        fetchDataAndInitChart();
    };
    document.head.appendChild(script);

    const pathname = location.pathname;
    const userId = pathname.split('/').pop();

    // 容器
    const container = document.createElement("div");
    container.className = "SidePanel";
    container.style.position = "relative"
    const pinnedLayout = document.getElementById('pinnedLayout');
    pinnedLayout.parentNode.insertBefore(container, pinnedLayout);
    // 创建并插入 canvas 容器
    const canvas = document.createElement("canvas");
    canvas.id = "myChart";
    canvas.style.width = "258px";
    canvas.style.height = "258px";
    canvas.style.borderRadius = '8px';
    container.appendChild(canvas);
    // 时间选择
    const selector = document.createElement("select");
    selector.id = "selector";
    selector.style.borderRadius = '6px';
    selector.style.padding = '2px';
    selector.style.color = 'rgba(54, 162, 235)';
    selector.style.borderColor = 'rgba(54, 162, 235, 0.2)';
    const options = [
        { value: "7d", text: "最近一周" },
        { value: "1m", text: "最近一个月" },
        { value: "3m", text: "最近三个月" },
        { value: "6m", text: "最近半年" },
        { value: "1y", text: "最近一年" },
        { value: "1", text: "最近 20 次" },
        { value: "3", text: "最近 60 次" },
        { value: "5", text: "最近 100 次" },
        { value: "10", text: "最近 200 次" }
    ];
    options.forEach(o => {
        const option = document.createElement("option");
        option.value = o.value;
        option.text = o.text;
        selector.appendChild(option);
    })
    selector.addEventListener('input', () => {
        fetchDataAndInitChart();
    })
    container.appendChild(selector);
    // 加载圈
    const loader = document.createElement('div');
    loader.style.position = "absolute";
    loader.style.width = "258px";
    loader.style.height = "258px";
    loader.style.top = "45px";
    loader.style.zIndex = '10';
    loader.style.backgroundColor = 'rgba(255, 255, 255, 0.7)';
    loader.style.display = 'none';
    loader.innerHTML = `
        <div style="position: relative; top: 94px; left: 94px; width: 50px; height: 50px; border: 3px solid #f3f3f3; border-top: 5px solid #FF6384; border-radius: 50%; animation: spin 1s linear infinite;"></div>
        <style>
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    `;
    container.appendChild(loader);
    // 标题
    const title = document.createElement("h2");
    title.textContent = `${userId} ${selector.options[selector.selectedIndex].text}的动画观看作息`;
    container.insertBefore(title, canvas);
    // 查询失败
    const failed = document.createElement('div');
    failed.textContent = "查询失败，可能是服务器暂时关闭了";
    failed.style.position = "absolute";
    failed.style.width = "258px";
    failed.style.height = "258px";
    failed.style.top = "45px";
    failed.style.textAlign = "center";
    failed.style.lineHeight = "258px";
    failed.style.fontWeight = "bold";
    failed.style.fontSize = "14px";
    failed.style.display = 'none';
    container.appendChild(failed);

    // 调 api
    function fetchDataAndInitChart() {
        showLoader();
        title.textContent = `${userId} ${selector.options[selector.selectedIndex].text}的动画观看作息`;

        const url = `http://127.0.0.1:5000/timeline?userid=${userId}&range=${selector.options[selector.selectedIndex].value}`;

        if (sessionStorage.getItem(url)) {
            const hours = JSON.parse(sessionStorage.getItem(url));
            initChart(hours);
            hideLoader();
            return;
        }

        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                sessionStorage.setItem(url, JSON.stringify(data.hours));
                initChart(data.hours);
                hideLoader();
            })
            .catch(() => {
                if (chart) {
                    chart.destroy();
                }
                hideLoader();
                failed.style.display = "block";
            });
    }

    let chart = null;
    // 初始化图表
    function initChart(hours) {
        if (chart) {
            chart.destroy();
        }

        const ctx = document.getElementById('myChart').getContext('2d');
        const gradient = ctx.createLinearGradient(0, 0, 400, 0);
        gradient.addColorStop(0, 'rgba(255, 99, 132, 0.7)');
        gradient.addColorStop(1, 'rgba(54, 162, 235, 0.7)');

        chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['0 点', '1 点', '2 点', '3 点', '4 点', '5 点', '6 点', '7 点', '8 点', '9 点', '10 点', '11 点', '12 点', '13 点', '14 点', '15 点', '16 点', '17 点', '18 点', '19 点', '20 点', '21 点', '22 点', '23 点'],
                datasets: [{
                    label: `观看集数（共${hours.reduce((sum, value) => sum + value, 0)}集）`,
                    data: hours,
                    backgroundColor: gradient
                }]
            },
            options: {
                scales: {
                    x: {
                        ticks: {
                            callback: function(value, index, ticks) {
                                const label = this.getLabelForValue(value);
                                return label === '0 点' || label === '6 点' || label === '12 点' || label === '18 点' ? label : '';
                            },
                            autoSkip: false,
                            maxRotation: 0,
                            align: 'center'
                        },
                        grid: {
                            color: function(context) {
                                const index = context.index;
                                if (index === 3 || index === 9 || index === 15 || index === 21) {
                                    return 'rgba(0, 0, 0, 0.05)';
                                }
                                if (index === 0 || index === 6 || index === 12 || index === 18) {
                                    return 'rgba(0, 0, 0, 0.1)';
                                }
                                return 'transparent';
                            },
                            drawTicks: true // 保留刻度线
                        }
                    }
                }
            }
        });
    }

    function showLoader() {
        loader.style.display = 'block';
        selector.disabled = true;
    }

    function hideLoader() {
        loader.style.display = 'none';
        selector.disabled = false;
        failed.style.display = "none";
    }
}

