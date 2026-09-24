// The chat screen: header with partner info, message list, input box
// and the Next / Stop / Report buttons.
// Messages are rendered as plain text by React, which escapes HTML for us.
// Never use dangerouslySetInnerHTML here.

import { useEffect, useRef, useState } from "react";
import { countryName, flag } from "../countries.js";

const REPORT_REASONS = [
  { value: "spam", label: "Spam or ads" },
  { value: "abusive", label: "Abusive or rude" },
  { value: "sexual", label: "Unwanted sexual content" },
  { value: "underage", label: "Seems under 18" },
  { value: "other", label: "Something else" },
];

export default function ChatRoom({
  status,
  partner,
  messages,
  partnerTyping,
  onSend,
  onTyping,
  onNext,
  onStop,
  onReport,
}) {
  const [text, setText] = useState("");
  const [showReport, setShowReport] = useState(false);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const partnerLeft = status === "partner_left";

  // Auto-scroll to the newest message (and when the typing bubble appears).
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, partnerTyping, partnerLeft]);

  // Focus the input when a new chat starts.
  useEffect(() => {
    inputRef.current?.focus();
  }, [partner]);

  function handleSubmit(event) {
    event.preventDefault();
    if (onSend(text)) setText("");
  }

  function handleChange(event) {
    setText(event.target.value);
    if (event.target.value.trim()) onTyping();
  }

  function handleReport(reason) {
    setShowReport(false);
    onReport(reason);
  }

  return (
    <main className="chat">
      <header className="chat-header">
        <div className="partner">
          <div className="avatar" aria-hidden="true">
            {partner?.username?.[0]?.toUpperCase() || "?"}
          </div>
          <div>
            <div className="partner-name">{partner?.username || "Stranger"}</div>
            {partner && (
              <div className="partner-meta">
                {partner.age} · {flag(partner.country)} {countryName(partner.country)}
              </div>
            )}
          </div>
        </div>
        <div className="chat-actions">
          <button className="btn btn-small" onClick={onNext} title="Skip to a new stranger">
            Next
          </button>
          <button className="btn btn-small" onClick={onStop} title="Back to the home screen">
            Stop
          </button>
          <button
            className="btn btn-small btn-danger"
            onClick={() => setShowReport((v) => !v)}
            disabled={partnerLeft}
            title="Report this stranger"
          >
            Report
          </button>
        </div>
      </header>

      {showReport && (
        <div className="report-menu">
          <span>Why are you reporting {partner?.username}?</span>
          <div className="report-reasons">
            {REPORT_REASONS.map((r) => (
              <button key={r.value} className="btn btn-small" onClick={() => handleReport(r.value)}>
                {r.label}
              </button>
            ))}
            <button className="btn btn-small btn-ghost" onClick={() => setShowReport(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}

      <section className="messages" aria-live="polite">
        <p className="system">
          You're now chatting with {partner?.username || "a stranger"}. Say hi! 👋
        </p>

        {messages.map((m) => (
          <div key={m.id} className={`bubble ${m.from === "me" ? "bubble-me" : "bubble-them"}`}>
            {m.text}
          </div>
        ))}

        {partnerTyping && !partnerLeft && (
          <div className="bubble bubble-them typing" aria-label="Stranger is typing">
            <span />
            <span />
            <span />
          </div>
        )}

        {partnerLeft && (
          <div className="left-box">
            <p>Stranger has disconnected</p>
            <button className="btn btn-primary" onClick={onNext}>
              Find new stranger
            </button>
          </div>
        )}

        <div ref={bottomRef} />
      </section>

      {partnerTyping && !partnerLeft && <p className="typing-text">Stranger is typing...</p>}

      <form className="composer" onSubmit={handleSubmit}>
        <input
          ref={inputRef}
          type="text"
          value={text}
          maxLength={1000}
          placeholder={partnerLeft ? "Chat ended" : "Type a message..."}
          disabled={partnerLeft}
          onChange={handleChange}
          aria-label="Message"
        />
        <button type="submit" className="btn btn-primary" disabled={partnerLeft || !text.trim()}>
          Send
        </button>
      </form>
    </main>
  );
}
