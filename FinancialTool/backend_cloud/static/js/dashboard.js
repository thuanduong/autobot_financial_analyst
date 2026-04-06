// GLOBAL VARIABLES
let candleSeries;
let chart;
let CURRENT_TF = 'M5';
const USERNAME = "User_" + Math.floor(Math.random() * 1000);

// --- INIT ---
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('ui-username').innerText = USERNAME;
    initChart();
    loadHistory();
    setupWebSocket();
    
    // Auto update stats every 2 seconds
    setInterval(updateStats, 2000);
});

// --- 1. CHART SETUP ---
function initChart() {
    const chartOptions = {
        layout: { 
            background: { color: '#121212' }, 
            textColor: '#d1d4dc',
        },
        grid: { 
            vertLines: { color: '#2B2B43' }, 
            horzLines: { color: '#2B2B43' } 
        },
        timeScale: {
            timeVisible: true,
            secondsVisible: false,
            borderColor: '#485c7b',
        },
    };

    const container = document.getElementById('chart-container');
    chart = LightweightCharts.createChart(container, chartOptions);

    candleSeries = chart.addSeries(LightweightCharts.CandlestickSeries, {
        upColor: '#26a69a', downColor: '#ef5350', 
        borderVisible: false, wickUpColor: '#26a69a', wickDownColor: '#ef5350'
    });

    // Auto Resize
    new ResizeObserver(entries => {
        if (entries.length === 0 || entries[0].target !== container) return;
        const newRect = entries[0].contentRect;
        chart.applyOptions({ height: newRect.height, width: newRect.width });
    }).observe(container);

    
}

// --- 2. DATA LOADING ---
async function loadHistory() {
    const sym = document.getElementById('inp-symbol').value;
    const loader = document.getElementById('loading');
    if(loader) loader.style.display = 'block';

    try {
        const res = await fetch(`/api/chart-history?symbol=${sym}&tf=${CURRENT_TF}`);
        const data = await res.json();
        
        if (data.length > 0) {
            candleSeries.setData(data);
            //chart.timeScale().fitContent();
            this.focusOnNewestCandle();
            console.log("load history!");
        }
    } catch (e) {
        console.error("Load History Error:", e);
    } finally {
        if(loader) loader.style.display = 'none';
    }
}

// --- 3. WEBSOCKET ---
function setupWebSocket() {
    const ws = new WebSocket("ws://" + location.host + "/ws");
    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        const sym = document.getElementById('inp-symbol').value;
        
        if (msg.type === 'CANDLE_UPDATE') {
            // 2. Filter: Chỉ xử lý nếu đúng Symbol và Timeframe đang xem
            if (msg.symbol === sym && msg.tf === CURRENT_TF) {
                updateChartSafe(msg.data);
            }
        }
    };
}


function updateChartSafe(serverCandle) {
    // Lấy dữ liệu nến hiện tại đang có trên Chart
    const dataArr = candleSeries.data();
    if (dataArr.length === 0) {
        // Nếu chart trắng, set luôn
        candleSeries.update(serverCandle);
        return;
    }

    const lastClientCandle = dataArr[dataArr.length - 1];
    
    // --- LOGIC SO SÁNH (COMPARE) ---
    
    // Trường hợp 1: Time Server == Time Client -> UPDATE nến đang chạy
    if (serverCandle.time === lastClientCandle.time) {
        candleSeries.update(serverCandle);
    } 
    // Trường hợp 2: Time Server > Time Client -> ADD nến mới (New Candle)
    else if (serverCandle.time > lastClientCandle.time) {
        // Chart tự động nối thêm nến mới
        candleSeries.update(serverCandle);
        //console.log("🕯️ New Candle Created:", new Date(serverCandle.time * 1000).toLocaleTimeString());
    }
    // Trường hợp 3: Time Server < Time Client -> BỎ QUA (Dữ liệu cũ/Latency)
    else {
        // Không làm gì cả để bảo vệ Chart khỏi dữ liệu sai lệch
        // console.warn("Ignored old data packet");
    }
}

// --- 4. INTERACTIONS ---
function selectTF(btn, tf) {
    document.querySelectorAll('.btn-tf').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    CURRENT_TF = tf;
    loadHistory();
}

async function trade(action) {
    const sym = document.getElementById('inp-symbol').value;
    const vol = document.getElementById('inp-vol').value;
    await fetch('/api/paper/trade', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ username: USERNAME, symbol: sym, action: action, volume: vol })
    });
    updateStats();
    alert("✅ Order Sent!");
}

async function closeTrade(ticketId) {
    if(!confirm("Close order #" + ticketId + "?")) return;
    const res = await fetch('/api/paper/close', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ ticket: ticketId })
    });
    const result = await res.json();
    if(result.status === 'success') {
        updateStats();
        alert(`✅ Closed #${ticketId}`);
    } else {
        alert("❌ Error: " + result.msg);
    }
}

async function updateStats() {
    try {
        // User Info
        const resU = await fetch('/api/user-info/' + USERNAME);
        const dataU = await resU.json();
        document.getElementById('ui-balance').innerText = dataU.balance.toFixed(2) + " $";
        renderPositions(dataU.active_orders);

        // Bot Stats
        const resB = await fetch('/api/bot-stats');
        const dataB = await resB.json();
        renderBots(dataB);
    } catch(e) {}
}

function renderPositions(orders) {
    const listDiv = document.getElementById('position-list');
    if (!orders || orders.length === 0) {
        listDiv.innerHTML = '<div style="font-size:12px; color:#666; text-align:center;">No active trades</div>';
        return;
    }
    let html = "";
    orders.forEach(o => {
        let typeColor = o.type === 'BUY' ? '#26a69a' : '#ef5350';
        html += `<div class="pos-item" style="border-left: 3px solid ${typeColor}; background:#333; padding:8px; margin-bottom:5px; border-radius:4px;">
                    <div style="display:flex; justify-content:space-between;">
                        <span style="color:${typeColor}; font-weight:bold">${o.type} ${o.symbol}</span>
                        <button class="btn-close" onclick="closeTrade(${o.ticket})" style="background:#555; color:white; border:none; cursor:pointer;">✕</button>
                    </div>
                    <div style="color:#aaa; font-size:11px;">Vol: ${o.volume} | Open: ${o.open_price}</div>
                 </div>`;
    });
    listDiv.innerHTML = html;
}

function renderBots(bots) {
    // ... (Logic render bot tương tự) ...
    const listDiv = document.getElementById('bot-list');
    let html = "";
    bots.forEach(b => {
        let color = b.profit >= 0 ? '#4caf50' : '#ef5350';
        html += `<div style="display:flex; justify-content:space-between; margin-bottom:4px; font-size:13px;">
                    <span>${b.bot_id}</span>
                    <span style="color:${color}; font-weight:bold">${b.profit.toFixed(2)}$</span>
                 </div>`;
    });
    listDiv.innerHTML = html;
}

function focusOnNewestCandle() {
    if (chart){ 
        chart.timeScale().scrollToRealTime();
    }
}