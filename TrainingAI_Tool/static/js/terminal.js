/* static/js/terminal.js */

const TerminalApp = {
    chart: null,
    series: null,
    currentSymbol: "XAUUSD.sml",
    currentTimeframe: "M5",
    lastCandleTime: 0,
    radarInterval: null,

    init: function() {
        if (this.chart) return; 

        // 1. Khởi tạo Chart
        const chartContainer = document.getElementById('tv-chart');
        if(!chartContainer) return;

        this.chart = LightweightCharts.createChart(chartContainer, {
            layout: { backgroundColor: 'transparent', textColor: '#d1d5db' },
            grid: { vertLines: { color: 'rgba(42, 46, 57, 0.5)' }, horzLines: { color: 'rgba(42, 46, 57, 0.5)' } },
            timeScale: { timeVisible: true, secondsVisible: false }
        });
        this.series = this.chart.addCandlestickSeries();
        
        // Resize observer
        new ResizeObserver(entries => {
            if (!entries[0]) return;
            const { width, height } = entries[0].contentRect;
            this.chart.applyOptions({ width, height });
        }).observe(chartContainer);

        // Load lệnh lần đầu
        this.loadOrders();
        
        // 2. Kích hoạt Radar Loop
        this.updateRadar(); 
        if (this.radarInterval) clearInterval(this.radarInterval);
        this.radarInterval = setInterval(() => this.updateRadar(), 2000);

        console.log("Terminal Initialized");
    },
    requestChartData: function() {
        this.series.setData([]);
        this.lastCandleTime = 0;
        this.showStatus(`Đang tải ${this.currentSymbol} (${this.currentTimeframe})...`);

        if(window.sendWsMessage) {
            window.sendWsMessage({
                type: "SWITCH_SYMBOL", 
                symbol: this.currentSymbol,
                timeframe: this.currentTimeframe 
            });
        }
    },
    changeTimeframe: function(tf) {
        if (this.currentTimeframe === tf) return;
        this.currentTimeframe = tf;

        // Update UI Active Class
        document.querySelectorAll('.btn-tf-sm').forEach(btn => {
            btn.classList.remove('active');
            if(btn.innerText === tf) btn.classList.add('active');
        });

        // Gọi hàm request chung
        this.requestChartData();
    },
    // --- XỬ LÝ DỮ LIỆU TỪ WEBSOCKET (DO MAIN.JS GỌI) ---
    handleWsMessage: function(msg) {
        if (msg.type === "HISTORY") {
            const sorted = msg.data.sort((a,b) => a.time - b.time);
            this.series.setData(sorted);
            if(sorted.length > 0) {
                this.updatePriceDisplay(sorted[sorted.length-1].close);
                this.lastCandleTime = sorted[sorted.length-1].time;
                this.showStatus("");
            } else {
                this.showStatus("Không có dữ liệu lịch sử", true);
            }
        }
        
        if (msg.type === "UPDATE" && msg.symbol === this.currentSymbol) {
            if (msg.candle.time < this.lastCandleTime) return;
            this.series.update(msg.candle);
            this.lastCandleTime = msg.candle.time;
            this.updatePriceDisplay(msg.candle.close);
        }
    },

    updatePriceDisplay: function(price) {
        const el = document.getElementById('chart-price');
        if(el) el.innerText = price;
        this.calculateVolume(price);
        this.updateActivePnL(price);
    },
    changeSymbol: function(symbol) {
        this.currentSymbol = symbol;
        document.getElementById('inp-symbol').value = symbol;
        document.getElementById('chart-symbol').innerText = symbol;
        
        // Highlight RadarRow
        document.querySelectorAll('.radar-row').forEach(r => r.classList.remove('active'));
        const row = document.getElementById(`radar-${symbol}`);
        if(row) row.classList.add('active');

        // Gửi yêu cầu switch qua WS Global (Gọi hàm từ window hoặc main)
        if(window.sendWsMessage) {
            window.sendWsMessage({type: "SWITCH_SYMBOL", symbol: symbol, timeframe: this.currentTimeframe });
        }
    },
    hangeSymbol: function(symbol) {
        this.currentSymbol = symbol;
        document.getElementById('inp-symbol').value = symbol;
        document.getElementById('chart-symbol').innerText = symbol;
        
        // Highlight RadarRow
        document.querySelectorAll('.radar-row').forEach(r => r.classList.remove('active'));
        const row = document.getElementById(`radar-${symbol}`);
        if(row) row.classList.add('active');

        this.requestChartData(); 
    },

    calculateVolume: function(currentPrice) {
        if(!currentPrice) return;
        if(document.getElementById('mode-money').style.display === 'none') return;
        
        const amt = parseFloat(document.getElementById('inp-amount').value) || 0;
        const lev = parseFloat(document.getElementById('inp-leverage').value) || 1;
        let size = this.currentSymbol.includes("XAU") ? 100 : 1;
        
        let vol = (amt * lev) / (currentPrice * size);
        vol = Math.max(0.01, Math.round(vol*100)/100);
        
        const el = document.getElementById('calc-vol');
        if(el) el.innerText = vol.toFixed(2);
    },

    toggleMode: function(mode) {
        document.getElementById('mode-money').style.display = mode === 'money' ? 'block' : 'none';
        document.getElementById('mode-vol').style.display = mode === 'vol' ? 'block' : 'none';
    },

    // --- API CALLS ---
    sendOrder: async function(side) {
        const username = localStorage.getItem("trader_user");
        let vol = parseFloat(document.getElementById('calc-vol').innerText);
        if(document.getElementById('mode-vol').style.display === 'block') {
            vol = parseFloat(document.getElementById('inp-vol').value);
        }
        
        const res = await fetch('/api/trade', {
            method:'POST', headers:{'Content-Type':'application/json'},
            body:JSON.stringify({username, symbol:this.currentSymbol, action:side, volume:vol})
        });
        const data = await res.json();
        const msgBox = document.getElementById('msg-box');
        msgBox.innerText = data.msg;
        msgBox.style.color = data.status==='success'?'var(--accent-green)':'var(--accent-red)';
        this.loadOrders();
    },

    loadOrders: async function() {
        const username = localStorage.getItem("trader_user");
        if(!username) return;
        const res = await fetch(`/api/orders/${username}?t=${Date.now()}`);
        const data = await res.json();
        
        const activeBody = document.getElementById('active-body');
        const historyBody = document.getElementById('history-body');
        if(!activeBody || !historyBody) return;

        activeBody.innerHTML = "";
        historyBody.innerHTML = "";
        
        let count = 0;
        if(data.status === 'success') {
            data.data.forEach(o => {
                if(o.status==='OPEN') {
                    count++;
                    activeBody.innerHTML += `
                        <tr id="row-${o.id}" data-entry="${o.entry_price}" data-vol="${o.volume}" data-type="${o.type}">
                            <td>#${o.id}</td>
                            <td style="color:${o.type==='BUY'?'var(--accent-green)':'var(--accent-red)'}">${o.type}</td>
                            <td>${o.volume}</td>
                            <td>${o.entry_price}</td>
                            <td class="live-pnl">...</td>
                            <td><button onclick="TerminalApp.closeOrder(${o.id})" class="btn-sm-danger">✖</button></td>
                        </tr>`;
                } else {
                    const pnlColor = o.pnl>=0?'var(--accent-green)':'var(--accent-red)';
                    historyBody.innerHTML += `
                        <tr>
                            <td style="color:var(--text-muted); font-size:0.8rem">${o.close_time?.split(' ')[1]||''}</td>
                            <td style="color:${o.type==='BUY'?'var(--accent-green)':'var(--accent-red)'}">${o.type}</td>
                            <td>${o.exit_price}</td>
                            <td style="color:${pnlColor}; font-weight:bold">${o.pnl.toFixed(2)}$</td>
                        </tr>`;
                }
            });
        }
        document.getElementById('count-active').innerText = count;
    },

    updateActivePnL: function(price) {
        document.querySelectorAll('#active-body tr').forEach(row => {
            const entry = parseFloat(row.dataset.entry);
            const vol = parseFloat(row.dataset.vol);
            const type = row.dataset.type;
            let pnl = (type==='BUY' ? price-entry : entry-price) * vol;
            if(this.currentSymbol.includes("XAU")) pnl *= 100;
            
            const cell = row.querySelector('.live-pnl');
            cell.innerText = pnl.toFixed(2) + "$";
            cell.style.color = pnl>=0?'var(--accent-green)':'var(--accent-red)';
        });
    },
    closeOrder: async function(id) {
        if(!confirm("Close #"+id+"?")) return;
        const username = localStorage.getItem("trader_user");
        await fetch('/api/close-order', {
            method:'POST', headers:{'Content-Type':'application/json'},
            body:JSON.stringify({order_id:id, username})
        });
        this.loadOrders();
    },
    openTab: function(evt, tabName) {
        // Ẩn tất cả tab content
        document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
        // Bỏ active tất cả tab btn
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        
        // Hiện tab được chọn
        document.getElementById(tabName).classList.add('active');
        if(evt && evt.currentTarget) evt.currentTarget.classList.add('active');
    },
    updateRadar: async function() {
        try {
            const response = await fetch('/api/scan-results');
            const resJson = await response.json();
            const data = resJson.data || {};     
            const status = resJson.status || "UNKNOWN";
            console.log("Radar Status:", status);
            // Xây dựng HTML
            let html = "";
            for(const [sym, info] of Object.entries(data)) {
                let color = info.signal.includes('BUY')?'var(--accent-green)':(info.signal.includes('SELL')?'var(--accent-red)':'#8b949e');
                
                // Highlight dòng đang chọn
                let activeClass = sym === this.currentSymbol ? 'active' : '';
                
                // QUAN TRỌNG: Gọi TerminalApp.changeSymbol thay vì changeSymbol khơi khơi
                html += `<div id="radar-${sym}" class="radar-row ${activeClass}" onclick="TerminalApp.changeSymbol('${sym}')">
                    <div class="radar-symbol">${sym}</div>
                    <div style="display:flex; justify-content:space-between; font-size:0.8rem; color:var(--text-muted)">
                        <span>RSI: ${info.rsi}</span>
                        <span style="color:${color}; font-weight:bold">${info.signal}</span>
                    </div>
                </div>`;
                
                // Cập nhật gợi ý SL/TP nếu đúng mã đang xem
                if(sym === this.currentSymbol) {
                    const slEl = document.getElementById('suggest-sl');
                    const tpEl = document.getElementById('suggest-tp');
                    if(slEl) slEl.innerText = info.suggested_sl || '---';
                    if(tpEl) tpEl.innerText = info.suggested_tp || '---';
                }
            }
            
            const listEl = document.getElementById('radar-list');
            if(listEl && html) listEl.innerHTML = html;
            
        } catch(e) { console.error("Radar mini error", e); }
    },
    showStatus: function(msg, isError=false) {
        const chartArea = document.getElementById('tv-chart');
        // Tạo một lớp phủ (overlay) nếu chưa có
        let overlay = document.getElementById('chart-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'chart-overlay';
            overlay.style.cssText = "position:absolute; top:50%; left:50%; transform:translate(-50%, -50%); color:#8b949e; z-index:10; pointer-events:none;";
            if(chartArea) chartArea.parentElement.style.position = 'relative'; // Đảm bảo parent relative
            if(chartArea) chartArea.parentElement.appendChild(overlay);
        }
        
        overlay.innerText = msg;
        overlay.style.color = isError ? 'var(--accent-red)' : '#8b949e';
        
        // Nếu có dữ liệu rồi thì ẩn overlay đi
        if (msg === "") overlay.style.display = 'none';
        else overlay.style.display = 'block';
    }

};
window.TerminalApp = TerminalApp;
