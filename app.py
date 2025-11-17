import os, json, re, datetime
from pathlib import Path
from flask import Flask, request, jsonify, render_template

MOCK_MODE = True  # Keep True for demo (no IBM calls). Set False to enable real IBM stubs.
CONFIG_PATH = os.getenv("VHA_CONFIG", "config.json")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "local_data"
DATA_DIR.mkdir(exist_ok=True)
HISTORY_FILE = DATA_DIR / "history.json"

app = Flask(__name__, static_folder="static", template_folder="templates")

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}

CONFIG = load_config()

def _read_history():
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, "r") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []

def _write_history(history_list):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history_list, f, indent=2)

def save_turn(user_text, bot_text, meta=None):
    hist = _read_history()
    hist.append({
        "ts": datetime.datetime.utcnow().isoformat() + "Z",
        "user": user_text,
        "bot": bot_text,
        "meta": meta or {}
    })
    _write_history(hist)

def clean_text(t: str) -> str:
    t = (t or "").strip()
    t = re.sub(r"\s+", " ", t)
    return t

def detect_symptoms(text: str):
    text_l = text.lower()
    return {
        "fever": any(k in text_l for k in ["fever", "temperature", "high temp"]),
        "cough": any(k in text_l for k in ["cough", "coughing"]),
        "cold": any(k in text_l for k in ["cold", "runny nose", "sneezing"]),
        "headache": any(k in text_l for k in ["headache", "migraine", "head pain"]),
        "sore_throat": any(k in text_l for k in ["sore throat", "throat pain"]),
        "body_pain": any(k in text_l for k in ["body pain", "body ache", "muscle pain", "myalgia"]),
        "stomach": any(k in text_l for k in ["stomach", "abdomen", "abdominal", "belly", "gastric"]),
        "vomiting": any(k in text_l for k in ["vomit", "vomiting", "throwing up", "nausea"]),
        "diarrhea": any(k in text_l for k in ["diarrhea", "loose motion", "loose motions"]),
        "breath": any(k in text_l for k in ["shortness of breath", "breathless", "breathing trouble"]),
        "chest_pain": any(k in text_l for k in ["chest pain", "tightness in chest"]),
        "injury": any(k in text_l for k in ["injury", "sprain", "fracture", "cut", "wound"])
    }

def severity_assessor(sym):
    red_flags = []
    severity = "low"
    if sym["breath"] or sym["chest_pain"]:
        severity = "urgent"
        if sym["breath"]: red_flags.append("Shortness of breath")
        if sym["chest_pain"]: red_flags.append("Chest pain")
    if sym["vomiting"] and sym["diarrhea"]:
        severity = "moderate" if severity != "urgent" else severity
        red_flags.append("Risk of dehydration")
    if sym["fever"] and (sym["headache"] or sym["body_pain"]):
        severity = "moderate" if severity != "urgent" else severity
    if sym["injury"]:
        severity = "moderate" if severity != "urgent" else severity
    return severity, red_flags

def structured_plan(sym):
    plan = {"possible_causes": [], "self_care": [], "otc": [], "monitoring": [], "seek_help": []}

    if sym["fever"] and (sym["cough"] or sym["cold"] or sym["body_pain"]):
        plan["possible_causes"].append("Viral fever / common respiratory infection")
    if sym["sore_throat"]:
        plan["possible_causes"].append("Viral pharyngitis")
    if sym["stomach"] and (sym["vomiting"] or sym["diarrhea"]):
        plan["possible_causes"].append("Gastroenteritis (stomach infection)")
    if sym["injury"]:
        plan["possible_causes"].append("Musculoskeletal injury")
    if sym["chest_pain"]:
        plan["possible_causes"].append("Chest discomfort — needs medical evaluation")
    if sym["breath"]:
        plan["possible_causes"].append("Breathing difficulty — possible asthma/respiratory issue")

    plan["self_care"] += [
        "Rest and avoid strenuous activity",
        "Hydrate well (water/ORS/soups) — small, frequent sips",
        "Light, easy-to-digest meals (khichdi, soups, bananas, curd rice)"
    ]
    if sym["sore_throat"] or sym["cough"] or sym["cold"]:
        plan["self_care"] += ["Warm saline gargles 2–3×/day", "Steam inhalation 1–2×/day"]
    if sym["injury"]:
        plan["self_care"].append("RICE: Rest, Ice (15–20 min), Compression, Elevation")

    if sym["fever"] or sym["headache"] or sym["body_pain"]:
        plan["otc"].append("Paracetamol 500 mg as per label (avoid overdose)")
    if sym["cold"] or sym["cough"] or sym["sore_throat"]:
        plan["otc"].append("Warm fluids, lozenges; cough syrup as per label")
    if sym["vomiting"] or sym["diarrhea"]:
        plan["otc"].append("Oral Rehydration Solution (ORS) after each loose stool")

    plan["monitoring"] += [
        "Check temperature 2–3×/day if fever",
        "Watch urine output/dizziness/dry mouth (dehydration signs)",
        "Note worsening symptoms, rash, confusion, or persistent high fever"
    ]

    severity, red_flags = severity_assessor(sym)
    if severity == "urgent":
        plan["seek_help"] = [
            "Immediate medical care/ER for chest pain or breathing difficulty",
            "Go to ER for fainting, confusion, blue lips, or severe persistent pain"
        ]
    else:
        plan["seek_help"] = [
            "Consult a clinician if symptoms persist >72 hours or worsen",
        ]
        if "Risk of dehydration" in red_flags:
            plan["seek_help"].append("See a clinician if you cannot keep fluids down or urine output drops")
    return severity, plan

def compose_message(user_text, severity, plan):
    openings = {
        "urgent": "Thanks for sharing — some of what you described can be serious.",
        "moderate": "Thanks — I can suggest steps to help you feel better.",
        "low": "Got it — here are a few steps that usually help."
    }
    lines = [openings.get(severity, openings["low"])]

    if plan["possible_causes"]:
        lines.append("\n**Possible cause(s):** " + "; ".join(plan["possible_causes"]))
    if plan["self_care"]:
        lines.append("\n**Do now:**")
        lines += [f"- {s}" for s in plan["self_care"]]
    if plan["otc"]:
        lines.append("\n**Over-the-counter options (check label & allergies):**")
        lines += [f"- {o}" for o in plan["otc"]]
    if plan["monitoring"]:
        lines.append("\n**Monitor:**")
        lines += [f"- {m}" for m in plan["monitoring"]]
    if plan["seek_help"]:
        lines.append("\n**Seek medical help if:**")
        lines += [f"- {h}" for h in plan["seek_help"]]

    lines.append("\n*Note: General guidance only — not a diagnosis. For emergencies, seek immediate care.*")
    if len(user_text) <= 140:
        lines.append(f'\n> You said: “{user_text}”. I tailored the steps based on those symptoms.')
    return "\n".join(lines)

def generate_mock_reply(user_text: str):
    text = clean_text(user_text)
    sym = detect_symptoms(text)
    if not any(sym.values()):
        generic = (
            "I didn’t detect specific symptoms. Could you share duration, fever, pain location, or triggers? "
            "Meanwhile, rest, hydrate, and avoid heavy meals. If chest pain, trouble breathing, severe weakness, "
            "or symptoms >72 hours, please see a clinician."
        )
        return {"reply": generic, "severity": "unknown", "actions": {}}
    severity, plan = structured_plan(sym)
    return {"reply": compose_message(text, severity, plan), "severity": severity, "actions": plan}

def ibm_assistant_reply(user_text: str) -> str:
    # Stub showing how IBM Watson Assistant would be called (disabled for Mock Mode)
    return "IBM Watson Assistant (disabled in Mock Mode)."

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/healthbot", methods=["POST"])
def api_healthbot():
    data = request.get_json(silent=True) or {}
    user_text = clean_text(data.get("message", ""))
    if not user_text:
        return jsonify({"error": "Empty message"}), 400
    if MOCK_MODE:
        out = generate_mock_reply(user_text)
        save_turn(user_text, out["reply"], {"mode": "MOCK"})
        return jsonify({
            "text": out["reply"],
            "severity": out.get("severity", "unknown"),
            "actions": out.get("actions", {}),
            "tts_url": None
        })
    reply = ibm_assistant_reply(user_text)
    save_turn(user_text, reply, {"mode": "IBM"})
    return jsonify({"text": reply, "severity": "unknown", "actions": {}, "tts_url": None})

@app.route("/api/history", methods=["GET"])
def api_history():
    return jsonify(_read_history())

@app.route("/api/reset", methods=["POST"])
def api_reset():
    _write_history([])
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(debug=True)
