# PDF Parser

A machine learning pipeline for extracting and semantically translating documents into structured JSON formats.

## Overview

This project provides a two-step pipeline:

1. **Step 1 - Extraction**: Parse PDF documents to extract structured sections with numbering, hierarchy, titles, and body text
2. **Step 2 - Semantic Translation**: Use OpenAI's GPT model to translate legal/regulatory text into plain English components

## Technical Approach

### Step 1: Heuristic-Based Section Extraction

**Why this approach?**

Legal/regulatory documents like zoning bylaws follow predictable structural patterns but vary in formatting across jurisdictions. A rule-based heuristic approach was chosen because:

1. **Deterministic output**: Same input always produces same output, critical for legal document processing
2. **No training data required**: Works immediately on new document types without labeled datasets
3. **Interpretable**: Easy to debug and adjust rules when extraction fails
4. **Low latency**: No model inference overhead, processes documents in milliseconds

**How it works:**

| Component | Method | Purpose |
|-----------|--------|---------|
| **PDF Text Extraction** | `pdfplumber` library | Extracts text while preserving layout and reading order |
| **Section Detection** | Regex pattern `^\d+(?:\.\d+)*\s+` | Identifies numbered sections (1, 1.1, 2.2.1, etc.) |
| **Header/Footer Removal** | Frequency analysis | Detects text appearing on multiple pages and filters it |
| **Title vs Body Classification** | Multi-heuristic scoring | Distinguishes section titles from regulatory body text |
| **Hierarchy Derivation** | String parsing | Computes parent from section number (2.2.1 → parent: 2.2) |

**Title Detection Heuristics:**

The system uses negative filtering to identify body text, then classifies remaining short text as titles:

```
Body Text Indicators (NOT a title if any match):
├── Length > 60 characters or > 6 words
├── Ends with punctuation (: . , ;)
├── Contains parentheses, measurements (m², %), or section references
├── Starts with regulatory patterns:
│   ├── "A new...", "The...", "For the..."
│   ├── "If...", "Where...", "Unless...", "Except..."
│   ├── "No building may...", "All uses must..."
│   └── "Minimum...", "Maximum..."
└── Contains regulatory verbs (permitted, required, shall, must)

Title Indicators (IS a title if):
├── ALL CAPS with ≤5 words
├── Title Case with ≤5 words and no verbs
└── Short phrase (≤3 words) with proper capitalization
```

### Step 2: LLM-Based Semantic Translation

**Why this approach?**

Translating legal text to plain English requires understanding context, intent, and nuance. An LLM approach was chosen because:

1. **Semantic understanding**: LLMs comprehend legal language patterns and can rephrase them naturally
2. **Structured extraction**: Can identify conditions, requirements, and exceptions from complex sentences
3. **Flexibility**: Handles varied sentence structures without explicit rules for each pattern
4. **Quality**: Produces human-readable summaries that capture regulatory intent

**How it works:**

| Component | Method | Purpose |
|-----------|--------|---------|
| **Model** | OpenAI GPT API | Processes each section independently |
| **Prompt Engineering** | Structured JSON output prompt | Ensures consistent output format |
| **Temperature** | 0.1 (low) | Maximizes determinism and consistency |
| **Retry Logic** | 3 attempts with backoff | Handles transient API failures |
| **Response Parsing** | Regex + JSON parsing | Extracts valid JSON from model responses |

**Semantic Components Extracted:**

```
Input: Legal section text
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│                    GPT Processing                        │
│  ┌─────────────────────────────────────────────────┐    │
│  │ 1. Identify WHEN rule applies (condition)       │    │
│  │ 2. Identify WHAT must be done (requirement)     │    │
│  │ 3. Identify IF exceptions exist                 │    │
│  │ 4. Generate plain English summary               │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
         │
         ▼
Output: {
  "condition_english": "When does this apply?",
  "requirement_english": "What must be done?",
  "exception": { "condition": "...", "requirement": "..." },
  "description": "Plain English summary"
}
```

**Why separate steps instead of end-to-end LLM?**

1. **Cost efficiency**: Only sections with body text go to the LLM (reduces API calls by ~30%)
2. **Accuracy**: Structural extraction (section numbers, hierarchy) is deterministic
3. **Debuggability**: Can verify Step 1 output before incurring API costs
4. **Modularity**: Can swap LLM provider or use local models for Step 2

## Requirements

- Python 3.9+
- OpenAI API key

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Set your OpenAI API key as an environment variable:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

Or create a `.env` file in the project directory:

```
OPENAI_API_KEY=your-api-key-here
```

## Usage

### Web Interface (Recommended)

Launch the Streamlit application for an interactive experience:

```bash
streamlit run app.py
```

Features:
- Upload PDF documents via drag-and-drop
- View extracted sections with expandable content
- Real-time progress tracking during translation
- Search and filter sections
- Download JSON outputs

### Command Line Interface

#### Step 1: Extract Sections from PDF

```bash
python step1_extractor.py --input <pdf_path> --output <output_json_path>
```

**Example:**
```bash
python step1_extractor.py --input zoning-by-law-district-schedule-r1-1.pdf --output step1_output.json
```

**Output Format:**
```json
{
  "sections": [
    {
      "parent_section": "",
      "section": "2",
      "section_title": "USE REGULATIONS",
      "section_body_text": null,
      "section_start_page": 2,
      "section_end_page": 2
    },
    {
      "parent_section": "2.2",
      "section": "2.2.1",
      "section_title": null,
      "section_body_text": "A new multiple dwelling, duplex with secondary suite...",
      "section_start_page": 4,
      "section_end_page": 4
    }
  ]
}
```

#### Step 2: Translate Sections to Plain English

```bash
python step2_translator.py --input <step1_json_path> --output <output_json_path>
```

**Example:**
```bash
python step2_translator.py --input step1_output.json --output step2_output.json
```

**Optional Arguments:**
- `--api-key`: Provide API key directly instead of environment variable
- `--quiet`: Suppress progress output

**Output Format:**
```json
{
  "translated_sections": [
    {
      "id": "2.2.1",
      "description": "New multiple dwellings, duplexes with secondary suites, and similar housing types must meet tree retention requirements...",
      "condition_english": "Applies to new multiple dwelling, duplex with secondary suite, single detached house with secondary suite...",
      "requirement_english": "Sites under 15.1m wide must retain or plant at least one front-yard tree...",
      "exception": {
        "condition_english": "Site has no lane access.",
        "requirement_english": "Director of Planning may waive the tree requirement."
      }
    }
  ]
}
```

## Output Field Descriptions

### Step 1 Fields

| Field | Description |
|-------|-------------|
| `parent_section` | Parent section number (e.g., "2.2" for section "2.2.1"). Empty for top-level sections. |
| `section` | Section number identifier (e.g., "2.2.1") |
| `section_title` | Title of the section if present, null otherwise |
| `section_body_text` | Full text content of the section, null for header-only sections |
| `section_start_page` | Page number where the section begins |
| `section_end_page` | Page number where the section ends |

### Step 2 Fields

| Field | Description |
|-------|-------------|
| `id` | Section identifier matching Step 1 output |
| `description` | Plain English summary readable by non-experts |
| `condition_english` | When does this rule apply? What triggers it? |
| `requirement_english` | What must be done to comply with this section? |
| `exception` | Object with `condition_english` and `requirement_english` for exception clauses, null if none |

## Complete Pipeline Example

```bash
python step1_extractor.py \
    --input zoning-by-law-district-schedule-r1-1.pdf \
    --output step1_output.json

python step2_translator.py \
    --input step1_output.json \
    --output step2_output.json
```

## Project Structure

```
pdf_parser_poc/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── app.py                    # Streamlit web application
├── step1_extractor.py        # PDF section extraction module
├── step2_translator.py       # OpenAI semantic translation module
└── .env                      # Environment variables (create this)
```

## Model Configuration

The translator uses OpenAI's `gpt-5.2-2025-12-11` model. To use a different model, modify the `MODEL_NAME` constant in `step2_translator.py`.

## Error Handling

- Step 1 handles malformed PDFs gracefully and extracts what it can
- Step 2 includes retry logic for API failures (3 retries with exponential backoff)
- Failed translations produce fallback responses to maintain output consistency

## License

MIT License

