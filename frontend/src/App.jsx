// Top-level component: picks which screen to show based on the socket status.
//   idle                 -> ProfileForm
//   waiting              -> WaitingScreen
//   chatting/partner_left -> ChatRoom

import { useState } from "react";
import { useChatSocket } from "./useChatSocket.js";
import ProfileForm from "./components/ProfileForm.jsx";
import WaitingScreen from "./components/WaitingScreen.jsx";
import ChatRoom from "./components/ChatRoom.jsx";

export default function App() {
  const chat = useChatSocket();

  // Remembered for the whole session, so "Next" and "Stop" don't make you retype.
  const [profile, setProfile] = useState({ username: "", age: "", country: "", gender: "" });
  const [filters, setFilters] = useState({ countries: [], age_min: 18, age_max: 99 });

  function handleStart(cleanProfile, cleanFilters) {
    chat.join(cleanProfile, cleanFilters);
  }

  let screen;
  if (chat.status === "waiting") {
    screen = <WaitingScreen filters={filters} gender={profile.gender} onCancel={chat.leave} />;
  } else if (chat.status === "chatting" || chat.status === "partner_left") {
    screen = (
      <ChatRoom
        status={chat.status}
        partner={chat.partner}
        messages={chat.messages}
        partnerTyping={chat.partnerTyping}
        onSend={chat.sendMessage}
        onTyping={chat.sendTyping}
        onNext={chat.next}
        onStop={chat.leave}
        onReport={chat.report}
      />
    );
  } else {
    screen = (
      <ProfileForm
        profile={profile}
        setProfile={setProfile}
        filters={filters}
        setFilters={setFilters}
        onStart={handleStart}
        connected={chat.connected}
        onlineCount={chat.onlineCount}
      />
    );
  }

  return (
    <div className="app">
      {screen}
      {chat.toast && (
        <div className={`toast toast-${chat.toast.kind}`} role="status">
          {chat.toast.text}
        </div>
      )}
    </div>
  );
}
