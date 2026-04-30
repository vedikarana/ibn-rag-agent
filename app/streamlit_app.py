import sys, os, tempfile, time, json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
from src.intent_parser import parse_intent
from src.config_generator import generate_config
from src.safety_validator import validate
from src.document_manager import ingest_document, list_namespaces, get_doc_count, delete_namespace

st.set_page_config(page_title="IBN-RAG", page_icon="⬡", layout="wide")

st.html("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Syncopate:wght@400;700&family=DM+Sans:wght@300;400;500&family=DM+Mono:wght@300;400;500&display=swap" rel="stylesheet">
""")

st.markdown("""<style>
:root{--bg:#04080f;--glass:rgba(255,255,255,0.05);--border:rgba(255,255,255,0.09);
--border2:rgba(99,179,255,0.30);--blue:#63b3ff;--cyan:#67e8f9;--violet:#a78bfa;
--green:#4ade80;--amber:#fbbf24;--red:#f87171;--text:rgba(255,255,255,0.88);
--text2:rgba(255,255,255,0.45);--D:'Syncopate',sans-serif;--B:'DM Sans',sans-serif;--M:'DM Mono',monospace;}
html,body{background:#04080f !important;}
[data-testid="stAppViewContainer"]>.main{
  background:radial-gradient(ellipse 90% 55% at 15% 5%,rgba(99,102,241,.14) 0%,transparent 55%),
  radial-gradient(ellipse 70% 50% at 85% 85%,rgba(6,182,212,.12) 0%,transparent 50%),#04080f !important;}
[data-testid="stAppViewContainer"]>.main::before{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background-image:linear-gradient(rgba(99,179,255,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(99,179,255,.025) 1px,transparent 1px);
  background-size:56px 56px;}
[data-testid="stSidebar"]{background:rgba(4,8,15,.97)!important;border-right:1px solid rgba(255,255,255,.07)!important;}
#MainMenu,footer,header{visibility:hidden;}
.block-container{padding:1.5rem 2rem!important;max-width:1500px!important;position:relative;z-index:1;}
html,body,[class*="css"],p,span,div,label{font-family:'DM Sans',sans-serif!important;color:rgba(255,255,255,0.88);}
input,textarea{background:rgba(255,255,255,.05)!important;border:1px solid rgba(255,255,255,.10)!important;
  border-radius:10px!important;color:rgba(255,255,255,.88)!important;font-family:'DM Mono',monospace!important;font-size:13px!important;}
input:focus,textarea:focus{border-color:rgba(99,179,255,.5)!important;box-shadow:0 0 0 3px rgba(99,179,255,.12)!important;}
[data-testid="stSelectbox"]>div>div{background:rgba(255,255,255,.05)!important;border:1px solid rgba(255,255,255,.10)!important;border-radius:10px!important;}
[data-testid="stFileUploader"]{background:rgba(255,255,255,.03)!important;border:1px dashed rgba(99,179,255,.25)!important;border-radius:12px!important;}
.stButton>button{background:rgba(255,255,255,.05)!important;border:1px solid rgba(99,179,255,.28)!important;color:#63b3ff!important;
  font-family:'Syncopate',sans-serif!important;font-size:9.5px!important;font-weight:700!important;letter-spacing:.15em!important;
  border-radius:8px!important;padding:11px 22px!important;transition:all .22s!important;}
.stButton>button:hover{background:rgba(99,179,255,.14)!important;border-color:#63b3ff!important;box-shadow:0 0 22px rgba(99,179,255,.28)!important;}
button[kind="primary"]{background:linear-gradient(135deg,rgba(99,179,255,.22),rgba(103,232,249,.16))!important;border-color:#67e8f9!important;color:#67e8f9!important;}
[data-testid="stCode"],pre{background:rgba(0,0,0,.55)!important;border:1px solid rgba(99,179,255,.14)!important;
  border-left:2px solid #63b3ff!important;border-radius:10px!important;color:#67e8f9!important;}
[data-testid="stJson"]{background:rgba(0,0,0,.45)!important;border:1px solid rgba(74,222,128,.18)!important;
  border-left:2px solid #4ade80!important;border-radius:10px!important;}
[data-testid="stSuccess"]{background:rgba(74,222,128,.07)!important;border:1px solid rgba(74,222,128,.28)!important;border-radius:10px!important;color:#4ade80!important;}
[data-testid="stWarning"]{background:rgba(251,191,36,.07)!important;border:1px solid rgba(251,191,36,.28)!important;border-radius:10px!important;color:#fbbf24!important;}
[data-testid="stError"]{background:rgba(248,113,113,.07)!important;border:1px solid rgba(248,113,113,.28)!important;border-radius:10px!important;color:#f87171!important;}
[data-testid="stTabs"] [data-baseweb="tab"]{font-family:'Syncopate',sans-serif!important;font-size:9px!important;letter-spacing:.15em!important;color:rgba(255,255,255,.4)!important;}
[data-testid="stTabs"] [aria-selected="true"]{color:#63b3ff!important;border-bottom-color:#63b3ff!important;}
[data-testid="stTabs"] [data-baseweb="tab-list"]{background:transparent!important;border-bottom:1px solid rgba(255,255,255,.08)!important;}
[data-baseweb="tab-panel"]{background:transparent!important;}
[data-baseweb="tag"]{background:rgba(99,179,255,.16)!important;border:1px solid rgba(99,179,255,.32)!important;border-radius:6px!important;color:#63b3ff!important;}
[data-testid="stProgressBar"]>div>div{background:linear-gradient(90deg,#63b3ff,#67e8f9)!important;}
[data-testid="stExpander"]{background:rgba(255,255,255,.04)!important;border:1px solid rgba(255,255,255,.09)!important;border-radius:12px!important;}
::-webkit-scrollbar{width:3px;height:3px;}::-webkit-scrollbar-thumb{background:rgba(99,179,255,.35);border-radius:2px;}
hr{border-color:rgba(255,255,255,.07)!important;}
</style>""", unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-bottom:24px;">
  <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:12px;">
    <div style="width:48px;height:48px;border-radius:12px;
      background:linear-gradient(135deg,rgba(99,179,255,.22),rgba(103,232,249,.12));
      border:1px solid rgba(99,179,255,.32);display:flex;align-items:center;justify-content:center;font-size:20px;
      box-shadow:0 0 28px rgba(99,179,255,.2);">⬡</div>
    <div>
      <div style="font-family:'Syncopate',sans-serif;font-size:22px;font-weight:700;letter-spacing:.06em;
        background:linear-gradient(130deg,#fff 25%,#63b3ff 60%,#67e8f9 100%);
        -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">IBN — RAG</div>
      <div style="font-family:'DM Mono',monospace;font-size:10px;color:rgba(255,255,255,.3);letter-spacing:.18em;">INTENT · BASED · NETWORKING · AGENT</div>
    </div>
    <div style="margin-left:auto;display:flex;gap:6px;flex-wrap:wrap;">
      <span style="padding:3px 11px;border-radius:20px;font-family:'DM Mono',monospace;font-size:10px;background:rgba(74,222,128,.10);color:#4ade80;border:1px solid rgba(74,222,128,.22);">● ONLINE</span>
      <span style="padding:3px 11px;border-radius:20px;font-family:'DM Mono',monospace;font-size:10px;background:rgba(99,179,255,.08);color:#63b3ff;border:1px solid rgba(99,179,255,.18);">CPU ONLY</span>
      <span style="padding:3px 11px;border-radius:20px;font-family:'DM Mono',monospace;font-size:10px;background:rgba(167,139,250,.08);color:#a78bfa;border:1px solid rgba(167,139,250,.18);">NO CLOUD API</span>
    </div>
  </div>
  <div style="height:1px;background:linear-gradient(90deg,transparent,rgba(99,179,255,.35),rgba(103,232,249,.2),transparent);"></div>
</div>
""", unsafe_allow_html=True)

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div style="font-family:\'Syncopate\',sans-serif;font-size:10px;font-weight:700;color:#63b3ff;letter-spacing:.18em;margin-bottom:10px;">KNOWLEDGE BASE</div>', unsafe_allow_html=True)
    uploaded_files = st.file_uploader("files", type=["pdf","txt","md"], accept_multiple_files=True, label_visibility="collapsed")
    st.markdown('<p style="font-family:\'DM Mono\',monospace;font-size:10px;color:rgba(255,255,255,.25);margin-top:-6px;margin-bottom:8px;">PDF · TXT · MARKDOWN</p>', unsafe_allow_html=True)
    ns_name = st.text_input("ns", placeholder="namespace e.g. cisco / nist", label_visibility="collapsed")
    if st.button("⬆  INGEST", use_container_width=True):
        if not uploaded_files: st.warning("Select files.")
        elif not ns_name.strip(): st.warning("Enter namespace.")
        else:
            total=0; prog=st.progress(0,text="Processing...")
            for i,f in enumerate(uploaded_files):
                prog.progress(i/len(uploaded_files),text=f"{f.name}")
                suf=Path(f.name).suffix
                with tempfile.NamedTemporaryFile(delete=False,suffix=suf) as tmp:
                    tmp.write(f.read()); tp=tmp.name
                try: total+=ingest_document(tp,namespace=ns_name.strip())
                finally: os.unlink(tp)
            prog.progress(1.0,text="Done"); st.success(f"{total} chunks → '{ns_name.strip()}'"); st.rerun()

    st.markdown('<div style="height:1px;background:rgba(255,255,255,.06);margin:12px 0;"></div>', unsafe_allow_html=True)
    st.markdown('<p style="font-family:\'DM Mono\',monospace;font-size:10px;color:rgba(255,255,255,.25);margin-bottom:8px;">ACTIVE NAMESPACES</p>', unsafe_allow_html=True)
    all_ns = list_namespaces()
    if all_ns:
        selected_ns = st.multiselect("ns_sel", options=["all"]+all_ns, default=all_ns[:1], label_visibility="collapsed")
        for ns in all_ns:
            c1,c2=st.columns([5,1])
            c1.markdown(f'<div style="font-family:\'DM Mono\',monospace;font-size:11px;color:rgba(255,255,255,.4);">{ns} <span style="color:#63b3ff">· {get_doc_count(ns)}</span></div>', unsafe_allow_html=True)
            if c2.button("✕",key=f"del_{ns}"): delete_namespace(ns); st.rerun()
    else:
        selected_ns=[]; st.markdown('<p style="font-family:\'DM Mono\',monospace;font-size:11px;color:rgba(255,255,255,.2);">No documents loaded</p>', unsafe_allow_html=True)

    st.markdown('<div style="height:1px;background:rgba(255,255,255,.06);margin:12px 0;"></div>', unsafe_allow_html=True)
    st.markdown('<p style="font-family:\'DM Mono\',monospace;font-size:10px;color:rgba(255,255,255,.25);margin-bottom:6px;">OUTPUT FORMAT</p>', unsafe_allow_html=True)
    output_format = st.selectbox("fmt", ["generic","cisco","juniper","ansible"], label_visibility="collapsed")

    st.markdown('<div style="height:1px;background:rgba(255,255,255,.06);margin:12px 0;"></div>', unsafe_allow_html=True)
    from src.config import PARSER_MODEL, GEN_MODEL
    st.markdown(f"""<div style="font-family:'DM Mono',monospace;font-size:10px;line-height:2.2;color:rgba(255,255,255,.2);">
      PARSER&nbsp;&nbsp;&nbsp;<span style="color:#63b3ff">{PARSER_MODEL}</span><br>
      GENERATOR&nbsp;<span style="color:#63b3ff">{GEN_MODEL}</span><br>
      CLOUD API&nbsp;&nbsp;<span style="color:#4ade80">none</span></div>""", unsafe_allow_html=True)

# ── TABS ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["⬡  GENERATE CONFIG", "◈  METRICS & TIMING", "⊞  MODEL COMPARISON"])

# ══ TAB 1: GENERATE ══════════════════════════════════════════════════════════
with tab1:
    st.markdown('<div style="font-family:\'Syncopate\',sans-serif;font-size:9.5px;font-weight:700;color:#63b3ff;letter-spacing:.2em;margin:14px 0 10px;">NETWORK INTENT</div>', unsafe_allow_html=True)
    examples = [
        "Deny all TCP from 10.0.0.0/8 to 192.168.1.100 port 22",
        "Permit HTTP from 192.168.10.0/24 to 10.0.1.5 between 09:00 and 18:00",
        "Block ICMP from any to 172.16.0.0/16 after 22:00",
        "Allow DNS from 192.168.0.0/16 to 8.8.8.8 port 53",
    ]
    with st.expander("Examples"):
        for ex in examples:
            if st.button(ex,key=f"ex_{ex}"): st.session_state["intent_input"]=ex

    intent_text=st.text_area("intent",value=st.session_state.get("intent_input",""),
        placeholder='"Block all SSH from Sales VLAN to Finance server between 21:00 and 06:00"',
        height=90,label_visibility="collapsed")

    c1,c2=st.columns([2,5])
    with c1:
        go=st.button("⬡  GENERATE",type="primary",use_container_width=True,
                     disabled=not intent_text.strip() or not selected_ns)
    with c2:
        if not selected_ns:
            st.markdown('<p style="font-family:\'DM Mono\',monospace;font-size:11px;color:#fbbf24;padding:10px 0;">⚠  load a knowledge base first</p>',unsafe_allow_html=True)

    if go and intent_text.strip() and selected_ns:
        st.markdown('<div style="height:1px;background:linear-gradient(90deg,transparent,rgba(99,179,255,.2),transparent);margin:18px 0 14px;"></div>',unsafe_allow_html=True)
        c1,c2,c3=st.columns([1,1.4,.85])

        with c1:
            st.markdown('<div style="font-family:\'Syncopate\',sans-serif;font-size:8.5px;font-weight:700;color:#67e8f9;letter-spacing:.2em;margin-bottom:10px;">01 · PARSED INTENT</div>',unsafe_allow_html=True)
            t0=time.perf_counter()
            with st.spinner("Parsing..."): intent_json=parse_intent(intent_text)
            parse_ms=round((time.perf_counter()-t0)*1000)
            if "error" in intent_json: st.error(f"Parse failed · {intent_json.get('raw','')[:80]}"); st.stop()
            st.json(intent_json)
            st.markdown(f'<p style="font-family:\'DM Mono\',monospace;font-size:10px;color:rgba(255,255,255,.2);">parse time: {parse_ms}ms</p>',unsafe_allow_html=True)

        with c2:
            st.markdown('<div style="font-family:\'Syncopate\',sans-serif;font-size:8.5px;font-weight:700;color:#67e8f9;letter-spacing:.2em;margin-bottom:10px;">02 · GENERATED CONFIG</div>',unsafe_allow_html=True)
            t1=time.perf_counter()
            with st.spinner("Generating..."): config=generate_config(intent_json,namespaces=selected_ns,output_format=output_format)
            gen_ms=round((time.perf_counter()-t1)*1000)
            st.code(config,language="text")
            st.markdown(f'<p style="font-family:\'DM Mono\',monospace;font-size:10px;color:rgba(255,255,255,.2);">gen time: {gen_ms}ms</p>',unsafe_allow_html=True)
            st.download_button("⬇  EXPORT",data=config,file_name="ibn_config.txt",mime="text/plain")

        with c3:
            t2=time.perf_counter()
            result=validate(config)
            val_ms=round((time.perf_counter()-t2)*1000)
            total_ms=parse_ms+gen_ms+val_ms
            st.markdown('<div style="font-family:\'Syncopate\',sans-serif;font-size:8.5px;font-weight:700;color:#67e8f9;letter-spacing:.2em;margin-bottom:10px;">03 · SAFETY REPORT</div>',unsafe_allow_html=True)
            sc=result.score
            if sc>=70: rc,lb,bg="#4ade80","SAFE","rgba(74,222,128,.08)"
            elif sc>=40: rc,lb,bg="#fbbf24","REVIEW","rgba(251,191,36,.08)"
            else: rc,lb,bg="#f87171","BLOCKED","rgba(248,113,113,.08)"
            st.markdown(f"""<div style="background:{bg};border:1px solid {rc}33;border-radius:16px;padding:20px 14px;text-align:center;margin-bottom:10px;box-shadow:0 0 35px {rc}18;">
              <div style="width:82px;height:82px;border-radius:50%;border:2px solid {rc};margin:0 auto 10px;
                display:flex;align-items:center;justify-content:center;flex-direction:column;
                box-shadow:0 0 25px {rc}44;background:rgba(0,0,0,.35);">
                <div style="font-family:'Syncopate',sans-serif;font-size:23px;font-weight:700;color:{rc};line-height:1;">{sc}</div>
                <div style="font-family:'DM Mono',monospace;font-size:9px;color:{rc}99;">/100</div>
              </div>
              <div style="font-family:'Syncopate',sans-serif;font-size:9px;font-weight:700;color:{rc};letter-spacing:.2em;">{lb}</div>
            </div>""",unsafe_allow_html=True)
            if result.safe: st.success("Cleared for deployment")
            else: st.error("Deployment blocked")
            for issue in result.issues: st.error(f"✕  {issue}")
            for w in result.warnings: st.warning(f"△  {w}")
            st.markdown(f'<p style="font-family:\'DM Mono\',monospace;font-size:10px;color:rgba(255,255,255,.2);margin-top:6px;">total: {total_ms}ms</p>',unsafe_allow_html=True)

        if "history" not in st.session_state: st.session_state.history=[]
        st.session_state.history.insert(0,{
            "intent":intent_text,"score":sc,"format":output_format,"ns":selected_ns,
            "parse_ms":parse_ms,"gen_ms":gen_ms,"val_ms":val_ms,"total_ms":total_ms
        })

    if st.session_state.get("history"):
        st.markdown('<div style="height:1px;background:linear-gradient(90deg,transparent,rgba(99,179,255,.15),transparent);margin:22px 0 14px;"></div>',unsafe_allow_html=True)
        st.markdown('<div style="font-family:\'Syncopate\',sans-serif;font-size:9px;font-weight:700;color:#63b3ff;letter-spacing:.2em;margin-bottom:10px;">SESSION LOG</div>',unsafe_allow_html=True)
        for h in st.session_state.history[:5]:
            sc2=h["score"]; dot="#4ade80" if sc2>=70 else "#fbbf24" if sc2>=40 else "#f87171"
            with st.expander(f"{h['intent'][:65]}..."):
                st.markdown(f'<div style="font-family:\'DM Mono\',monospace;font-size:11px;color:rgba(255,255,255,.4);">score <span style="color:{dot}">{sc2}</span> · {h.get("total_ms",0)}ms total · {h["format"]} · {" · ".join(h["ns"])}</div>',unsafe_allow_html=True)

# ══ TAB 2: METRICS & TIMING ═══════════════════════════════════════════════════
with tab2:
    st.markdown('<div style="font-family:\'Syncopate\',sans-serif;font-size:9.5px;font-weight:700;color:#63b3ff;letter-spacing:.2em;margin:14px 0 16px;">PERFORMANCE METRICS DASHBOARD</div>',unsafe_allow_html=True)

    if st.session_state.get("history"):
        hist=st.session_state.history
        avg_parse=sum(h.get("parse_ms",0) for h in hist)/len(hist)
        avg_gen=sum(h.get("gen_ms",0) for h in hist)/len(hist)
        avg_val=sum(h.get("val_ms",0) for h in hist)/len(hist)
        avg_total=sum(h.get("total_ms",0) for h in hist)/len(hist)
        avg_score=sum(h.get("score",0) for h in hist)/len(hist)

        m1,m2,m3,m4,m5=st.columns(5)
        def metric_card(col,label,val,unit=""):
            col.markdown(f"""<div style="background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.09);
              border-top:2px solid #63b3ff;border-radius:10px;padding:14px 12px;text-align:center;">
              <div style="font-family:'Syncopate',sans-serif;font-size:18px;font-weight:700;color:#63b3ff;">{val}{unit}</div>
              <div style="font-family:'DM Mono',monospace;font-size:9px;color:rgba(255,255,255,.35);margin-top:4px;letter-spacing:.08em;">{label}</div>
            </div>""",unsafe_allow_html=True)

        metric_card(m1,"PARSE TIME",f"{avg_parse:.0f}","ms")
        metric_card(m2,"GEN TIME",f"{avg_gen:.0f}","ms")
        metric_card(m3,"VALIDATE",f"{avg_val:.0f}","ms")
        metric_card(m4,"TOTAL TIME",f"{avg_total:.0f}","ms")
        metric_card(m5,"AVG RISK SCORE",f"{avg_score:.0f}","/100")

        st.markdown('<div style="height:1px;background:rgba(255,255,255,.06);margin:20px 0 14px;"></div>',unsafe_allow_html=True)
        st.markdown('<div style="font-family:\'Syncopate\',sans-serif;font-size:9px;color:#63b3ff;letter-spacing:.18em;margin-bottom:12px;">TIMING BREAKDOWN — ALL RUNS</div>',unsafe_allow_html=True)

        import pandas as pd
        df=pd.DataFrame([{
            "Intent":h["intent"][:40]+"...",
            "Parse (ms)":h.get("parse_ms",0),
            "Generate (ms)":h.get("gen_ms",0),
            "Validate (ms)":h.get("val_ms",0),
            "Total (ms)":h.get("total_ms",0),
            "Risk Score":h.get("score",0),
        } for h in hist])
        st.dataframe(df,use_container_width=True)

        st.markdown('<div style="height:1px;background:rgba(255,255,255,.06);margin:16px 0 12px;"></div>',unsafe_allow_html=True)
        st.markdown('<div style="font-family:\'Syncopate\',sans-serif;font-size:9px;color:#63b3ff;letter-spacing:.18em;margin-bottom:10px;">TIMING CHART</div>',unsafe_allow_html=True)
        chart_df=pd.DataFrame({"Step":["Parse","Generate","Validate"],"Time (ms)":[avg_parse,avg_gen,avg_val]})
        st.bar_chart(chart_df.set_index("Step"))

        results_path=ROOT/"results"/"eval_results.csv"
        if results_path.exists():
            st.markdown('<div style="height:1px;background:rgba(255,255,255,.06);margin:16px 0 12px;"></div>',unsafe_allow_html=True)
            st.markdown('<div style="font-family:\'Syncopate\',sans-serif;font-size:9px;color:#63b3ff;letter-spacing:.18em;margin-bottom:10px;">BENCHMARK EVALUATION RESULTS</div>',unsafe_allow_html=True)
            eval_df=pd.read_csv(results_path)
            st.dataframe(eval_df,use_container_width=True)
    else:
        st.info("Run at least one intent generation to see metrics here.")
        st.markdown("""<div style="font-family:'DM Mono',monospace;font-size:12px;color:rgba(255,255,255,.4);margin-top:16px;line-height:2;">
        To populate the benchmark evaluation table:<br>
        1. Go to your terminal<br>
        2. Run: <span style="color:#63b3ff">python scripts/run_evaluation.py</span><br>
        3. Results appear here automatically
        </div>""",unsafe_allow_html=True)

# ══ TAB 3: MODEL COMPARISON ═══════════════════════════════════════════════════
with tab3:
    st.markdown('<div style="font-family:\'Syncopate\',sans-serif;font-size:9.5px;font-weight:700;color:#63b3ff;letter-spacing:.2em;margin:14px 0 16px;">MODEL COMPARISON</div>',unsafe_allow_html=True)

    AVAILABLE_MODELS=["tinyllama","phi3:mini","qwen2.5-coder:0.5b","qwen2.5-coder:1.5b","gemma2:2b","mistral:7b-q2_k"]
    ca,cb=st.columns(2)
    with ca:
        st.markdown('<p style="font-family:\'DM Mono\',monospace;font-size:10px;color:rgba(255,255,255,.3);margin-bottom:6px;">MODEL A</p>',unsafe_allow_html=True)
        model_a=st.selectbox("mA",AVAILABLE_MODELS,index=0,label_visibility="collapsed")
    with cb:
        st.markdown('<p style="font-family:\'DM Mono\',monospace;font-size:10px;color:rgba(255,255,255,.3);margin-bottom:6px;">MODEL B</p>',unsafe_allow_html=True)
        model_b=st.selectbox("mB",AVAILABLE_MODELS,index=1,label_visibility="collapsed")

    cmp_intent=st.text_area("cmp_intent",
        placeholder="Type an intent to compare both models...",
        height=80,label_visibility="collapsed")

    if st.button("⊞  COMPARE MODELS",type="primary",disabled=not cmp_intent.strip() or not selected_ns):
        results={}
        for label,model in [("A",model_a),("B",model_b)]:
            import os; os.environ["PARSER_MODEL"]=model; os.environ["GEN_MODEL"]=model
            import importlib, src.config as cfg_mod, src.intent_parser as ip_mod, src.config_generator as cg_mod
            importlib.reload(cfg_mod); importlib.reload(ip_mod); importlib.reload(cg_mod)
            t0=time.perf_counter()
            ij=ip_mod.parse_intent(cmp_intent); pt=round((time.perf_counter()-t0)*1000)
            t1=time.perf_counter()
            cfg=cg_mod.generate_config(ij,namespaces=selected_ns,output_format="cisco"); gt=round((time.perf_counter()-t1)*1000)
            res=validate(cfg)
            results[label]={"model":model,"intent_json":ij,"config":cfg,"score":res.score,"safe":res.safe,"parse_ms":pt,"gen_ms":gt,"total_ms":pt+gt}

        st.markdown('<div style="height:1px;background:linear-gradient(90deg,transparent,rgba(99,179,255,.2),transparent);margin:16px 0 14px;"></div>',unsafe_allow_html=True)
        col_a,col_b=st.columns(2)
        for col,(label,r) in zip([col_a,col_b],results.items()):
            with col:
                sc=r["score"]; rc="#4ade80" if sc>=70 else "#fbbf24" if sc>=40 else "#f87171"
                st.markdown(f'<div style="font-family:\'Syncopate\',sans-serif;font-size:9px;font-weight:700;color:#67e8f9;letter-spacing:.2em;margin-bottom:8px;">MODEL {label}: {r["model"].upper()}</div>',unsafe_allow_html=True)
                st.markdown(f"""<div style="display:flex;gap:10px;margin-bottom:10px;">
                  <div style="background:rgba(99,179,255,.08);border:1px solid rgba(99,179,255,.2);border-radius:8px;padding:8px 12px;text-align:center;flex:1;">
                    <div style="font-family:'Syncopate',sans-serif;font-size:14px;color:#63b3ff;">{r["parse_ms"]}ms</div>
                    <div style="font-family:'DM Mono',monospace;font-size:9px;color:rgba(255,255,255,.3);">PARSE</div></div>
                  <div style="background:rgba(99,179,255,.08);border:1px solid rgba(99,179,255,.2);border-radius:8px;padding:8px 12px;text-align:center;flex:1;">
                    <div style="font-family:'Syncopate',sans-serif;font-size:14px;color:#63b3ff;">{r["gen_ms"]}ms</div>
                    <div style="font-family:'DM Mono',monospace;font-size:9px;color:rgba(255,255,255,.3);">GENERATE</div></div>
                  <div style="background:{rc}11;border:1px solid {rc}33;border-radius:8px;padding:8px 12px;text-align:center;flex:1;">
                    <div style="font-family:'Syncopate',sans-serif;font-size:14px;color:{rc};">{sc}</div>
                    <div style="font-family:'DM Mono',monospace;font-size:9px;color:rgba(255,255,255,.3);">RISK</div></div>
                </div>""",unsafe_allow_html=True)
                st.json(r["intent_json"])
                st.code(r["config"],language="text")
                if r["safe"]: st.success("Safe")
                else: st.error("Blocked")
