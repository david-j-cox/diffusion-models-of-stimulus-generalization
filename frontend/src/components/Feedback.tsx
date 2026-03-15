import type { FC } from "react";

interface FeedbackProps {
  feedbackType: string | null;
  message: string;
  visible: boolean;
}

const Feedback: FC<FeedbackProps> = ({ feedbackType, message, visible }) => {
  if (!visible || !feedbackType || feedbackType === "none") return null;

  return (
    <div className="feedback-text" aria-live="polite">
      {message}
    </div>
  );
};

export default Feedback;
