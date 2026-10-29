# SmartSpell NLP Dashboard

## Requirements
- Python 3.10–3.12 recommended
- Internet connection for LanguageTool service on first use / remote checks

## Setup (Windows PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m spacy download en_core_web_sm
streamlit run app.py
```

If PowerShell blocks activation, run the executable directly:
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m spacy download en_core_web_sm
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## Features
- Spelling suggestions with pyspellchecker
- Grammar suggestions via LanguageTool
- Corrected text panel and download button
- spaCy token, lemma, POS, dependency and stop-word analysis
- Word-frequency and POS charts

## Notes
- Grammar checking requires a working LanguageTool service and may be slow on first use.
- The spelling engine may flag names and domain-specific words.
- The displayed suffix analysis is heuristic, not full morphological analysis.
- Always review suggestions before accepting them.
