// Custom React hook that owns the WebSocket connection (SPEC section 10).
// Components never touch the socket directly: they read state from this hook
// and call its functions (join, sendMessage, next, leave, report...).

import { useCallback, useEffect, useRef, useState } from "react";

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws";
const TYPING_SHOW_MS = 2000; // how long "Stranger is typing..." stays visible
const TYPING_SEND_MS = 1000; // send "typing" at most once per second
const KICKED_CLOSE_CODE = 4000; // server closed us after too many reports

let nextMessageId = 1; // unique keys for React lists

export function useChatSocket() {
  const [connected, setConnected] = useState(false);
  const [status, setStatus] = useState("idle"); // idle | waiting | chatting | partner_left
  const [messages, setMessages] = useState([]);
  const [partner, setPartner] = useState(null);
  const [onlineCount, setOnlineCount] = useState(0);
  const [partnerTyping, setPartnerTyping] = useState(false);
  const [toast, setToast] = useState(null); // { kind: "error" | "info", text }

  const wsRef = useRef(null);
  const typingTimerRef = useRef(null);
  const toastTimerRef = useRef(null);
  const lastTypingSentRef = useRef(0);

  const showToast = useCallback((kind, text) => {
    setToast({ kind, text });
    clearTimeout(toastTimerRef.current);
    toastTimerRef.current = setTimeout(() => setToast(null), 4000);
  }, []);

  // ---------- connect (and reconnect once if the connection drops) ----------
  useEffect(() => {
    let stopped = false; // true when the component unmounts
    let retriedOnce = false;

    function handleEvent(data) {
      switch (data.type) {
        case "waiting":
          setStatus("waiting");
          setPartner(null);
          setMessages([]);
          setPartnerTyping(false);
          break;
        case "matched":
          setStatus("chatting");
          setPartner(data.partner);
          setMessages([]);
          setPartnerTyping(false);
          break;
        case "message":
          setPartnerTyping(false);
          setMessages((old) => [...old, { id: nextMessageId++, from: "partner", text: data.text }]);
          break;
        case "partner_typing":
          setPartnerTyping(true);
          clearTimeout(typingTimerRef.current);
          typingTimerRef.current = setTimeout(() => setPartnerTyping(false), TYPING_SHOW_MS);
          break;
        case "partner_left":
          setStatus("partner_left");
          setPartnerTyping(false);
          break;
        case "online_count":
          setOnlineCount(data.count);
          break;
        case "error":
          showToast("error", data.message);
          break;
        default:
          console.warn("Unknown event from server:", data);
      }
    }

    function connect() {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        retriedOnce = false; // connection works again, allow another retry later
      };

      ws.onmessage = (event) => {
        try {
          handleEvent(JSON.parse(event.data));
        } catch (err) {
          console.error("Bad message from server", err);
        }
      };

      ws.onclose = (event) => {
        if (stopped) return;
        setConnected(false);
        // Any chat in progress is gone when the socket closes.
        setStatus("idle");
        setPartner(null);
        setPartnerTyping(false);

        if (event.code === KICKED_CLOSE_CODE) return; // don't come back after a kick
        if (!retriedOnce) {
          retriedOnce = true;
          showToast("error", "Connection lost. Reconnecting...");
          setTimeout(() => !stopped && connect(), 1000);
        } else {
          showToast("error", "Can't reach the server. Refresh the page to try again.");
        }
      };
    }

    connect();

    return () => {
      stopped = true;
      clearTimeout(typingTimerRef.current);
      clearTimeout(toastTimerRef.current);
      wsRef.current?.close();
    };
  }, [showToast]);

  // ---------- actions the UI can call ----------

  const send = useCallback(
    (data) => {
      const ws = wsRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN) {
        showToast("error", "Not connected to the server yet");
        return false;
      }
      ws.send(JSON.stringify(data));
      return true;
    },
    [showToast]
  );

  const join = useCallback((profile, filters) => send({ type: "join", profile, filters }), [send]);

  const sendMessage = useCallback(
    (text) => {
      const clean = text.trim();
      if (!clean || clean.length > 1000) return false;
      if (!send({ type: "message", text: clean })) return false;
      // Show my own message right away (the server only forwards it to the partner).
      setMessages((old) => [...old, { id: nextMessageId++, from: "me", text: clean }]);
      return true;
    },
    [send]
  );

  const sendTyping = useCallback(() => {
    const now = Date.now();
    if (now - lastTypingSentRef.current < TYPING_SEND_MS) return;
    lastTypingSentRef.current = now;
    send({ type: "typing" });
  }, [send]);

  const next = useCallback(() => send({ type: "next" }), [send]);

  const leave = useCallback(() => {
    send({ type: "leave" });
    setStatus("idle");
    setPartner(null);
    setMessages([]);
    setPartnerTyping(false);
  }, [send]);

  const report = useCallback(
    (reason) => {
      if (send({ type: "report", reason })) {
        showToast("info", "Thanks, your report was sent. Finding someone new...");
        send({ type: "next" });
      }
    },
    [send, showToast]
  );

  return {
    connected,
    status,
    messages,
    partner,
    onlineCount,
    partnerTyping,
    toast,
    join,
    sendMessage,
    sendTyping,
    next,
    leave,
    report,
  };
}
