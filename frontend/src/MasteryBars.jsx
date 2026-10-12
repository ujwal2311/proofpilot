import { UI } from "./labels.js";

// Always visible, because the point of the project is that a student can see what the system
// thinks they know. Iterates the mapping rather than a fixed list of three, so the fourth skill
// appears on its own when the Translate stage arrives in M2.
export function MasteryBars({ mastery }) {
  const skills = Object.entries(mastery ?? {});
  if (!skills.length) return null;
  return (
    <section className="mastery" aria-label={UI.mastery}>
      <h2>{UI.mastery}</h2>
      <ul>
        {skills.map(([skill, value]) => (
          <li key={skill}>
            <span className="skill">{skill}</span>
            <span className="track">
              {/* aria-* so the bar is not purely visual: a screen reader and a projector at the
                  back of a room have the same problem, which is that the fill is hard to read. */}
              <span
                className="fill"
                style={{ width: `${Math.round(value * 100)}%` }}
                role="progressbar"
                aria-valuenow={Math.round(value * 100)}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={skill}
              />
            </span>
            <span className="percent">{Math.round(value * 100)}%</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
