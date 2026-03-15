import type { FC } from "react";

interface ConsentScreenProps {
  onAgree: () => void;
}

const ConsentScreen: FC<ConsentScreenProps> = ({ onAgree }) => {
  return (
    <div className="screen-container">
      <h1>Informed Consent</h1>

      <h2>Study Title</h2>
      <p>Stimulus Generalization in Humans: An Online Behavioral Study</p>

      <h2>Purpose</h2>
      <p>
        You are invited to participate in a research study investigating how
        people learn to respond to visual stimuli. The purpose of this study is
        to understand how responding to one stimulus generalizes to similar
        stimuli.
      </p>

      <h2>Procedures</h2>
      <p>
        If you agree to participate, you will be asked to view oriented lines on
        your screen and press the SPACEBAR when you see certain lines. The
        experiment consists of several phases including practice, training, and
        test phases. The entire session should take approximately 20-30 minutes.
      </p>

      <h2>Risks and Benefits</h2>
      <p>
        There are no known risks associated with participation in this study
        beyond those encountered in everyday life. You will earn points during
        the experiment. There are no direct benefits to you, but your
        participation will contribute to scientific understanding of learning and
        generalization.
      </p>

      <h2>Confidentiality</h2>
      <p>
        Your responses will be anonymous. We will not collect any personally
        identifiable information. Data will be stored securely and used only for
        research purposes.
      </p>

      <h2>Voluntary Participation</h2>
      <p>
        Your participation is entirely voluntary. You may withdraw at any time
        without penalty by closing the browser window. However, you must
        complete the experiment to receive your completion code.
      </p>

      <h2>Contact</h2>
      <p>
        If you have questions about this study, please contact the research team
        at the email address provided in your recruitment materials.
      </p>

      <hr style={{ margin: "1.5rem 0", border: "none", borderTop: "1px solid #ccc" }} />

      <p>
        By clicking the button below, you confirm that you have read and
        understood the information above and voluntarily agree to participate in
        this study. You confirm that you are at least 18 years of age.
      </p>

      <button className="btn-primary" onClick={onAgree}>
        I Agree &mdash; Begin Study
      </button>
    </div>
  );
};

export default ConsentScreen;
