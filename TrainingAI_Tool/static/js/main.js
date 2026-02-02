/* static/js/main.js */
let globalWS = null;
let currentView = 'dashboard';
let currentRadarTF = "M5";

// --- 1. CẤU HÌNH & UTILS ---
const fmtMoney = (num) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(num);
};

const fmtNum = (num) => {
    return new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 5 }).format(num);
};

// --- 2. QUẢN LÝ USER (LOGIN SYSTEM) ---
function ensureUser() {
    let user = localStorage.getItem("trader_user");
    console.log("Current User:", user);

    // NẾU CHƯA CÓ USER: HỎI NGƯỜI DÙNG (Không tự gán Trader1 nữa)
    if (!user || user === "null") {
        // Hiện hộp thoại nhập tên
        user = prompt("Chào mừng! Vui lòng nhập tên tài khoản để bắt đầu:", "");
        
        if (user && user.trim() !== "") {
            // Nếu người dùng chịu nhập -> Lưu lại
            localStorage.setItem("trader_user", user);
        } else {
            // Nếu bấm Cancel hoặc để trống -> Trả về null (Chế độ Khách)
            user = null;
        }
    }
    
    // Hiển thị tên lên Topbar
    const userInfo = document.getElementById('user-info');
    if (userInfo) {
        userInfo.innerText = user ? user : "Khách (Guest)";
        // Đổi màu chữ nếu là Khách để dễ nhận biết
        userInfo.style.color = user ? "#c9d1d9" : "#da3633"; 
    }
    
    return user;
}

// --- 3. LOGIC DASHBOARD (Trang chủ) ---
async function updateDashboard() {
    // Lưu ý: Không gọi ensureUser() ở đây nữa để tránh hiện popup liên tục
    // Chỉ lấy từ localStorage ra thôi
    const username = localStorage.getItem("trader_user");
    
    // Nếu là Khách (không có username) -> Không gọi API Stats
    if (!username) {
        document.querySelectorAll('.card-value').forEach(el => el.innerText = "---");
        return; 
    }

    try {
        const response = await fetch(`/api/stats/${username}`);
        if (!response.ok) throw new Error("API Stats Error");
        
        const data = await response.json();
        const cards = document.querySelectorAll('.card-value');
        
        if (cards.length >= 3) {
            cards[0].innerText = fmtMoney(data.balance);
            
            const pnlVal = data.pnl || 0;
            cards[1].innerText = (pnlVal > 0 ? '+' : '') + fmtMoney(pnlVal);
            cards[1].style.color = pnlVal >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';
            
            cards[2].innerText = fmtMoney(data.equity || data.balance);
        }
    } catch (e) { 
        console.error("Dashboard error:", e); 
    }
}


// Hàm áp dụng theme
function applyTheme(themeName) {
    if (themeName === 'cyber') {
        document.body.setAttribute('data-theme', 'cyber');
    } else {
        document.body.removeAttribute('data-theme'); // Mặc định (Dark)
    }
}

// Hàm đổi TF
function switchRadarTF(tf) {
    currentRadarTF = tf;
    
    // Update UI Active Button
    document.querySelectorAll('.btn-tf').forEach(b => {
        b.classList.remove('active');
        if(b.innerText === tf) b.classList.add('active');
    });

    // Gọi update ngay lập tức
    updateRadarPage();
}

// --- 4. LOGIC RADAR PAGE (Trang /radar) ---
// Radar là dữ liệu chung (Public), nên Khách vẫn xem được bình thường
async function updateRadarPage() {
    try {
        // Gọi API với tham số TF
        console.log(`Fetching radar: /api/scan-results?tf=${currentRadarTF}`);

        const response = await fetch(`/api/scan-results?tf=${currentRadarTF}`);
        if (!response.ok) {
            console.error("Server returned:", response.status);
            throw new Error(`Server Error: ${response.status}`);
        }
        
        const resJson = await response.json();
        const data = resJson.data || {};     
        const status = resJson.status || "UNKNOWN";
        console.log("Radar Status:", status);

        const tbody = document.getElementById('radar-body');
        if (!tbody) return;

        if (Object.keys(data).length === 0) {
            let msg = "Đang khởi động Scanner...";
            let color = "#8b949e";

            if (status.includes("CLOSED")) {
                msg = "💤 THỊ TRƯỜNG ĐANG ĐÓNG CỬA";
                color = "var(--accent-red)";
            } else if (status === "LOADING" || status === "Starting...") {
                msg = "🔄 Đang khởi động hệ thống AI...";
                color = "var(--accent-blue)";
            }

            tbody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align:center; padding: 40px;">
                        <div style="font-size: 1.2rem; color: ${color}; font-weight: bold;">
                            <i class="fa-solid fa-store-slash"></i> ${msg}
                        </div>
                        <div style="font-size: 0.9rem; color: var(--text-muted); margin-top: 10px;">
                            Status: ${status}
                        </div>
                    </td>
                </tr>`;
            return;
        }

        tbody.innerHTML = ''; 

        if (Object.keys(data).length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:20px">Đang quét ${currentRadarTF}...</td></tr>`;
            return;
        }

        for (const [symbol, info] of Object.entries(data)) {
            // ... (Logic màu sắc cũ giữ nguyên) ...
            
            // TÍNH TOÁN TIỀN DỰ KIẾN (EST. PROFIT)
            // Giả định đánh 0.1 Lot
            let lotSize = 0.1;
            let contractSize = symbol.includes("XAU") ? 100 : 100000; // Vàng 100, Forex 100k
            let price = info.price || 0;
            let score = info.score || 0;
            let signal = info.signal || "NEUTRAL";

            // Khoảng cách từ Entry đến TP
            let distTP = Math.abs(info.suggested_tp - price);
            let profitUSD = distTP * contractSize * lotSize;
            
            // Format số tiền
            let profitStr = `+${fmtMoney(profitUSD)}`;
            let riskStr = `-${fmtMoney(Math.abs(price - info.suggested_sl) * contractSize * lotSize)}`;

            const row = `
                <tr class="radar-row-hover">
                    <td><b>${symbol}</b></td>
                    <td style="color:${info.macro_trend==='UPTREMD'?'var(--accent-green)':'var(--accent-red)'}">
                        ${fmtNum(price)}
                    </td>
                    
                    <td><span class="badge badge-neutral">${info.macro_trend}</span></td>
                    
                    <td><span class="badge ${signal.includes('BUY')?'badge-buy':(signal.includes('SELL')?'badge-sell':'badge-neutral')}">${signal}</span></td>
                    
                    <td>
                        <div style="font-size:0.8rem">
                            <span style="color:var(--accent-red)">SL: ${info.suggested_sl}</span><br>
                            <span style="color:var(--accent-green)">TP: ${info.suggested_tp}</span>
                        </div>
                    </td>
                    
                    <td>
                        <div style="font-size:0.8rem">
                            <span style="color:var(--accent-green)">Target: ${profitStr}</span><br>
                            <span style="color:var(--text-muted); font-size:0.7rem">Risk: ${riskStr}</span>
                        </div>
                    </td>

                    <td style="font-size:0.8rem; color:var(--text-muted)">${info.reason}</td>
                </tr>
            `;
            tbody.innerHTML += row;
        }
    } catch (error) { 
        console.error("Radar error:", error);
        // Hiển thị lỗi kết nối lên giao diện thay vì console
        const tbody = document.getElementById('radar-body');
        if(tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align:center; color: var(--accent-red); padding: 20px;">
                        ⚠️ Mất kết nối tới Server (${error.message})<br>
                        <small>Đang thử lại...</small>
                    </td>
                </tr>`;
        }
    }
}


function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    globalWS = new WebSocket(`${protocol}//${window.location.host}/ws`);

    globalWS.onopen = () => {
        console.log("🟢 WS Connected");
        // Nếu Terminal đã init, gửi yêu cầu subscribe symbol hiện tại
        if(TerminalApp.currentSymbol) {
            sendWsMessage({type: "SWITCH_SYMBOL", symbol: TerminalApp.currentSymbol});
        }
    };

    globalWS.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        
        // PHÂN PHỐI DỮ LIỆU
        
        // A. Dữ liệu cho Terminal (Chart & Tick)
        if (msg.type === "HISTORY" || msg.type === "UPDATE") {
            // Chỉ update chart nếu đang xem Terminal để tiết kiệm CPU
            if (currentView === 'terminal') {
                TerminalApp.handleWsMessage(msg);
            }
        }
        
        // B. Dữ liệu cho Radar (nếu sau này bạn stream radar qua WS)
        // ...
    };

    globalWS.onclose = () => {
        console.log("🔴 WS Disconnected. Reconnecting...");
        setTimeout(initWebSocket, 3000);
    };
}

// Hàm gửi tin nhắn public để Terminal.js gọi
window.sendWsMessage = (data) => {
    if(globalWS && globalWS.readyState === WebSocket.OPEN) {
        globalWS.send(JSON.stringify(data));
    }
};

// --- 3. VIEW ROUTER (SPA LOGIC) ---
function switchView(viewName) {
    currentView = viewName;
    
    // 1. Update Menu Active
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    document.getElementById(`nav-${viewName}`).classList.add('active');
    
    // 2. Hide All Views
    document.querySelectorAll('.view-section').forEach(el => el.style.display = 'none');
    
    // 3. Show Selected View
    document.getElementById(`view-${viewName}`).style.display = 'block';
    
    // 4. Trigger Init Logic (Lazy Load)
    if (viewName === 'terminal') {
        TerminalApp.init(); // Init chart nếu chưa có
        // Gửi lại request lấy data chart vì có thể kết nối đã idle
        sendWsMessage({type: "SWITCH_SYMBOL", symbol: TerminalApp.currentSymbol, timeframe: TerminalApp.currentTimeframe });
    } else if (viewName === 'radar') {
        updateRadarPage();
    } else {
        updateDashboard();
    }
}

// Hàm toggle (gọi khi bấm nút)
window.toggleTheme = function() {
    const current = localStorage.getItem('app_theme');
    const newTheme = current === 'cyber' ? 'default' : 'cyber';
    
    localStorage.setItem('app_theme', newTheme);
    applyTheme(newTheme);
};

// --- 5. MAIN EXECUTION ---
document.addEventListener("DOMContentLoaded", () => {
    // Gọi 1 lần khi load trang để xác định User
    ensureUser();
    initWebSocket();

    switchView('dashboard');
    setInterval(() => {
        if(currentView === 'dashboard') updateDashboard();
        if(currentView === 'radar') updateRadarPage();
    }, 2000);

    const savedTheme = localStorage.getItem('app_theme');
    applyTheme(savedTheme);
});


// Hàm Global Logout
window.logout = function() {
    // Nếu chưa đăng nhập thì nút này đóng vai trò là "Đăng nhập"
    const currentUser = localStorage.getItem("trader_user");
    const msg = currentUser ? "Bạn muốn đổi tài khoản?" : "Đăng nhập tài khoản mới?";
    
    if(confirm(msg)) {
        const newUser = prompt("Nhập tên tài khoản:", currentUser || "");
        if (newUser && newUser.trim() !== "") {
            localStorage.setItem("trader_user", newUser);
            window.location.reload(); // Reload để áp dụng
        }
    }
};