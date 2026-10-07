import { useEffect, useRef, useState } from "react";
import { AreaSeries, CandlestickSeries, ColorType, CrosshairMode, createChart, createSeriesMarkers } from "lightweight-charts";
import type { IChartApi, ISeriesApi, Time, CandlestickData, AreaData, WhitespaceData } from "lightweight-charts";
import type { ActivityPoint } from "../types";

const price = (v: number) => v.toLocaleString("id-ID", { maximumFractionDigits: 0 });
export function OverviewPriceChart({ points, dark = false, graphiteIce = false, height = 300, symbol }: { points: ActivityPoint[]; dark?: boolean; graphiteIce?: boolean; height?: number; symbol: string }) {
  const host = useRef<HTMLDivElement>(null);
  const api = useRef<IChartApi | null>(null);
  const [mode, setMode] = useState<"area" | "candle">("area");
  const [legend, setLegend] = useState("");
  useEffect(() => {
    if (!host.current) return;
    const ordered = [...new Map(points.map(p => [p.date, p])).values()].sort((a,b) => a.date.localeCompare(b.date));
    const valid = ordered.filter(p => p.close !== null && Number.isFinite(p.close));
    const last = valid.at(-1);
    const initial = last ? `Harga terakhir · Rp ${price(last.close!)}` : "Harga belum tersedia";
    setLegend(initial);
    const accent = graphiteIce ? "#67e8f9" : "#ec176d";
    const label = graphiteIce ? "#2c3d52" : "#ec176d";
    const chart = createChart(host.current, {
      autoSize: true, height,
      layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor: dark ? "#b8c5d6" : "#738095", attributionLogo: true },
      grid: { vertLines: { visible: false }, horzLines: { color: dark ? "#252c3e" : "#edf0f5" } },
      rightPriceScale: { borderVisible: false }, timeScale: { borderVisible: false, rightOffset: 8 },
      crosshair: { mode: CrosshairMode.Normal, horzLine: { color: accent, labelBackgroundColor: label }, vertLine: { color: "#9199ae", labelBackgroundColor: "#343e56" } },
      handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: false },
      handleScale: { mouseWheel: true, pinch: true, axisPressedMouseMove: true },
    });
    api.current = chart;
    const format = { type: "price" as const, precision: 0, minMove: 1 };
    const series = mode === "area"
      ? chart.addSeries(AreaSeries, { lineColor: accent, topColor: graphiteIce ? "rgba(103,232,249,.22)" : "rgba(236,23,109,.24)", bottomColor: graphiteIce ? "rgba(103,232,249,0)" : "rgba(236,23,109,0)", lineWidth: 2, priceFormat: format, lastValueVisible: false, priceLineVisible: false })
      : chart.addSeries(CandlestickSeries, { upColor: graphiteIce ? "#67e8f9" : "#129e80", downColor: graphiteIce ? "#ff8e9c" : "#ec176d", borderVisible: false, wickUpColor: graphiteIce ? "#67e8f9" : "#129e80", wickDownColor: graphiteIce ? "#ff8e9c" : "#ec176d", priceFormat: format, lastValueVisible: false, priceLineVisible: false });
    const data: (AreaData<Time> | CandlestickData<Time> | WhitespaceData<Time>)[] = ordered.map(p => {
      const time = p.date as Time;
      if (p.close === null || !Number.isFinite(p.close)) return { time };
      if (mode === "area") return { time, value: p.close };
      if ([p.open,p.high,p.low].some(v => v == null || !Number.isFinite(v))) return { time };
      return { time, open: p.open!, high: p.high!, low: p.low!, close: p.close };
    });
    // The discriminated series is matched to the data above; missing prices remain whitespace.
    if (mode === "area") (series as ISeriesApi<"Area">).setData(data as (AreaData<Time> | WhitespaceData<Time>)[]);
    else (series as ISeriesApi<"Candlestick">).setData(data as (CandlestickData<Time> | WhitespaceData<Time>)[]);
    if (last) series.createPriceLine({ price: last.close!, color: accent, axisLabelColor: graphiteIce ? label : accent, axisLabelTextColor: "#ffffff", lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: "Terakhir" });
    if (last) createSeriesMarkers(series, [{ time: last.date as Time, position: "atPriceMiddle", price: last.close!, shape: "circle", color: accent, size: 1 }]);
    chart.subscribeCrosshairMove(event => {
      const bar = event.seriesData.get(series);
      if (!event.time || !bar || !("value" in bar || "close" in bar)) { setLegend(initial); return; }
      const close = "value" in bar ? bar.value : bar.close;
      const cursor = event.point ? series.coordinateToPrice(event.point.y) : null;
      setLegend(`${String(event.time)} · Harga Rp ${price(close)}${cursor === null ? "" : ` · Kursor Rp ${price(cursor)}`}`);
    });
    chart.timeScale().fitContent();
    return () => { api.current = null; chart.remove(); };
  }, [points, dark, graphiteIce, height, mode]);
  function zoom(factor: number) {
    const scale = api.current?.timeScale(); const range = scale?.getVisibleLogicalRange();
    if (scale && range) { const middle = (range.from + range.to) / 2; const half = (range.to-range.from)*factor/2; scale.setVisibleLogicalRange({ from: middle-half, to: middle+half }); }
  }
  return <section className="ov-chart" aria-label={`Grafik harga interaktif ${symbol}`}>
    <div className="ov-chart-bar"><strong>{symbol} <span>/ IDR</span></strong><div className="ov-chart-controls">
      <button aria-pressed={mode === "area"} onClick={() => setMode("area")}>Area</button><button aria-pressed={mode === "candle"} onClick={() => setMode("candle")}>Candle</button>
      <button aria-label="Perbesar grafik" onClick={() => zoom(.65)}>+</button><button aria-label="Perkecil grafik" onClick={() => zoom(1.5)}>−</button><button onClick={() => api.current?.timeScale().fitContent()}>Reset</button>
    </div></div>
    <div className="ov-chart-legend" role="status">{legend}</div>
    <div ref={host} className="ov-chart-canvas" style={{height}} />
    <div className="ov-chart-foot"><span>Geser untuk jelajahi · Scroll untuk zoom</span><a href="https://www.tradingview.com/" target="_blank" rel="noreferrer">Charts by TradingView</a></div>
  </section>;
}
