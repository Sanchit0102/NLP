import streamlit as st
import pandas as pd
import plotly.express as px
import spacy
import language_tool_python
from spellchecker import SpellChecker
from collections import Counter
from pathlib import Path
import re

st.set_page_config(page_title="SmartSpell | NLP Assistant", page_icon="✍️", layout="wide")

# ---------- Styling ----------
st.markdown("""
<style>
    .stApp { background: #f5f7fb; }
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1400px; }
    .hero {
        background: linear-gradient(120deg, #14213d 0%, #234e70 100%);
        color: white; padding: 28px 32px; border-radius: 18px; margin-bottom: 22px;
    }
    .hero h1 { color: white; margin: 0; font-size: 2.15rem; }
    .hero p { color: #dbeafe; margin: 8px 0 0 0; font-size: 1rem; }
    .metric-card {
        background: white; border: 1px solid #e5eaf2; padding: 16px 18px;
        border-radius: 14px; box-shadow: 0 2px 8px rgba(25, 45, 80, .04);
    }
    .section-title { font-size: 1.15rem; font-weight: 700; color: #172b4d; margin: 4px 0 12px 0; }
    .small-muted { color: #68778d; font-size: .88rem; }
    div[data-testid="stMetric"] {
        background: white; border: 1px solid #e5eaf2; padding: 12px 16px;
        border-radius: 13px;
    }
    .stButton > button { border-radius: 10px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def load_nlp():
    return spacy.load("en_core_web_sm")

@st.cache_resource
def load_spellchecker():
    return SpellChecker()

@st.cache_resource
def load_grammar_tool():
    # LanguageTool may require internet access / Java depending on setup.
    return language_tool_python.LanguageTool("en-US")

try:
    nlp = load_nlp()
    nlp_error = None
except Exception as e:
    nlp = None
    nlp_error = str(e)

try:
    spell = load_spellchecker()
except Exception:
    spell = None

st.markdown("""
<div class="hero">
  <h1>SmartSpell</h1>
  <p>Smart spelling and grammar assistant powered by Natural Language Processing</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## SmartSpell")
    st.caption("NLP-powered writing workspace")
    page = st.radio("Navigation", ["Writing Assistant", "NLP Analysis", "About Project"])
    st.divider()
    st.markdown("### Settings")
    check_spelling = st.checkbox("Check spelling", value=True)
    check_grammar = st.checkbox("Check grammar", value=True)
    st.caption("Grammar checking uses LanguageTool. The first run may take time.")

@st.cache_data
def load_demo_sentences():
    return pd.read_csv(Path(__file__).parent / "demo_sentences.csv").fillna("")

demo_df = load_demo_sentences()

@st.cache_data
def load_demo_sentences():
    return pd.read_csv("demo_sentences.csv").fillna("")

def select_demo_sentence():
    choice = st.session_state.get("demo_choice", "")
    if choice and choice != "Custom text":
        st.session_state["input_text"] = DEMO_LOOKUP[choice]
        st.session_state["analysis_done"] = False
        st.session_state["corrected_text"] = ""

DEMO_DATA = load_demo_sentences()
DEMO_LOOKUP = {
    f"{row.category} | {row.scenario}": row.sentence
    for row in DEMO_DATA.itertuples(index=False)
}

if "corrected_text" not in st.session_state:
    st.session_state.corrected_text = ""

if page == "Writing Assistant":
    st.markdown('<div class="section-title">Writing workspace</div>', unsafe_allow_html=True)
    left, right = st.columns([1.15, 0.85], gap="large")

    with left:
        st.markdown("#### Faculty demo sentences")
        categories = ["All"] + sorted(demo_df["category"].unique().tolist())
        selected_category = st.selectbox("Choose an error category", categories)
        filtered = demo_df if selected_category == "All" else demo_df[demo_df["category"] == selected_category]
        options = filtered.index.tolist()
        selected_idx = st.selectbox(
            "Select a ready-made example",
            options,
            format_func=lambda i: f"{demo_df.loc[i, 'category']} — {demo_df.loc[i, 'title']}"
        )
        selected_example = demo_df.loc[selected_idx]
        if st.button("Load example into editor", use_container_width=True):
            st.session_state["input_text"] = selected_example["input_text"]
            st.session_state["expected_demo"] = selected_example["expected_correction"]
            st.session_state["analysis_done"] = False
            st.rerun()
        with st.expander("Expected correction for selected example"):
            st.write(selected_example["expected_correction"])
            st.caption("Reference answer for demonstration; actual predictions may differ.")
        st.selectbox(
            "Faculty demo examples (select a sentence)",
            options=["Custom text"] + list(DEMO_LOOKUP),
            key="demo_choice",
            on_change=select_demo_sentence,
        )
        st.caption("22 ready-made examples: spelling, grammar, mixed errors, and correct sentences.")
        if "input_text" not in st.session_state:
            st.session_state["input_text"] = DEMO_LOOKUP["Mixed | Classroom demonstration"]
        text = st.text_area(
            "Enter or paste your text",
            height=240,
            placeholder="Type your paragraph here...",
            key="input_text"
        )
        run = st.button("Analyze text", type="primary", use_container_width=True)

        if run:
            spelling_rows = []
            grammar_rows = []
            corrected = text

            if check_spelling and spell and text.strip():
                # Word-level spelling suggestions. Preserve original capitalization.
                tokens = re.findall(r"\b[A-Za-z]+\b", text)
                for word in tokens:
                    if word.lower() not in spell:
                        suggestion = spell.correction(word.lower())
                        if suggestion and suggestion.lower() != word.lower():
                            spelling_rows.append({
                                "Original": word,
                                "Suggestion": suggestion,
                                "Type": "Spelling"
                            })
                            corrected = re.sub(
                                rf"\b{re.escape(word)}\b",
                                suggestion.capitalize() if word[:1].isupper() else suggestion,
                                corrected,
                                count=1
                            )

            if check_grammar and text.strip():
                try:
                    tool = load_grammar_tool()
                    # Check the spelling-corrected version so offsets match the text being edited.
                    grammar_input = corrected
                    matches = tool.check(grammar_input)
                    for match in matches:
                        replacements = ", ".join(match.replacements[:3]) if match.replacements else "Review manually"
                        grammar_rows.append({
                            "Original text": grammar_input[match.offset:match.offset + match.errorLength],
                            "Suggestion": replacements,
                            "Rule": match.ruleId,
                            "Message": match.message
                        })
                    corrected = language_tool_python.utils.correct(grammar_input, matches)
                except Exception as e:
                    st.warning(f"Grammar service could not be reached. Spelling and NLP analysis can still be used. Details: {e}")

            st.session_state["spelling_rows"] = spelling_rows
            st.session_state["grammar_rows"] = grammar_rows
            st.session_state["corrected_text"] = corrected
            st.session_state["analysis_done"] = True

    with right:
        st.markdown('<div class="section-title">Corrected version</div>', unsafe_allow_html=True)
        if st.session_state.get("analysis_done"):
            st.text_area("Suggested text", value=st.session_state.corrected_text, height=240)
            st.download_button(
                "Download corrected text",
                data=st.session_state.corrected_text,
                file_name="smartspell_corrected.txt",
                mime="text/plain",
                use_container_width=True
            )
        else:
            st.info("Your corrected text will appear here after analysis.")
            st.markdown("**What SmartSpell checks**")
            st.markdown("- Possible spelling mistakes\n- Common grammar issues\n- NLP features such as lemmas and POS tags")

    if st.session_state.get("analysis_done"):
        spelling_rows = st.session_state.get("spelling_rows", [])
        grammar_rows = st.session_state.get("grammar_rows", [])
        words = re.findall(r"\b\w+\b", text)
        sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Words", len(words))
        c2.metric("Sentences", len(sentences))
        c3.metric("Spelling suggestions", len(spelling_rows))
        c4.metric("Grammar matches", len(grammar_rows))

        st.markdown('<div class="section-title">Detected issues</div>', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Spelling", "Grammar"])
        with tab1:
            if spelling_rows:
                st.dataframe(pd.DataFrame(spelling_rows), use_container_width=True, hide_index=True)
            else:
                st.success("No spelling suggestions found.")
        with tab2:
            if grammar_rows:
                st.dataframe(pd.DataFrame(grammar_rows), use_container_width=True, hide_index=True)
            else:
                st.info("No grammar matches were returned, or grammar checking is unavailable.")

elif page == "NLP Analysis":
    st.markdown('<div class="section-title">Linguistic analysis</div>', unsafe_allow_html=True)
    analysis_text = st.text_area(
        "Text to analyze",
        value=st.session_state.get("input_text", "The students are studying natural language processing."),
        height=160,
        key="nlp_text"
    )
    if st.button("Run NLP analysis", type="primary"):
        if nlp is None:
            st.error("spaCy model is not installed. Run: python -m spacy download en_core_web_sm")
        elif not analysis_text.strip():
            st.warning("Enter some text first.")
        else:
            doc = nlp(analysis_text)
            rows = []
            for token in doc:
                if not token.is_space:
                    rows.append({
                        "Token": token.text,
                        "Lemma": token.lemma_,
                        "POS": token.pos_,
                        "Detailed tag": token.tag_,
                        "Dependency": token.dep_,
                        "Is stop word": token.is_stop,
                        "Is alphabetic": token.is_alpha
                    })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### Word frequency")
                words = [t.lemma_.lower() for t in doc if t.is_alpha and not t.is_stop]
                counts = Counter(words)
                if counts:
                    freq_df = pd.DataFrame(counts.most_common(12), columns=["Lemma", "Frequency"])
                    fig = px.bar(freq_df, x="Lemma", y="Frequency", title="Most frequent content words")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No content words to plot.")
            with col2:
                st.markdown("#### Part-of-speech distribution")
                pos_counts = Counter(t.pos_ for t in doc if not t.is_space and t.is_alpha)
                if pos_counts:
                    pos_df = pd.DataFrame(pos_counts.items(), columns=["POS", "Count"])
                    fig = px.pie(pos_df, names="POS", values="Count", hole=0.45, title="POS distribution")
                    st.plotly_chart(fig, use_container_width=True)

            st.markdown("#### Simple morphology view")
            morph_rows = []
            for token in doc:
                if token.is_alpha:
                    morph_rows.append({
                        "Word": token.text,
                        "Lemma / base form": token.lemma_,
                        "Suffix (heuristic)": token.text[len(token.lemma_):] if token.text.lower().startswith(token.lemma_.lower()) and len(token.text) > len(token.lemma_) else "(not inferred)"
                    })
            st.dataframe(pd.DataFrame(morph_rows), use_container_width=True, hide_index=True)
            st.caption("Suffix display is a simple heuristic, not a full morphological parser.")

elif page == "About Project":
    st.markdown("## About SmartSpell")
    st.write(
        "SmartSpell is a student mini-project that applies Natural Language Processing "
        "to identify possible spelling and grammar issues and display linguistic features."
    )
    st.markdown("### Demo dataset")
    st.dataframe(demo_df, use_container_width=True, hide_index=True)
    st.download_button("Download demo dataset CSV", demo_df.to_csv(index=False), "demo_sentences.csv", "text/csv")
    st.markdown("### Faculty demonstration dataset")
    st.dataframe(DEMO_DATA, use_container_width=True, hide_index=True)
    st.download_button("Download demo dataset", DEMO_DATA.to_csv(index=False), "demo_sentences.csv", "text/csv")
    st.markdown("### NLP concepts demonstrated")
    st.markdown("""
    - Tokenization and text normalization
    - Spelling correction using candidate suggestions
    - Minimum Edit Distance (can be added as an explicit correction-ranking module)
    - Grammar checking using LanguageTool
    - Lemmatization and Part-of-Speech tagging with spaCy
    - Stop-word analysis and word-frequency visualization
    - Evaluation on a labelled test dataset
    """)
    st.warning(
        "This is an educational assistant, not a perfect proofreader. Spelling suggestions can be wrong "
        "for names, technical terms, and context-dependent words. Review changes before using them."
    )

if nlp_error:
    with st.sidebar:
        st.error("spaCy model unavailable. Install it using the setup commands in README.")
