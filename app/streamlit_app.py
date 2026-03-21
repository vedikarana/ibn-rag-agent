import sys, os, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
from src.intent_parser import parse_intent
from src.config_generator import generate_config
from src.safety_validator import validate
from src.document_manager import (
    ingest_document, list_namespaces, get_doc_count, delete_namespace,
)

st.set_page_config(page_title="IBN-RAG", page_icon="⬡", layout="wide")

# Fonts loaded via st.html (bypasses CSP)
st.html("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Syncopate:wght@400;700&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;1,9..40,300&family=DM+Mono:wght@300;400;500&display=swap" rel="stylesheet">
""")

st.markdown("""
<style>
:root {
  --bg:      #04080f;
  --bg2:     #0a1220;
  --bg3:     #0d1a2e;
  --glass:   rgba(255,255,255,0.05);
  --glass2:  rgba(255,255,255,0.09);
  --border:  rgba(255,255,255,0.09);
  --border2: rgba(99,179,255,0.30);
  --blue:    #63b3ff;
  --cyan:    #67e8f9;
  --violet:  #a78bfa;
  --green:   #4ade80;
  --amber:   #fbbf24;
  --red:     #f87171;
  --text:    rgba(255,255,255,0.88);
  --text2:   rgba(255,255,255,0.45);
  --text3:   rgba(255,255,255,0.18);
  --D:       'Syncopate', sans-serif;
  --B:       'DM Sans', sans-serif;
  --M:       'DM Mono', monospace;
}

/* Force dark base */
html, body { background:#04080f !important; }

/* Mesh + grid background on the whole app */
[data-testid="stAppViewContainer"] > .main {
  background:
    radial-gradient(ellipse 90% 55% at 15%  5%,  rgba(99,102,241,.14) 0%, transparent 55%),
    radial-gradient(ellipse 70% 50% at 85% 85%,  rgba(6,182,212,.12)  0%, transparent 50%),
    radial-gradient(ellipse 55% 45% at 55% 35%,  rgba(167,139,250,.09) 0%, transparent 45%),
    #04080f !important;
}
[data-testid="stAppViewContainer"] > .main::before {
  content:'';
  position:fixed; inset:0; pointer-events:none; z-index:0;
  background-image:
    linear-gradient(rgba(99,179,255,.028) 1px, transparent 1px),
    linear-gradient(90deg, rgba(99,179,255,.028) 1px, transparent 1px);
  background-size: 56px 56px;
}

/* Sidebar */
[data-testid="stSidebar"] {
  background: rgba(4,8,15,.97) !important;
  border-right: 1px solid rgba(255,255,255,.07) !important;
}

/* Hide chrome */
#MainMenu, footer, header { visibility:hidden; }
.block-container { padding:2rem 2.5rem !important; max-width:1500px !important; position:relative; z-index:1; }

/* Typography */
html, body, [class*="css"], p, span, div, label {
  font-family: 'DM Sans', sans-serif !important;
  color: rgba(255,255,255,0.88);
}
h1,h2,h3 { font-family: 'Syncopate', sans-serif !important; }
code, pre, [data-testid="stCode"] { font-family: 'DM Mono', monospace !important; }

/* Inputs */
input, textarea {
  background: rgba(255,255,255,.05) !important;
  border: 1px solid rgba(255,255,255,.10) !important;
  border-radius: 10px !important;
  color: rgba(255,255,255,.88) !important;
  font-family: 'DM Mono', monospace !important;
  font-size: 13px !important;
  transition: border-color .2s, box-shadow .2s !important;
}
input:focus, textarea:focus {
  border-color: rgba(99,179,255,.5) !important;
  box-shadow: 0 0 0 3px rgba(99,179,255,.12) !important;
  outline: none !important;
}
[data-testid="stTextArea"] textarea { min-height: 100px !important; }

/* Selectbox */
[data-testid="stSelectbox"] > div > div {
  background: rgba(255,255,255,.05) !important;
  border: 1px solid rgba(255,255,255,.10) !important;
  border-radius: 10px !important;
}

/* File uploader */
[data-testid="stFileUploader"] {
  background: rgba(255,255,255,.03) !important;
  border: 1px dashed rgba(99,179,255,.25) !important;
  border-radius: 12px !important;
}

/* Buttons */
.stButton > button {
  background: rgba(255,255,255,.05) !important;
  border: 1px solid rgba(99,179,255,.28) !important;
  color: #63b3ff !important;
  font-family: 'Syncopate', sans-serif !important;
  font-size: 9.5px !important;
  font-weight: 700 !important;
  letter-spacing: .15em !important;
  border-radius: 8px !important;
  padding: 11px 22px !important;
  transition: all .22s !important;
}
.stButton > button:hover {
  background: rgba(99,179,255,.14) !important;
  border-color: #63b3ff !important;
  box-shadow: 0 0 22px rgba(99,179,255,.28) !important;
  transform: translateY(-1px) !important;
}
button[kind="primary"] {
  background: linear-gradient(135deg, rgba(99,179,255,.22), rgba(103,232,249,.16)) !important;
  border-color: #67e8f9 !important;
  color: #67e8f9 !important;
  box-shadow: 0 0 28px rgba(103,232,249,.18) !important;
}
button[kind="primary"]:hover {
  box-shadow: 0 0 42px rgba(103,232,249,.32) !important;
}

/* Download button */
[data-testid="stDownloadButton"] button {
  background: rgba(167,139,250,.10) !important;
  border: 1px solid rgba(167,139,250,.30) !important;
  color: #a78bfa !important;
  font-family: 'Syncopate', sans-serif !important;
  font-size: 9px !important;
  letter-spacing: .14em !important;
  border-radius: 8px !important;
}

/* Code */
[data-testid="stCode"], pre {
  background: rgba(0,0,0,.55) !important;
  border: 1px solid rgba(99,179,255,.14) !important;
  border-left: 2px solid #63b3ff !important;
  border-radius: 10px !important;
  color: #67e8f9 !important;
}

/* JSON */
[data-testid="stJson"] {
  background: rgba(0,0,0,.45) !important;
  border: 1px solid rgba(74,222,128,.18) !important;
  border-left: 2px solid #4ade80 !important;
  border-radius: 10px !important;
}

/* Alerts */
[data-testid="stSuccess"] {
  background: rgba(74,222,128,.07) !important;
  border: 1px solid rgba(74,222,128,.28) !important;
  border-radius: 10px !important; color:#4ade80 !important;
}
[data-testid="stWarning"] {
  background: rgba(251,191,36,.07) !important;
  border: 1px solid rgba(251,191,36,.28) !important;
  border-radius: 10px !important; color:#fbbf24 !important;
}
[data-testid="stError"] {
  background: rgba(248,113,113,.07) !important;
  border: 1px solid rgba(248,113,113,.28) !important;
  border-radius: 10px !important; color:#f87171 !important;
}
[data-testid="stInfo"] {
  background: rgba(255,255,255,.04) !important;
  border: 1px solid rgba(255,255,255,.10) !important;
  border-radius: 10px !important;
}

/* Multiselect tags */
[data-baseweb="tag"] {
  background: rgba(99,179,255,.16) !important;
  border: 1px solid rgba(99,179,255,.32) !important;
  border-radius: 6px !important;
  color: #63b3ff !important;
  font-family: 'DM Mono', monospace !important;
  font-size: 11px !important;
}

/* Progress */
[data-testid="stProgressBar"] > div > div {
  background: linear-gradient(90deg, #63b3ff, #67e8f9) !important;
}

/* Expander */
[data-testid="stExpander"] {
  background: rgba(255,255,255,.04) !important;
  border: 1px solid rgba(255,255,255,.09) !important;
  border-radius: 12px !important;
}

/* Scrollbar */
::-webkit-scrollbar { width:3px; height:3px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:rgba(99,179,255,.35); border-radius:2px; }

/* Divider */
hr { border-color: rgba(255,255,255,.07) !important; }
</style>
""", unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-bottom:30px;">
  <div style="display:flex;align-items:center;gap:18px;flex-wrap:wrap;margin-bottom:14px;">
    <div style="
      width:50px;height:50px;border-radius:14px;
      background:linear-gradient(135deg,rgba(99,179,255,.22),rgba(103,232,249,.12));
      border:1px solid rgba(99,179,255,.32);
      display:flex;align-items:center;justify-content:center;font-size:22px;
      box-shadow:0 0 32px rgba(99,179,255,.2),inset 0 1px 0 rgba(255,255,255,.1);">⬡</div>
    <div>
      <div style="
        font-family:'Syncopate',sans-serif;font-size:24px;font-weight:700;
        letter-spacing:.06em;line-height:1.1;margin-bottom:3px;
        background:linear-gradient(130deg,#fff 25%,#63b3ff 60%,#67e8f9 100%);
        -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">
        IBN — RAG
      </div>
      <div style="font-family:'DM Mono',monospace;font-size:10.5px;
                  color:rgba(255,255,255,.3);letter-spacing:.18em;text-transform:uppercase;">
        Intent · Based · Networking · Agent
      </div>
    </div>
    <div style="margin-left:auto;display:flex;gap:7px;flex-wrap:wrap;align-items:center;">
      <span style="padding:4px 12px;border-radius:20px;font-family:'DM Mono',monospace;font-size:10px;
                   background:rgba(74,222,128,.10);color:#4ade80;border:1px solid rgba(74,222,128,.22);">● ONLINE</span>
      <span style="padding:4px 12px;border-radius:20px;font-family:'DM Mono',monospace;font-size:10px;
                   background:rgba(99,179,255,.08);color:#63b3ff;border:1px solid rgba(99,179,255,.18);">CPU ONLY</span>
      <span style="padding:4px 12px;border-radius:20px;font-family:'DM Mono',monospace;font-size:10px;
                   background:rgba(167,139,250,.08);color:#a78bfa;border:1px solid rgba(167,139,250,.18);">NO CLOUD API</span>
    </div>
  </div>
  <div style="height:1px;background:linear-gradient(90deg,transparent,rgba(99,179,255,.35),rgba(103,232,249,.2),transparent);"></div>
</div>
""", unsafe_allow_html=True)

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:14px 0 12px;">
      <div style="font-family:'Syncopate',sans-serif;font-size:10px;font-weight:700;
                  color:#63b3ff;letter-spacing:.18em;margin-bottom:10px;">KNOWLEDGE BASE</div>
      <div style="height:1px;background:linear-gradient(90deg,rgba(99,179,255,.4),transparent);"></div>
    </div>
    """, unsafe_allow_html=True)

    uploaded_files = st.file_uploader("files", type=["pdf","txt","md"],
                                       accept_multiple_files=True, label_visibility="collapsed")
    st.markdown('<p style="font-family:\'DM Mono\',monospace;font-size:10px;color:rgba(255,255,255,.25);letter-spacing:.08em;margin-top:-6px;margin-bottom:10px;">PDF · TXT · MARKDOWN</p>', unsafe_allow_html=True)
    ns_name = st.text_input("ns", placeholder="namespace  e.g. cisco / juniper / nist", label_visibility="collapsed")
    st.markdown('<p style="font-family:\'DM Mono\',monospace;font-size:10px;color:rgba(255,255,255,.25);letter-spacing:.08em;margin-top:-6px;margin-bottom:10px;">NAMESPACE TAG</p>', unsafe_allow_html=True)

    if st.button("⬆  INGEST DOCUMENTS", use_container_width=True):
        if not uploaded_files: st.warning("Select files first.")
        elif not ns_name.strip(): st.warning("Enter a namespace tag.")
        else:
            total=0
            prog=st.progress(0,text="Processing...")
            for i,f in enumerate(uploaded_files):
                prog.progress(i/len(uploaded_files),text=f"{f.name}")
                suf=Path(f.name).suffix
                with tempfile.NamedTemporaryFile(delete=False,suffix=suf) as tmp:
                    tmp.write(f.read()); tp=tmp.name
                try: total+=ingest_document(tp,namespace=ns_name.strip())
                finally: os.unlink(tp)
            prog.progress(1.0,text="Done")
            st.success(f"{total} chunks → '{ns_name.strip()}'")
            st.rerun()

    st.markdown('<div style="height:1px;background:rgba(255,255,255,.06);margin:14px 0;"></div>', unsafe_allow_html=True)
    st.markdown('<p style="font-family:\'DM Mono\',monospace;font-size:10px;color:rgba(255,255,255,.25);letter-spacing:.08em;margin-bottom:8px;">ACTIVE NAMESPACES</p>', unsafe_allow_html=True)
    all_ns = list_namespaces()
    if all_ns:
        selected_ns = st.multiselect("ns_sel", options=["all"]+all_ns, default=all_ns[:1], label_visibility="collapsed")
        for ns in all_ns:
            c1,c2=st.columns([5,1])
            c1.markdown(f'<div style="font-family:\'DM Mono\',monospace;font-size:11px;color:rgba(255,255,255,.45);padding:3px 0;">{ns} <span style="color:#63b3ff">· {get_doc_count(ns)}</span></div>', unsafe_allow_html=True)
            if c2.button("✕",key=f"del_{ns}"): delete_namespace(ns); st.rerun()
    else:
        selected_ns=[]
        st.markdown('<p style="font-family:\'DM Mono\',monospace;font-size:11px;color:rgba(255,255,255,.2);">No documents loaded</p>', unsafe_allow_html=True)

    st.markdown('<div style="height:1px;background:rgba(255,255,255,.06);margin:14px 0;"></div>', unsafe_allow_html=True)
    st.markdown('<p style="font-family:\'DM Mono\',monospace;font-size:10px;color:rgba(255,255,255,.25);letter-spacing:.08em;margin-bottom:8px;">OUTPUT FORMAT</p>', unsafe_allow_html=True)
    output_format = st.selectbox("fmt", ["generic","cisco","juniper","ansible"], label_visibility="collapsed")

    st.markdown('<div style="height:1px;background:rgba(255,255,255,.06);margin:14px 0;"></div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-family:'DM Mono',monospace;font-size:10px;line-height:2.3;color:rgba(255,255,255,.2);">
      PARSER&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#63b3ff">phi3.5</span><br>
      GENERATOR&nbsp;&nbsp;<span style="color:#63b3ff">qwen2.5-coder</span><br>
      VECTOR DB&nbsp;&nbsp;&nbsp;<span style="color:#63b3ff">ChromaDB</span><br>
      EMBEDDER&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#63b3ff">MiniLM-L6</span><br>
      CLOUD API&nbsp;&nbsp;&nbsp;<span style="color:#4ade80">none · offline</span>
    </div>
    """, unsafe_allow_html=True)

# ── INTENT ────────────────────────────────────────────────────────────────────
st.markdown('<div style="font-family:\'Syncopate\',sans-serif;font-size:9.5px;font-weight:700;color:#63b3ff;letter-spacing:.2em;margin-bottom:10px;">NETWORK INTENT</div>', unsafe_allow_html=True)

examples = [
    "Deny all TCP from 10.0.0.0/8 to 192.168.1.100 port 22",
    "Permit HTTP from 192.168.10.0/24 to 10.0.1.5 between 09:00 and 18:00",
    "Block ICMP from any to 172.16.0.0/16 after 22:00",
    "Allow DNS from 192.168.0.0/16 to 8.8.8.8 port 53",
]
with st.expander("Examples"):
    for ex in examples:
        if st.button(ex, key=f"ex_{ex}"): st.session_state["intent_input"]=ex

intent_text = st.text_area("intent", value=st.session_state.get("intent_input",""),
    placeholder='Describe your network policy in plain English...\ne.g.  "Block all SSH from Sales VLAN to Finance server between 21:00 and 06:00"',
    height=100, label_visibility="collapsed")

c1,c2=st.columns([2,5])
with c1:
    go=st.button("⬡  GENERATE CONFIG", type="primary", use_container_width=True,
                 disabled=not intent_text.strip() or not selected_ns)
with c2:
    if not selected_ns:
        st.markdown('<p style="font-family:\'DM Mono\',monospace;font-size:11px;color:#fbbf24;padding:10px 0;opacity:.75;">⚠  load a knowledge base to continue</p>', unsafe_allow_html=True)

# ── OUTPUT ────────────────────────────────────────────────────────────────────
if go and intent_text.strip() and selected_ns:
    st.markdown('<div style="height:1px;background:linear-gradient(90deg,transparent,rgba(99,179,255,.2),transparent);margin:22px 0 18px;"></div>', unsafe_allow_html=True)

    c1,c2,c3=st.columns([1,1.4,.85])

    with c1:
        st.markdown('<div style="font-family:\'Syncopate\',sans-serif;font-size:8.5px;font-weight:700;color:#67e8f9;letter-spacing:.2em;margin-bottom:10px;">01 · PARSED INTENT</div>', unsafe_allow_html=True)
        with st.spinner("Parsing..."): intent_json=parse_intent(intent_text)
        if "error" in intent_json: st.error(f"Parse failed · {intent_json.get('raw','')[:100]}"); st.stop()
        st.json(intent_json)

    with c2:
        st.markdown('<div style="font-family:\'Syncopate\',sans-serif;font-size:8.5px;font-weight:700;color:#67e8f9;letter-spacing:.2em;margin-bottom:10px;">02 · GENERATED CONFIG</div>', unsafe_allow_html=True)
        with st.spinner("Generating..."): config=generate_config(intent_json,namespaces=selected_ns,output_format=output_format)
        st.code(config,language="text")
        st.download_button("⬇  EXPORT CONFIG",data=config,file_name="ibn_config.txt",mime="text/plain")

    with c3:
        result=validate(config)
        st.markdown('<div style="font-family:\'Syncopate\',sans-serif;font-size:8.5px;font-weight:700;color:#67e8f9;letter-spacing:.2em;margin-bottom:10px;">03 · SAFETY REPORT</div>', unsafe_allow_html=True)
        sc=result.score
        if sc>=70:   rc,lb,bg="#4ade80","SAFE",   "rgba(74,222,128,.08)"
        elif sc>=40: rc,lb,bg="#fbbf24","REVIEW", "rgba(251,191,36,.08)"
        else:        rc,lb,bg="#f87171","BLOCKED","rgba(248,113,113,.08)"

        st.markdown(f"""
        <div style="background:{bg};border:1px solid {rc}33;border-radius:16px;
                    padding:24px 16px;text-align:center;margin-bottom:12px;
                    box-shadow:0 0 40px {rc}18;">
          <div style="width:88px;height:88px;border-radius:50%;border:2px solid {rc};
                      margin:0 auto 12px;display:flex;align-items:center;
                      justify-content:center;flex-direction:column;
                      box-shadow:0 0 28px {rc}44,inset 0 0 16px {rc}10;
                      background:rgba(0,0,0,.35);">
            <div style="font-family:'Syncopate',sans-serif;font-size:25px;font-weight:700;
                        color:{rc};line-height:1;">{sc}</div>
            <div style="font-family:'DM Mono',monospace;font-size:9px;color:{rc}99;">/100</div>
          </div>
          <div style="font-family:'Syncopate',sans-serif;font-size:10px;font-weight:700;
                      color:{rc};letter-spacing:.2em;">{lb}</div>
        </div>
        """, unsafe_allow_html=True)

        if result.safe: st.success("Cleared for deployment")
        else:           st.error("Deployment blocked")
        for issue in result.issues: st.error(f"✕  {issue}")
        for w in result.warnings:   st.warning(f"△  {w}")
        st.markdown(f'<p style="font-family:\'DM Mono\',monospace;font-size:10px;color:rgba(255,255,255,.2);margin-top:8px;">kb: {" · ".join(selected_ns)}</p>', unsafe_allow_html=True)

    if "history" not in st.session_state: st.session_state.history=[]
    st.session_state.history.insert(0,{"intent":intent_text,"score":sc,"format":output_format,"ns":selected_ns})

# ── LOG ───────────────────────────────────────────────────────────────────────
if st.session_state.get("history"):
    st.markdown('<div style="height:1px;background:linear-gradient(90deg,transparent,rgba(99,179,255,.15),transparent);margin:26px 0 16px;"></div>', unsafe_allow_html=True)
    st.markdown('<div style="font-family:\'Syncopate\',sans-serif;font-size:9px;font-weight:700;color:#63b3ff;letter-spacing:.2em;margin-bottom:12px;">SESSION LOG</div>', unsafe_allow_html=True)
    for h in st.session_state.history[:6]:
        sc2=h["score"]
        dot="#4ade80" if sc2>=70 else "#fbbf24" if sc2>=40 else "#f87171"
        with st.expander(f"{h['intent'][:70]}..."):
            st.markdown(f'<div style="font-family:\'DM Mono\',monospace;font-size:11px;color:rgba(255,255,255,.4);">score <span style="color:{dot}">{sc2}</span> · format {h["format"]} · kb {" · ".join(h["ns"])}</div>', unsafe_allow_html=True)