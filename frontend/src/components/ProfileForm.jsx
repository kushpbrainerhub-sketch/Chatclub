// Home screen: your profile + optional partner filters (SPEC sections 4 and 5).
// The same rules are checked again on the backend, which never trusts us.

import { useState } from "react";
import { COUNTRIES, countryName, flag } from "../countries.js";
import CountrySelect from "./CountrySelect.jsx";

const USERNAME_PATTERN = /^[A-Za-z0-9_. ]{3,20}$/;
const VALID_CODES = new Set(COUNTRIES.map((c) => c.code));

// Returns an object like { age: "Age must be..." }. Empty object = all good.
function validate(profile, filters, agreed) {
  const errors = {};
  const username = profile.username.trim();
  const age = Number(profile.age);
  const min = Number(filters.age_min);
  const max = Number(filters.age_max);

  if (!USERNAME_PATTERN.test(username)) {
    errors.username = "3-20 characters: letters, numbers, _ . or space";
  }
  if (!Number.isInteger(age) || age < 18 || age > 99) {
    errors.age = "You must be 18 to 99 years old";
  }
  if (!VALID_CODES.has(profile.country)) {
    errors.country = "Please choose your country";
  }
  if (profile.gender !== "male" && profile.gender !== "female") {
    errors.gender = "Please choose your gender";
  }
  if (!Number.isInteger(min) || !Number.isInteger(max) || min < 18 || max > 99 || min > max) {
    errors.ageRange = "Age range must be between 18 and 99, min not above max";
  }
  if (!agreed) {
    errors.agreed = "Please confirm to continue";
  }
  return errors;
}

export default function ProfileForm({
  profile,
  setProfile,
  filters,
  setFilters,
  onStart,
  connected,
  onlineCount,
}) {
  const [agreed, setAgreed] = useState(false);
  const [errors, setErrors] = useState({});

  const partnerGender =
    profile.gender === "male" ? "Female" : profile.gender === "female" ? "Male" : null;

  function updateProfile(field, value) {
    setProfile((old) => ({ ...old, [field]: value }));
  }

  function updateFilters(field, value) {
    setFilters((old) => ({ ...old, [field]: value }));
  }

  function addCountry(code) {
    if (code && !filters.countries.includes(code)) {
      updateFilters("countries", [...filters.countries, code]);
    }
  }

  function removeCountry(code) {
    updateFilters("countries", filters.countries.filter((c) => c !== code));
  }

  function handleSubmit(event) {
    event.preventDefault();
    const found = validate(profile, filters, agreed);
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    onStart(
      {
        username: profile.username.trim(),
        age: Number(profile.age),
        country: profile.country,
        gender: profile.gender,
      },
      {
        countries: filters.countries,
        age_min: Number(filters.age_min),
        age_max: Number(filters.age_max),
      }
    );
  }

  return (
    <main className="home">
      <header className="home-header">
        <h1>
          <span className="brand-mark" aria-hidden="true"><svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M21 11.5a8.4 8.4 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7a8.4 8.4 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.4 8.4 0 0 1 3.8-.9h.5a8.5 8.5 0 0 1 8 8v.5Z" /><path d="M8 11h8M8 15h4" /></svg></span> Chatclub
        </h1>
        <p className="tagline">Free, anonymous text chat with a random stranger.</p>
        <p className="online">
          <span className={`dot ${connected ? "dot-on" : "dot-off"}`} />
          {connected ? `${onlineCount} online now` : "Connecting to server..."}
        </p>
      </header>

      <form className="card" onSubmit={handleSubmit} noValidate>
        <div className="section-heading"><div><h2>About you</h2><p>A little introduction goes a long way.</p></div></div>

        <label className="field">
          <span>Username</span>
          <input
            type="text"
            value={profile.username}
            maxLength={20}
            placeholder="e.g. night_owl"
            onChange={(e) => updateProfile("username", e.target.value)}
          />
          {errors.username && <small className="error">{errors.username}</small>}
        </label>

        <div className="row">
          <label className="field">
            <span>Age</span>
            <input
              type="number"
              min={18}
              max={99}
              value={profile.age}
              placeholder="18+"
              onChange={(e) => updateProfile("age", e.target.value)}
            />
            {errors.age && <small className="error">{errors.age}</small>}
          </label>

          <CountrySelect label="Country" value={profile.country} onChange={(value) => updateProfile("country", value)} placeholder="Choose your country" error={errors.country} />
        </div>

        <fieldset className="field">
          <legend>Gender</legend>
          <div className="segmented">
            {["male", "female"].map((g) => (
              <label key={g} className={profile.gender === g ? "selected" : ""}>
                <input
                  type="radio"
                  name="gender"
                  value={g}
                  checked={profile.gender === g}
                  onChange={() => updateProfile("gender", g)}
                />
                {g === "male" ? "Male" : "Female"}
              </label>
            ))}
          </div>
          {errors.gender && <small className="error">{errors.gender}</small>}
        </fieldset>

        <div className="section-heading section-divider"><div><h2>Who you want to meet</h2><p>Find a conversation that feels right.</p></div></div>

        {partnerGender && (
          <p className="note">
            You'll be matched with: <strong>{partnerGender}</strong>
          </p>
        )}

        <div className="field">
          <span className="label">Partner age</span>
          <div className="row tight">
            <input
              type="number"
              min={18}
              max={99}
              aria-label="Minimum partner age"
              value={filters.age_min}
              onChange={(e) => updateFilters("age_min", e.target.value)}
            />
            <span className="muted">to</span>
            <input
              type="number"
              min={18}
              max={99}
              aria-label="Maximum partner age"
              value={filters.age_max}
              onChange={(e) => updateFilters("age_max", e.target.value)}
            />
          </div>
          {errors.ageRange && <small className="error">{errors.ageRange}</small>}
        </div>

        <div className="field">
          <CountrySelect label="Partner country" value="" onChange={addCountry} excluded={filters.countries} placeholder={filters.countries.length === 0 ? "Any country · choose to filter" : "Add another country..."} />
          <div className="chips">
            {filters.countries.length === 0 ? (
              <span className="chip chip-any">🌍 Any country</span>
            ) : (
              <>
                {filters.countries.map((code) => (
                  <button
                    type="button"
                    key={code}
                    className="chip"
                    onClick={() => removeCountry(code)}
                    title="Remove"
                  >
                    {flag(code)} {countryName(code)} <span aria-hidden="true">×</span>
                  </button>
                ))}
                <button type="button" className="chip chip-clear" onClick={() => updateFilters("countries", [])}>
                  Any country
                </button>
              </>
            )}
          </div>
        </div>

        <label className="checkbox">
          <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} />
          <span>
            I confirm I am 18 or older and agree to be respectful (<a href="/terms">Terms</a>)
          </span>
        </label>
        {errors.agreed && <small className="error">{errors.agreed}</small>}

        <button type="submit" className="btn btn-primary btn-big" disabled={!connected}>
          Start Chatting <span aria-hidden="true">↗</span>
        </button>

        <p className="safety">
          Be respectful. Don't share personal info like phone number or address.
        </p>
      </form>

      <footer className="site-footer">
        <a href="/about">About &amp; FAQ</a>
        <a href="/privacy">Privacy</a>
        <a href="/terms">Terms</a>
      </footer>
    </main>
  );
}
