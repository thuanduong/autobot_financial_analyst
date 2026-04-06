"use client";

import React, { useEffect, useRef } from 'react';
import { 
  createChart, 
  ColorType, 
  IChartApi, 
  ISeriesApi, 
  CandlestickSeries, // 1. Import class Series
  UTCTimestamp,     // 2. Import kiểu Time chuẩn
  createSeriesMarkers,
  ISeriesMarkersPluginApi
} from 'lightweight-charts';
import { Marker, Candle } from '@/types/market';
interface Props {
  data: Candle[];
  markers: Marker[] 
  onLoadMore?: () => void;
}

export const TradingViewChart: React.FC<Props> = ({ data, markers, onLoadMore }) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const markersPluginRef = useRef<ISeriesMarkersPluginApi<any> | null>(null);
  const isInitialLoad = useRef(true);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#1e293b' },
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: '#334155' },
        horzLines: { color: '#334155' },
      },
      width: chartContainerRef.current.clientWidth,
      height: chartContainerRef.current.clientHeight,
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        borderColor: '#475569',
      },
    });

    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderVisible: false,
      wickUpColor: '#22c55e',
      wickDownColor: '#ef4444',
    });

    const markersPlugin = createSeriesMarkers(candlestickSeries, []);
    
    chartRef.current = chart;
    candlestickSeriesRef.current = candlestickSeries;
    markersPluginRef.current = markersPlugin;

    const handleVisibleLogicalRangeChange = (logicalRange: any) => {
      if (logicalRange !== null && onLoadMore) {
        if (logicalRange.from < 30) {
          onLoadMore();
        }
      }
    };
    chart.timeScale().subscribeVisibleLogicalRangeChange(handleVisibleLogicalRangeChange);

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth, height: chartContainerRef.current.clientHeight });
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.timeScale().unsubscribeVisibleLogicalRangeChange(handleVisibleLogicalRangeChange);
      chart.remove();
    };
  }, []);

  // C. Update Data
  useEffect(() => {
    if (candlestickSeriesRef.current) {
        if (data.length === 0) {
          candlestickSeriesRef.current.setData([]); 
          isInitialLoad.current = true;             
          return;
        }
        
        const uniqueDataMap = new Map();
        data.forEach(item => {
          if (item.time && item.time > 0) {
            uniqueDataMap.set(item.time, item);
          }
        });

        const validData = Array.from(uniqueDataMap.values())
        .filter(item => {
            if (!item.time || item.time === 0) return false;
            if (Number(item.time) < 1577836800) return false;
            return true;
            })
        .sort((a, b) => a.time - b.time)
        .map(item => ({
          ...item,
          time: Number(item.time) as UTCTimestamp,
          open: Number(item.open),
          high: Number(item.high),
          low: Number(item.low),
          close: Number(item.close),
        }));

        if (validData.length === 0) return;

        try {
          candlestickSeriesRef.current.setData(validData);
        } catch (e) {
          console.error("Lỗi SetData:", e);
        }
        
        if (isInitialLoad.current) {
          chartRef.current?.timeScale().fitContent();
          isInitialLoad.current = false;
        }
    }
  }, [data]);

  useEffect(() => {
    if(markersPluginRef.current) {
      try {
        const sortedMarkers = [...markers].sort((a, b) => a.time - b.time);
        markersPluginRef.current.setMarkers(sortedMarkers);
        //console.log("draw: ", markers.length)
      } catch (error) {
        console.error("Lỗi vẽ Marker:", error);
      }
    }
  }, [markers]);

  return <div ref={chartContainerRef} className="w-full h-full" />;
};