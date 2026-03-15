import type { FC } from "react";

interface ProgressBarProps {
  current: number;
  total: number;
  visible: boolean;
}

const ProgressBar: FC<ProgressBarProps> = ({ current, total, visible }) => {
  if (!visible || total === 0) return null;

  const pct = Math.min(100, (current / total) * 100);

  return (
    <div className="progress-bar-container">
      <div
        className="progress-bar-fill"
        style={{ width: `${pct}%` }}
        role="progressbar"
        aria-valuenow={current}
        aria-valuemin={0}
        aria-valuemax={total}
      />
    </div>
  );
};

export default ProgressBar;
