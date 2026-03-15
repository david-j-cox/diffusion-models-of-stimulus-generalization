import { useEffect, useState } from "react";
import type { FC } from "react";
import { isMobile, hasKeyboard } from "../utils/browser";

interface EligibilityScreenProps {
  onPass: () => void;
}

const EligibilityScreen: FC<EligibilityScreenProps> = ({ onPass }) => {
  const [mobile, setMobile] = useState(false);
  const [keyboard, setKeyboard] = useState(true);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    setMobile(isMobile());
    setKeyboard(hasKeyboard());
    setChecked(true);
  }, []);

  const eligible = !mobile && keyboard;

  if (!checked) return null;

  return (
    <div className="screen-container">
      <h1>Device Check</h1>

      <p>
        This experiment requires a desktop or laptop computer with a physical
        keyboard. Please ensure you are not using a mobile phone or tablet.
      </p>

      <div style={{ margin: "1.5rem 0" }}>
        <p>
          <strong>Device type:</strong>{" "}
          {mobile ? (
            <span style={{ color: "#dc2626" }}>
              Mobile device detected. Please switch to a desktop or laptop computer.
            </span>
          ) : (
            <span style={{ color: "#16a34a" }}>Desktop/laptop detected.</span>
          )}
        </p>
        <p>
          <strong>Keyboard:</strong>{" "}
          {keyboard ? (
            <span style={{ color: "#16a34a" }}>Keyboard available.</span>
          ) : (
            <span style={{ color: "#dc2626" }}>
              No keyboard detected. A physical keyboard is required.
            </span>
          )}
        </p>
      </div>

      {eligible ? (
        <>
          <p>Your setup meets the requirements. You may proceed.</p>
          <button className="btn-primary" onClick={onPass}>
            Continue
          </button>
        </>
      ) : (
        <p style={{ color: "#dc2626", fontWeight: 600 }}>
          Unfortunately, your current device does not meet the requirements for
          this experiment. Please try again on a desktop or laptop computer with
          a physical keyboard.
        </p>
      )}
    </div>
  );
};

export default EligibilityScreen;
