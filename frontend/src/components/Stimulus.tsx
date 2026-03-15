import type { FC } from "react";

interface StimulusProps {
  angleDegrees: number; // 20-160
  sizePx?: number;
  lineColor?: string;
  bgColor?: string;
}

/**
 * Renders an oriented line inside a circle using SVG.
 * The angle is measured from horizontal (0 = horizontal, 90 = vertical).
 */
const Stimulus: FC<StimulusProps> = ({
  angleDegrees,
  sizePx = 200,
  lineColor = "#ffffff",
  bgColor = "#808080",
}) => {
  const cx = sizePx / 2;
  const cy = sizePx / 2;
  const radius = sizePx * 0.42; // Line extends almost to circle edge
  const circleRadius = sizePx * 0.45;

  // Convert angle to radians. Angle 0 = horizontal, 90 = vertical.
  // SVG: 0 degrees points right, positive angle goes clockwise.
  // We want: 0 deg = horizontal, 90 deg = vertical.
  const rad = (angleDegrees * Math.PI) / 180;
  const dx = Math.cos(rad) * radius;
  const dy = -Math.sin(rad) * radius; // Negative because SVG y-axis is inverted

  return (
    <svg
      width={sizePx}
      height={sizePx}
      viewBox={`0 0 ${sizePx} ${sizePx}`}
      style={{ display: "block" }}
    >
      {/* Background circle */}
      <circle
        cx={cx}
        cy={cy}
        r={circleRadius}
        fill={bgColor}
        stroke="#999"
        strokeWidth={1.5}
      />
      {/* Oriented line */}
      <line
        x1={cx - dx}
        y1={cy - dy}
        x2={cx + dx}
        y2={cy + dy}
        stroke={lineColor}
        strokeWidth={3}
        strokeLinecap="round"
        shapeRendering="geometricPrecision"
      />
    </svg>
  );
};

export default Stimulus;
