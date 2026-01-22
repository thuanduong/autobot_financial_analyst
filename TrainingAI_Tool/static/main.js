// static/main.js

// --- 1. KHỞI TẠO BIỂU ĐỒ ---
const chartContainer = document.getElementById('chart-box');
const chart = LightweightCharts.createChart(chartContainer, {
    layout: { background: { color: '#161b22' }, textColor: '#c9d1d9' },
    grid: { vertLines: { color: '#21262d' }, horzLines: { color: '#21262d' } },
    timeScale: { timeVisible: true, secondsVisible: false },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
});

let candleSeries = chart.addCandlestickSeries({
    upColor: '#2ea043', downColor: '#f85149',
    borderDownColor: '#f85149', borderUpColor: '#2ea043',
    wickDownColor: '#f85149', wickUpColor: '#2ea043',
});

// Resize Observer
new ResizeObserver(entries => {
    if (entries.length === 0 || entries[0].target !== chartContainer) return;
    const newRect = entries[0].contentRect;
    chart.applyOptions({ width: newRect.width, height: newRect.height });
}).observe(chartContainer);

// --- 2. QUẢN LÝ USER & WEBSOCKET ---
let ws = null;
let currentUser = localStorage.getItem("trader_user") || "";

// A. Logic Đăng nhập
async function doLogin() {
    const u = document.getElementById("inp-user").value;
    const p = document.getElementById("inp-pass").value;
    if(!u) return alert("Vui lòng nhập Username!");

    try {
        const res = await fetch("/api/login", {
            method: "POST", headers: {"Content-Type":"application/json"},
            body: JSON.stringify({username: u, password: p})
        });
        const data = await res.json();
        
        if(data.status === "success") {
            currentUser = u;
            localStorage.setItem("trader_user", u);
            document.getElementById("login-overlay").style.display = "none";
            connectWebSocket(); // <--- CHỈ KẾT NỐI KHI ĐÃ LOGIN THÀNH CÔNG
        } else {
            alert("Lỗi: " + data.msg);
        }
    } catch (err) {
        console.error(err);
        alert("Không thể kết nối tới Server!");
    }
}

async function doRegister() {
    const u = document.getElementById("inp-user").value;
    const p = document.getElementById("inp-pass").value;
    if(!u) return alert("Vui lòng nhập Username!");

    try {
        const res = await fetch("/api/register", {
            method: "POST", headers: {"Content-Type":"application/json"},
            body: JSON.stringify({username: u, password: p})
        });
        const data = await res.json();
        
        if(data.status === "success") {
            alert("Đăng ký thành công!");
        } else {
            alert("Lỗi: " + data.msg);
        }
    } catch (err) {
        console.error(err);
        alert("Không thể kết nối tới Server!");
    }
}

// B. Logic Reset Data
async function resetAllData() {
    if(!confirm("⚠️ NGUY HIỂM: Hành động này sẽ xóa sạch tiền và lịch sử lệnh trong Database!\nTiếp tục?")) return;
    
    await fetch("/api/reset_data", {
        method: "POST", headers: {"Content-Type":"application/json"},
        body: JSON.stringify({username: currentUser, password: ""})
    });
    location.reload();
}

// C. Logic WebSocket
function connectWebSocket() {
    if (ws) ws.close();

    // Kiểm tra an toàn lần cuối
    if (!currentUser) {
        console.warn("Chưa có User, hủy kết nối WS.");
        document.getElementById("login-overlay").style.display = "flex";
        return;
    }

    ws = new WebSocket("ws://" + window.location.host + "/ws");

    ws.onopen = () => {
        console.log(`✅ Connected as [${currentUser}]`);
        // Gửi gói tin Login ngay lập tức
        ws.send(JSON.stringify({ type: "LOGIN", username: currentUser }));
    };

    ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);

        if (msg.type === "HISTORY") {
            candleSeries.setData(msg.data);
            chart.timeScale().fitContent();
        }

        if (msg.type === "UPDATE") {
            // Update Title
            document.getElementById("sym").innerText = msg.symbol + " (" + msg.timeframe + ")";

            // Update Input (nếu không focus)
            const inputField = document.getElementById("symbol-input");
            if (document.activeElement !== inputField) {
                inputField.value = msg.symbol;
            }
            
            // Update Chart
            candleSeries.update(msg.candle);
            
            // Update UI
            renderStrategies(msg.strategies, msg.details, msg.timeframe);
        }
    };

    ws.onclose = () => console.log("⚠️ Mất kết nối WS.");
    ws.onerror = (err) => console.error("WS Error:", err);
}

// --- 3. CÁC HÀM API & UI ---

async function changeSymbol() {
    const symInput = document.getElementById("symbol-input");
    const newSym = symInput.value.trim();
    const btn = document.getElementById("btn-symbol");

    if(!newSym) return alert("Nhập mã!");
    
    const oldText = btn.innerText;
    btn.innerText = "⏳"; btn.disabled = true;

    try {
        const res = await fetch("/api/symbol", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ symbol: newSym })
        });
        const data = await res.json();

        if(data.status === "success") {
            console.log("🔀 Đổi mã OK -> Reconnect WS");
            connectWebSocket(); 
        } else {
            alert("Lỗi: " + data.msg);
        }
    } catch (err) { alert("Lỗi kết nối!"); } 
    finally { btn.innerText = oldText; btn.disabled = false; }
}

async function changeTimeframe() {
    const tf = document.getElementById("tf-select").value;
    try {
        await fetch("/api/timeframe", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ timeframe: tf })
        });
        connectWebSocket(); 
    } catch (err) { console.error(err); }
}

async function updateGlobalCapital() {
    const cap = parseFloat(document.getElementById("inp-global-cap").value);
    if(confirm(`⚠️ Reset vốn về ${cap}$?`)) {
        // Gửi header X-User
        await fetch("/api/setting/global", {
            method: "POST", 
            headers: { "Content-Type": "application/json", "X-User": currentUser },
            body: JSON.stringify({ capital: cap })
        });
        connectWebSocket();
    }
}

async function updateStrategyConfig(name) {
    const lev = parseFloat(document.getElementById(`lev-${name}`).value);
    const bet = parseFloat(document.getElementById(`bet-${name}`).value);
    await fetch("/api/setting/strategy", {
        method: "POST", 
        headers: { "Content-Type": "application/json", "X-User": currentUser },
        body: JSON.stringify({ strategy_name: name, leverage: lev, bet_amount: bet })
    });
}

function sendOrder(strat, action) {
    if (!currentUser) {
        alert("Phiên đăng nhập hết hạn!");
        location.reload();
        return;
    }
    fetch("/api/trade", {
        method: "POST",
        headers: { 
            "Content-Type": "application/json", 
            "X-User": currentUser 
        },
        body: JSON.stringify({ action: action, strategy: strat })
    }).catch(err => console.error(err));
}

function estimateDuration(detail, timeframe) {
    if (!detail || !detail.tp_price || !detail.entry_price || !detail.atr) return "---";
    const dist = Math.abs(detail.tp_price - detail.entry_price);
    const candlesNeeded = Math.ceil(dist / detail.atr);
    let mins = 15;
    if (timeframe === "1h") mins = 60;
    if (timeframe === "1m") mins = 1;
    if (timeframe === "5m") mins = 5;
    return `~${candlesNeeded * mins}p`;
}

// --- 4. HÀM RENDER (ĐÃ CẬP NHẬT THEO YÊU CẦU CỦA BẠN) ---
function renderStrategies(data, details, timeframe) {
    const container = document.getElementById("strategy-box");
    
    data.forEach(strat => {
        const cardId = `card-${strat.name}`;
        let card = document.getElementById(cardId);
        
        const detail = details ? details[strat.name] : {};
        const logs = strat.logs || [];
        const logHtml = logs.map(l => `<div class="log-line">${l}</div>`).join("");
        const pnlClass = strat.pnl_total >= 0 ? "up" : "down";
        const pnlText = `${strat.pnl_total > 0 ? "+" : ""}${strat.pnl_total}$`;
        const isManual = strat.name === "Manual_Trader";

        // --- TẠO MỚI ---
        if (!card) {
            const newCard = document.createElement("div");
            newCard.id = cardId;
            newCard.className = `strat-card ${strat.is_best ? 'best' : ''}`;
            newCard.style.minWidth = "280px";
            
            let actionButtons = isManual ? `
                <div class="manual-grid">
                    <button class="btn btn-buy" onclick="sendOrder('Manual_Trader', 'BUY')">LONG</button>
                    <button class="btn btn-close" onclick="sendOrder('Manual_Trader', 'CLOSE')">CLOSE</button>
                    <button class="btn btn-sell" onclick="sendOrder('Manual_Trader', 'SELL')">SHORT</button>
                </div>` : `
                <div class="card-actions" style="margin-top:5px; text-align:center;">
                    <button class="mini-btn btn-close" onclick="sendOrder('${strat.name}', 'CLOSE')" style="width:100%">⛔ Đóng Lệnh</button>
                </div>`;

            // HTML Đã cập nhật mini-log style="height:60px;"
            newCard.innerHTML = `
                ${strat.is_best ? '<div class="best-label">🏆 TOP 1</div>' : ''}
                <div class="best-label-placeholder" style="display:none"></div>

                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h3 style="color:${isManual ? '#58a6ff' : '#e0e0e0'}">${strat.name}</h3>
                    <span class="status-badge status-${strat.signal}" id="status-${strat.name}">${strat.signal}</span>
                </div>

                <div style="display:flex; justify-content:space-between; align-items:center; margin-top:5px;">
                    <span class="pnl-value ${pnlClass}" id="pnl-${strat.name}">${pnlText}</span>
                    <div style="text-align:right; font-size:11px; color:#8b949e;">
                        <div id="equity-${strat.name}">Eq: ${strat.equity}$</div>
                        <div id="margin-${strat.name}">Mg: ${strat.margin_used}$</div>
                    </div>
                </div>

                <div class="config-row">
                    <div class="config-item">
                        <span>Lev(x):</span>
                        <input type="number" id="lev-${strat.name}" value="${strat.leverage}" onchange="updateStrategyConfig('${strat.name}')">
                    </div>
                    <div class="config-item">
                        <span>Bet($):</span>
                        <input type="number" id="bet-${strat.name}" value="${strat.bet_amount}" onchange="updateStrategyConfig('${strat.name}')">
                    </div>
                </div>

                ${!isManual ? `<div class="ai-suggestion" id="ai-${strat.name}">Target: <strong>${detail.tp_price || 0}</strong> | ⏳ ${estimateDuration(detail, timeframe)}</div>` : ''}

                ${actionButtons}

                <div class="mini-log" style="height:60px;" id="log-${strat.name}">${logHtml}</div>
            `;
            container.appendChild(newCard);
            
        } 
        // --- CẬP NHẬT ---
        else {
            // Update Best Label
            if (strat.is_best) {
                if (!card.classList.contains('best')) card.classList.add('best');
                if (!card.querySelector('.best-label')) card.insertAdjacentHTML('afterbegin', '<div class="best-label">🏆 TOP 1</div>');
            } else {
                if (card.classList.contains('best')) card.classList.remove('best');
                const badge = card.querySelector('.best-label');
                if (badge) badge.remove();
            }

            // Update Texts
            const statusEl = document.getElementById(`status-${strat.name}`);
            if (statusEl.innerText !== strat.signal) {
                statusEl.innerText = strat.signal;
                statusEl.className = `status-badge status-${strat.signal}`;
            }

            const pnlEl = document.getElementById(`pnl-${strat.name}`);
            pnlEl.innerText = pnlText;
            pnlEl.className = `pnl-value ${pnlClass}`;

            document.getElementById(`equity-${strat.name}`).innerText = `Eq: ${strat.equity}$`;
            document.getElementById(`margin-${strat.name}`).innerText = `Mg: ${strat.margin_used}$`;

            if (!isManual) {
                const aiEl = document.getElementById(`ai-${strat.name}`);
                const newAiHtml = `Target: <strong>${detail.tp_price || 0}</strong> | ⏳ ${estimateDuration(detail, timeframe)}`;
                if (aiEl.innerHTML !== newAiHtml) aiEl.innerHTML = newAiHtml;
            }

            // Update Inputs (Avoid focus loss)
            const levInput = document.getElementById(`lev-${strat.name}`);
            if (document.activeElement !== levInput) levInput.value = strat.leverage;

            const betInput = document.getElementById(`bet-${strat.name}`);
            if (document.activeElement !== betInput) betInput.value = strat.bet_amount;

            // Update Log (Preserve Scroll)
            const logBox = document.getElementById(`log-${strat.name}`);
            if (logBox.innerHTML !== logHtml) {
                const currentScroll = logBox.scrollTop;
                logBox.innerHTML = logHtml;
                logBox.scrollTop = currentScroll; 
            }
        }
    });
}

// --- 5. LOGIC KHỞI ĐỘNG CUỐI CÙNG ---
// Kiểm tra user, nếu có thì kết nối, nếu không thì hiện Login
if (currentUser) {
    document.getElementById("login-overlay").style.display = "none";
    connectWebSocket();
} else {
    document.getElementById("login-overlay").style.display = "flex";
}