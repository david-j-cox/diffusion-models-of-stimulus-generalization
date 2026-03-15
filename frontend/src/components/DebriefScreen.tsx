import type { FC } from "react";

interface DebriefScreenProps {
  onContinue: () => void;
  totalPoints: number;
}

const DebriefScreen: FC<DebriefScreenProps> = ({
  onContinue,
  totalPoints,
}) => {
  return (
    <div className="screen-container">
      <h1>Experiment Complete</h1>

      <p>
        Thank you for completing the experiment! You earned a total of{" "}
        <strong>{totalPoints} points</strong>.
      </p>

      <h2>About This Study</h2>
      <p>
        This study investigates stimulus generalization, a fundamental process
        in learning. After being trained to respond to a specific line
        orientation (the target), we measured how your responding generalized to
        other, similar orientations. This pattern of generalization helps
        researchers understand how organisms categorize and discriminate between
        stimuli.
      </p>

      <p>
        Stimulus generalization is an important process in many areas of
        psychology, including perception, learning, anxiety, and decision-making.
        By studying the shape of generalization gradients in healthy
        participants, we can better understand both normal cognition and clinical
        conditions where generalization may be altered.
      </p>

      <p>
        Your data will be analyzed anonymously along with data from other
        participants. No individual responses will be identifiable.
      </p>

      <p>
        If you have any questions about this study, please contact the research
        team using the information provided in your recruitment materials.
      </p>

      <button className="btn-primary" onClick={onContinue}>
        Get Completion Code
      </button>
    </div>
  );
};

export default DebriefScreen;
