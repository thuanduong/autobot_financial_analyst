"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { Candle, Marker } from "@/types/market";
import { getMarketHistoryData, getMarketHistoryRange, getMarketSignalsHistory } from "@/services/marketApi";
import { tradeApi } from "@/services/tradeApi"
import { useSocket } from "@/app/context/SocketContext";

const TF_TO_SECONDS: Record<string, number> = {
  "M1": 60, "M5": 300, "M15": 900, "H1": 3600, "H4": 14400, "D1": 86400
};

export const useMarketData = (symbol: string, tf: string) => {
  const [data, setData] = useState<Candle[]>([]);
  const [markers, setChartMarkers] = useState<Marker[]>([]);

  // --- SETTINGS ÂM THANH ---
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [volume, setVolume] = useState(0.5);

  // Dùng Ref để callback socket luôn lấy được volume mới nhất mà không cần re-subscribe
  const settingsRef = useRef({ soundEnabled, volume });
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    const savedSound = localStorage.getItem("trading_sound_enabled");
    const savedVolume = localStorage.getItem("trading_sound_volume");
    if (savedSound !== null) setSoundEnabled(savedSound === "true");
    if (savedVolume !== null) setVolume(parseFloat(savedVolume));
  }, []);

  // Khởi tạo Audio một lần duy nhất khi mount để "giữ chỗ" trong hệ thống âm thanh của trình duyệt
  useEffect(() => {
    const audio = new Audio("/sounds/signal-alert.mp3");
    audio.preload = "auto";
    audioRef.current = audio;
  }, []);

  useEffect(() => {
    settingsRef.current = { soundEnabled, volume };
  }, [soundEnabled, volume]);

  const playSignalSound = useCallback(() => {
    if (!settingsRef.current.soundEnabled || !audioRef.current) return;
    
    try {
      const audio = audioRef.current;
      audio.volume = settingsRef.current.volume;
      
      // Đưa thời gian về 0 để có thể phát lại ngay lập tức nếu có nhiều tín hiệu dồn dập
      audio.currentTime = 0;
      
      // Phát âm thanh và bắt lỗi (trình duyệt có thể chặn nếu chưa có tương tác người dùng)
      audio.play().catch((err) => {
        console.warn("Background audio play was prevented by browser policy:", err);
      });
    } catch (e) {
      console.warn("Audio play failed", e);
    }
  }, []); // Dependencies trống để giữ function reference ổn định

  const { isConnected, subscribe, unsubscribe } = useSocket(); // Lấy hàm từ Core
  
  // Dùng Ref để lưu context hiện tại cho callback
  const contextRef = useRef({ symbol, tf, playSignalSound });
  const isFetchingRef = useRef(false);
  
  // CHỐT CHẶN: Đảm bảo marker không bao giờ vượt quá cây nến cũ nhất (tránh tràn/hiển thị sai)
  useEffect(() => {
    if (data.length === 0 || markers.length === 0) return;
    
    const oldestCandleTime = data[0].time;
    setChartMarkers(prev => {
      // Chỉ giữ lại các marker có thời gian >= nến cũ nhất
      const filtered = prev.filter(m => m.time >= oldestCandleTime);
      // Nếu không có gì thay đổi thì không set state để tránh re-render thừa
      if (filtered.length === prev.length) return prev;
      return filtered;
    });
  }, [data[0]?.time]); // Chạy lại mỗi khi nến cũ nhất thay đổi (load more hoặc cắt RAM)

  // 1. Load History (HTTP) khi đổi cặp tiền
  useEffect(() => {
    contextRef.current = { ...contextRef.current, symbol, tf };
    setData([]); 
    isFetchingRef.current = false;

    const fetchInitialHistory = async () => {
      try {
        // Gọi API lấy dữ liệu lịch sử (500 nến)
        const [historyCandles, historySignals, signalResult] = await Promise.all([
          getMarketHistoryData(symbol, tf, 500),
          getMarketSignalsHistory(symbol, tf, 100),
          tradeApi.getBotHistory(symbol, tf, 100)
        ]);

        // Cập nhật vào State -> Kích hoạt re-render -> Truyền xuống Chart
        setData(historyCandles);
        
        const oldestTime = historyCandles[0]?.time || 0;

        // Map và lọc marker ngay từ đầu theo nến cũ nhất
        const m1: Marker[] = historySignals.map((msg: any) => {
          const isBuy = msg.signal.includes("BUY");
          return {
            time: msg.time,
            position: isBuy ? 'belowBar' : 'aboveBar',
            color: isBuy ? '#2ea043' : '#da3633',
            shape: isBuy ? 'arrowUp' : 'arrowDown',
            text: msg.signal,
            size: 1,
          };
        }).filter((m: Marker) => m.time >= oldestTime);

        let m2: Marker[] = [];
        if (signalResult && signalResult.status === "success") {
          m2 = signalResult.data
            .map((item: any) => formatTradeMarker(item))
            .filter((m: Marker) => m.time >= oldestTime);
        }

        // Gộp và xóa trùng lặp
        const combined = [...m1, ...m2];
        const unique = Array.from(new Map(combined.map(m => [`${m.time}_${m.strategy_id}`, m])).values());
        setChartMarkers(unique.sort((a, b) => a.time - b.time));

        console.log("Tải lịch sử xong: ", historyCandles.length);
      } catch (error) {
        console.error("Lỗi tải lịch sử:", error);
      }
    };

    fetchInitialHistory();
  }, [symbol, tf]);

  // 2. Đăng ký nhận 'PRICE_UPDATE' từ Socket Core
  useEffect(() => {
    // Định nghĩa hàm xử lý khi có tin nhắn tới
    const handlePriceUpdate = (msg: any) => {
      // Lọc dữ liệu: Chỉ lấy đúng Symbol/TF mình đang xem
      if (msg.symbol !== contextRef.current.symbol || msg.tf !== contextRef.current.tf) return;

      const newCandles = Array.isArray(msg.data) ? msg.data : [msg.data];
      
      setData((prevData) => {
        const updated = [...prevData];
        newCandles.forEach((candle: Candle) => {
          if (updated.length === 0) {
            updated.push(candle);
            return;
          }
          //console.log(`${candle.time} - ${candle.value}`);
          const last = updated[updated.length - 1];
          if (candle.time === last.time) {
            updated[updated.length - 1] = candle; // Update tick
          } else if (candle.time > last.time) {
            updated.push(candle); // New candle
          }
        });
        
        if (updated.length > 10000) return updated.slice(-10000);
        return updated;

      });
    };

    const handleSignalUpdate = (msg: any) => {
      if (msg.symbol === contextRef.current.symbol && msg.tf === contextRef.current.tf) {
        // Phát âm thanh nếu là tín hiệu mới (Mới bóp cò - PENDING)
        if (msg.data.outcome === 'PENDING') {
          contextRef.current.playSignalSound();
        }

        const newMarker = formatTradeMarker(msg.data);

        setChartMarkers(prev => {
          const filtered = prev.filter(m => !(m.time === newMarker.time && m.strategy_id === newMarker.strategy_id));
          const updatedMarkers = [...filtered, newMarker];
          updatedMarkers.sort((a, b) => a.time - b.time); 
          return updatedMarkers;
        });
      }
    };

    // Đăng ký (Subscribe)
    subscribe("PRICE_UPDATE", handlePriceUpdate);
    subscribe("SIGNAL_UPDATE", handleSignalUpdate);

    // Theo dõi trạng thái kết nối
    if (!isConnected) {
      console.warn("WebSocket disconnected. Checking authentication...");
    }

    return () => {
      unsubscribe("PRICE_UPDATE", handlePriceUpdate);
      unsubscribe("SIGNAL_UPDATE", handleSignalUpdate);
    };
  }, [subscribe, unsubscribe]); // Chỉ chạy 1 lần khi mount hook

  const loadMoreHistory = useCallback(async () => {
    if (isFetchingRef.current || data.length === 0) return;

    isFetchingRef.current = true; // Bật khóa chống spam API

    try {
      // Tìm thời gian của cây nến cũ nhất hiện tại
      const oldestTime = data[0].time;
      
      // Tính thời gian kết thúc (to_time) và thời gian bắt đầu (from_time)
      const toTime = oldestTime - 1;
      const stepSeconds = (TF_TO_SECONDS[tf] || 300) * 500; // Lùi về 500 nến
      const fromTime = toTime - stepSeconds;

      // Gọi API Range
      const [olderCandles, olderSignalsResult] = await Promise.all([
        getMarketHistoryRange(symbol, tf, fromTime, toTime),
        tradeApi.getBotHistoryRange(symbol, tf, 200, fromTime, toTime) // Tải thêm marker vùng này
      ]);

      if (olderCandles.length > 0) {
        setData(prevData => {
          const merged = [...olderCandles, ...prevData];
          if (merged.length > 10000) return merged.slice(-10000);
          return merged;
        });
      }
      
      if (olderSignalsResult?.status === "success" && olderSignalsResult.data.length > 0) {
        // Vùng chặn thời gian cho marker mới tải về
        const limitTime = olderCandles.length > 0 ? olderCandles[0].time : data[0].time;
        
        const newMarkers = olderSignalsResult.data.map((item: any) => formatTradeMarker(item));
        setChartMarkers(prev => {
          const combined = [...prev, ...newMarkers].filter(m => m.time >= limitTime);
          const uniqueMarkers = Array.from(new Map(combined.map(m => [`${m.time}_${m.strategy_id}`, m])).values());
          return uniqueMarkers.sort((a, b) => a.time - b.time);
        });
      }
    } catch (e) {
      console.error("Load more failed", e);
    } finally {
      // Chờ 500ms rồi mới mở khóa, tránh trigger sự kiện scroll liên tiếp
      setTimeout(() => { isFetchingRef.current = false; }, 500);
    }
  }, [data, symbol, tf]);

  // Hàm cập nhật có persistence
  const updateSoundEnabled = (val: boolean) => {
    setSoundEnabled(val);
    localStorage.setItem("trading_sound_enabled", String(val));
  };
  const updateVolume = (val: number) => {
    setVolume(val);
    localStorage.setItem("trading_sound_volume", String(val));
  };

  return { 
    data, 
    markers, 
    isConnected, 
    loadMoreHistory,
    soundEnabled, setSoundEnabled: updateSoundEnabled,
    volume, setVolume: updateVolume
  };
};

export const formatTradeMarker = (msg: any): Marker => {
  const isBuy = msg.signal.includes("BUY");
  const outcome = msg.outcome || 'PENDING';
  
  // Tô màu: Đang chạy = Vàng, Win = Xanh, Loss = Đỏ
  let markerColor = '#eab308'; 
  if (outcome === 'WIN') markerColor = '#2ea043';
  if (outcome === 'LOSS') markerColor = '#da3633';

  // Format text hiển thị. Ví dụ: "MACD: BUY (WIN)"
  const shortStratName = msg.strategy_id ? msg.strategy_id.split('_')[0] : '';
  const displayText = `${shortStratName}: ${msg.signal} ${outcome !== 'PENDING' ? `(${outcome})` : ''}`;

  return {
    time: msg.time,
    position: isBuy ? 'belowBar' : 'aboveBar',
    color: markerColor,
    shape: isBuy ? 'arrowUp' : 'arrowDown',
    text: displayText,
    size: outcome === 'PENDING' ? 2 : 1, 
    strategy_id: msg.strategy_id || 'UNKNOWN',
    outcome: outcome
  };
};