import { useState } from "react";
import type { FC } from "react";
import Stimulus from "./Stimulus";

interface InstructionsScreenProps {
  onComplete: () => void;
  targetAngle: number; // rendered angle in degrees for the example
}

interface PageDef {
  title: string;
  content: string;
  showExample?: boolean;
}

const PAGES: PageDef[] = [
  {
    title: "Welcome",
    content: `Thank you for participating in this study. In this experiment, you will see lines of different orientations displayed on the screen. Your task is to learn which line orientation is the "target" and press the SPACEBAR when you see it.`,
  },
  {
    title: "How It Works",
    content: `On each trial, a fixation cross (+) will appear briefly, followed by an oriented line. If you believe the line is the target, press the SPACEBAR as quickly as possible while it is still on screen. If you do not think it is the target, simply wait for the next trial.`,
  },
  {
    title: "Earning Points",
    content: `When you correctly press SPACEBAR for the target line, you will earn points. The message "+1 Point!" will appear on screen. Try to earn as many points as possible. You will NOT earn points for pressing on non-target lines.`,
  },
  {
    title: "Example Stimulus",
    content: `Below is an example of what the oriented line looks like. The actual target orientation will be revealed during practice. Pay attention to the angle of the line.`,
    showExample: true,
  },
  {
    title: "Important Tips",
    content: `Please keep this browser window in focus throughout the experiment. Avoid switching tabs or windows. Try to respond as quickly and accurately as possible. The experiment has several phases and will take approximately 20-30 minutes.`,
  },
];

const InstructionsScreen: FC<InstructionsScreenProps> = ({
  onComplete,
  targetAngle,
}) => {
  const [page, setPage] = useState(0);
  const current = PAGES[page];
  const isLast = page === PAGES.length - 1;

  return (
    <div className="screen-container">
      <h1>Instructions ({page + 1}/{PAGES.length})</h1>
      <h2>{current.title}</h2>
      <p>{current.content}</p>

      {current.showExample && (
        <div style={{ display: "flex", justifyContent: "center", margin: "1.5rem 0" }}>
          <Stimulus angleDegrees={targetAngle} sizePx={180} />
        </div>
      )}

      <div className="nav-buttons">
        {page > 0 && (
          <button className="btn-secondary" onClick={() => setPage(page - 1)}>
            Back
          </button>
        )}
        {isLast ? (
          <button className="btn-primary" onClick={onComplete}>
            Start Experiment
          </button>
        ) : (
          <button className="btn-primary" onClick={() => setPage(page + 1)}>
            Next
          </button>
        )}
      </div>
    </div>
  );
};

export default InstructionsScreen;
