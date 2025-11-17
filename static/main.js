const chat = document.getElementById("chat");
const msg = document.getElementById("msg");
const sendBtn = document.getElementById("sendBtn");
const micBtn = document.getElementById("micBtn");
const speakBtn = document.getElementById("speakBtn");
const resetBtn = document.getElementById("resetBtn");
const statusEl = document.getElementById("status");

/* Subtle IBM-style UI sounds using WebAudio (no files needed) */
const audioCtx = window.AudioContext ? new AudioContext() : null;
function beep(freq=880, duration=0.05, type="sine", vol=0.02){
  if(!audioCtx) return;
  const o = audioCtx.createOscillator();
  const g = audioCtx.createGain();
  o.type = type;
  o.frequency.value = freq;
  g.gain.value = vol;
  o.connect(g); g.connect(audioCtx.destination);
  o.start();
  setTimeout(()=>{o.stop();}, duration*1000);
}
function sendSound(){beep(820,0.05,"sine",0.02)}
function botSound(){beep(520,0.06,"sine",0.02)}

function addMsg(text, who = "bot", severity) {
  const div = document.createElement("div");
  div.className = `msg ${who}`;
  if (who === "bot" && severity && severity !== "unknown") {
    const badge = document.createElement("span");
    badge.className = `badge ${severity}`;
    badge.textContent = severity.toUpperCase();
    div.appendChild(badge);
    div.appendChild(document.createTextNode(" "));
  }
  div.appendChild(document.createTextNode(text));
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  if(who==="me") sendSound(); else botSound();
}

async function sendMessage() {
  const text = msg.value.trim();
  if (!text) return;
  addMsg(text, "me");
  msg.value = "";
  statusEl.textContent = "Analyzing…";
  try {
    const res = await fetch("/api/healthbot", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text })
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    addMsg(data.text, "bot", data.severity);
  } catch (e) {
    addMsg("Sorry, something went wrong.", "bot");
  } finally {
    statusEl.textContent = "";
  }
}

sendBtn.onclick = sendMessage;
msg.addEventListener("keydown", (e) => { if (e.key === "Enter") sendMessage(); });

/* --- Voice: SpeechRecognition (browser STT) --- */
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
let rec;
if (SR) {
  rec = new SR();
  rec.lang = "en-US";
  rec.interimResults = false;
  rec.maxAlternatives = 1;
  rec.onresult = (e) => {
    const text = e.results[0][0].transcript;
    msg.value = text;
    sendMessage();
  };
  rec.onerror = () => { statusEl.textContent = "Mic error."; };
}
micBtn.onclick = async () => {
  try{ if(audioCtx && audioCtx.state==="suspended") await audioCtx.resume(); }catch{}
  if (!rec) { alert("SpeechRecognition not supported in this browser."); return; }
  statusEl.textContent = "Listening…";
  rec.start();
};

/* --- Voice: speechSynthesis (browser TTS) --- */
speakBtn.onclick = () => {
  const lastBot = [...document.querySelectorAll(".msg.bot")].pop();
  if (!lastBot) return;
  const text = lastBot.innerText.replace(/^LOW|MODERATE|URGENT\s*/,"").trim();
  const u = new SpeechSynthesisUtterance(text);
  u.rate = 1.02;
  speechSynthesis.speak(u);
};

/* Utilities */
resetBtn.onclick = async () => {
  await fetch("/api/reset", { method: "POST" });
  chat.innerHTML = "";
  addMsg("History cleared. How can I help today?", "bot");
};

addMsg("Welcome. Please describe your symptoms. Example: “Fever and headache since yesterday.”", "bot");
