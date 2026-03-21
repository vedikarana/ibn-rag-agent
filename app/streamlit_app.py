import sys
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st

from src.intent_parser import parse_intent
from src.config_generator import generate_config
from src.safety_validator import validate
from src.document_manager import (
    ingest_document,
    list_namespaces,
    get_doc_count,
    delete_namespace,
)

st.set_page_config(page_title="IBN-RAG Agent", page_icon="shield", layout="wide")

st.title("IBN-RAG — Intent-Based Networking Agent")
st.caption("Upload any network documentation · Type your intent · Get verified configuration")

with st.sidebar:
    st.header("Knowledge Base")

    uploaded_files = st.file_uploader(
        "Upload documents (PDF or TXT)",
        type=["pdf", "txt", "md"],
        accept_multiple_files=True,
    )
    ns_name = st.text_input("Tag for these documents", placeholder="e.g. cisco, paloalto, my_runbook")

    if st.button("Ingest documents", use_container_width=True):
        if not uploaded_files:
            st.warning("Please upload at least one file.")
        elif not ns_name.strip():
            st.warning("Please enter a tag name.")
        else:
            total_chunks = 0
            progress = st.progress(0, text="Starting...")
            for i, f in enumerate(uploaded_files):
                progress.progress(i / len(uploaded_files), text=f"Processing {f.name}...")
                suffix = Path(f.name).suffix
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(f.read())
                    tmp_path = tmp.name
                try:
                    count = ingest_document(tmp_path, namespace=ns_name.strip())
                    total_chunks += count
                finally:
                    os.unlink(tmp_path)
            progress.progress(1.0, text="Done!")
            st.success(f"Stored {total_chunks} new chunks under '{ns_name.strip()}'")
            st.rerun()

    st.divider()

    st.markdown("**Select knowledge bases to query**")
    all_ns = list_namespaces()

    if all_ns:
        selected_ns = st.multiselect(
            "Active knowledge bases",
            options=["all"] + all_ns,
            default=all_ns[:1],
        )
        st.markdown("**Manage**")
        for ns in all_ns:
            col_a, col_b = st.columns([4, 1])
            col_a.caption(f"{ns} — {get_doc_count(ns)} chunks")
            if col_b.button("Del", key=f"del_{ns}"):
                delete_namespace(ns)
                st.success(f"Deleted '{ns}'")
                st.rerun()
    else:
        selected_ns = []
        st.info("No documents yet. Upload some above to get started.")

    st.divider()
    st.markdown("**Output settings**")
    output_format = st.selectbox("Config format", ["generic", "cisco", "juniper", "ansible"])
    st.markdown("**Models**")
    st.code("Parser:    phi3.5\nGenerator: qwen2.5-coder:1.5b", language="text")

st.subheader("Enter your network intent")

example_intents = [
    "Block all SSH traffic from 10.0.0.0/8 to the finance server",
    "Allow HTTP from Sales VLAN to web server between 9 AM and 6 PM only",
    "Deny ICMP from any source to 192.168.100.0/24 after business hours",
    "Permit DNS queries from internal hosts to the primary DNS server",
]

with st.expander("Show example intents"):
    for ex in example_intents:
        if st.button(ex, key=f"ex_{ex}"):
            st.session_state["intent_input"] = ex

intent_text = st.text_area(
    "Intent",
    value=st.session_state.get("intent_input", ""),
    placeholder="e.g. Block all SSH traffic from Sales VLAN to Finance server between 9 PM and 6 AM",
    height=100,
    label_visibility="collapsed",
)

generate_btn = st.button(
    "Generate Configuration",
    type="primary",
    disabled=not intent_text.strip() or not selected_ns,
)

if not selected_ns:
    st.warning("Upload documents and select a knowledge base in the sidebar first.")

if generate_btn and intent_text.strip() and selected_ns:

    col1, col2, col3 = st.columns([1, 1.2, 1])

    with col1:
        with st.spinner("Parsing intent..."):
            intent_json = parse_intent(intent_text)
        st.subheader("Parsed Intent")
        if "error" in intent_json:
            st.error(f"Parse failed: {intent_json.get('raw', '')}")
            st.stop()
        st.json(intent_json)

    with col2:
        with st.spinner("Retrieving docs and generating config..."):
            config = generate_config(
                intent_json,
                namespaces=selected_ns,
                output_format=output_format,
            )
        st.subheader("Generated Configuration")
        st.code(config, language="text")
        st.download_button(
            "Download config",
            data=config,
            file_name="network_config.txt",
            mime="text/plain",
        )

    with col3:
        result = validate(config)
        st.subheader("Safety Report")

        if result.score >= 70:
            st.success(f"Risk score: {result.score} / 100")
        elif result.score >= 40:
            st.warning(f"Risk score: {result.score} / 100")
        else:
            st.error(f"Risk score: {result.score} / 100")

        if result.safe:
            st.success("Safe to deploy")
        else:
            st.error("Review before deploying")

        for issue in result.issues:
            st.error(issue)
        for warn in result.warnings:
            st.warning(warn)

        st.caption(f"Knowledge bases used: {', '.join(selected_ns)}")

    if "history" not in st.session_state:
        st.session_state.history = []
    st.session_state.history.insert(0, {
        "intent": intent_text,
        "score": result.score,
        "format": output_format,
        "namespaces": selected_ns,
    })

if st.session_state.get("history"):
    st.divider()
    st.subheader("Session History")
    for h in st.session_state.history[:8]:
        label = "OK" if h["score"] >= 70 else "WARN" if h["score"] >= 40 else "RISK"
        with st.expander(f"[{label}] {h['intent'][:60]}... — score {h['score']}/100"):
            st.write(f"Format: {h['format']}")
            st.write(f"Knowledge bases: {', '.join(h['namespaces'])}")