import type { FC } from "react";

interface CompletionScreenProps {
  completionCode: string;
}

const CompletionScreen: FC<CompletionScreenProps> = ({ completionCode }) => {
  return (
    <div className="screen-container" style={{ textAlign: "center" }}>
      <h1>Thank You!</h1>

      <p>Your participation is complete. Please copy the completion code below and paste it into your recruitment platform to receive credit.</p>

      <div style={{ margin: "2rem 0" }}>
        <div className="completion-code">{completionCode}</div>
      </div>

      <p style={{ fontSize: "0.95rem", color: "#666" }}>
        You may now close this window. If you need to retrieve this code later,
        please contact the research team.
      </p>
    </div>
  );
};

export default CompletionScreen;
