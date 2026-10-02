interface Point {
  x: string;
  y: number | null;
  flag?: boolean;
}

export function SimpleLineChart({
  points,
  height = 260,
  reference,
  referenceLabel,
  suffix = "",
  emptyLabel = "No data available"
}: {
  points: Point[];
  height?: number;
  reference?: number;
  referenceLabel?: string;
  suffix?: string;
  emptyLabel?: string;
}) {
  const usable = points.filter(
    (point): point is Point & { y: number } =>
      point.y !== null && Number.isFinite(point.y)
  );

  if (usable.length < 2) {
    return (
      <div className="chart-empty">
        <span>◇</span>
        <p>{emptyLabel}</p>
      </div>
    );
  }

  const width = 900;
  const padX = 42;
  const padTop = 24;
  const padBottom = 34;

  const values = usable.map((point) => point.y);
  if (reference !== undefined) values.push(reference);

  let min = Math.min(...values);
  let max = Math.max(...values);

  if (min === max) {
    min -= 1;
    max += 1;
  }

  const padY = (max - min) * 0.12;
  min -= padY;
  max += padY;

  const chartHeight = height - padTop - padBottom;
  const chartWidth = width - padX * 2;

  const xy = usable.map((point, index) => {
    const x =
      padX +
      (index / Math.max(1, usable.length - 1)) * chartWidth;
    const y =
      padTop +
      ((max - point.y) / (max - min)) * chartHeight;

    return { ...point, px: x, py: y };
  });

  const path = xy
    .map(
      (point, index) =>
        `${index === 0 ? "M" : "L"} ${point.px.toFixed(
          2
        )} ${point.py.toFixed(2)}`
    )
    .join(" ");

  const refY =
    reference === undefined
      ? null
      : padTop +
        ((max - reference) / (max - min)) * chartHeight;

  const yTicks = Array.from({ length: 4 }).map((_, index) => {
    const ratio = index / 3;
    const value = max - (max - min) * ratio;
    const y = padTop + chartHeight * ratio;
    return { value, y };
  });

  const firstDate = usable[0].x;
  const midDate = usable[Math.floor(usable.length / 2)].x;
  const lastDate = usable[usable.length - 1].x;

  return (
    <div className="line-chart">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="Time series chart"
      >
        {yTicks.map((tick, index) => (
          <g key={index}>
            <line
              x1={padX}
              y1={tick.y}
              x2={width - padX}
              y2={tick.y}
              className="chart-grid-line"
            />
            <text
              x={padX - 8}
              y={tick.y + 4}
              textAnchor="end"
              className="chart-axis-label"
            >
              {tick.value.toFixed(2)}
              {suffix}
            </text>
          </g>
        ))}

        {refY !== null && (
          <g>
            <line
              x1={padX}
              y1={refY}
              x2={width - padX}
              y2={refY}
              className="chart-reference-line"
            />
            <text
              x={width - padX}
              y={refY - 7}
              textAnchor="end"
              className="chart-reference-label"
            >
              {referenceLabel ?? `Reference ${reference}`}
            </text>
          </g>
        )}

        <path d={path} className="chart-line-path" />

        {xy
          .filter((point) => point.flag)
          .map((point) => (
            <g key={`${point.x}-${point.y}`}>
              <circle
                cx={point.px}
                cy={point.py}
                r="7"
                className="chart-flag-halo"
              />
              <circle
                cx={point.px}
                cy={point.py}
                r="3.6"
                className="chart-flag-dot"
              />
            </g>
          ))}

        <text
          x={padX}
          y={height - 8}
          textAnchor="start"
          className="chart-axis-label"
        >
          {shortDate(firstDate)}
        </text>
        <text
          x={width / 2}
          y={height - 8}
          textAnchor="middle"
          className="chart-axis-label"
        >
          {shortDate(midDate)}
        </text>
        <text
          x={width - padX}
          y={height - 8}
          textAnchor="end"
          className="chart-axis-label"
        >
          {shortDate(lastDate)}
        </text>
      </svg>
    </div>
  );
}

function shortDate(value: string) {
  const date = new Date(`${value}T00:00:00`);

  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short"
  }).format(date);
}
