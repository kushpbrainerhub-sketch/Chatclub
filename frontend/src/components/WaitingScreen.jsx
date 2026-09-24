// "Looking for someone..." screen. After 30 seconds we show a hint
// to widen the filters (we never change the filters automatically).

import { useEffect, useState } from "react";
import { countryName } from "../countries.js";

const HINT_AFTER_SECONDS = 30;

export default function WaitingScreen({ filters, gender, onCancel }) {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  const lookingFor = gender === "male" ? "a woman" : "a man";
  const where =
    filters.countries.length === 0
      ? "from any country"
      : `from ${filters.countries.map(countryName).join(", ")}`;

  return (
    <main className="center-screen">
      <div className="card waiting">
        <div className="spinner" aria-hidden="true" />
        <h2>Looking for someone...</h2>
        <p className="muted">
          Searching for {lookingFor} aged {filters.age_min}–{filters.age_max} {where}
        </p>
        <p className="timer">{seconds}s</p>

        {seconds >= HINT_AFTER_SECONDS && (
          <p className="note">
            No match yet. Try widening your age range or country filter.
          </p>
        )}

        <button className="btn" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </main>
  );
}
