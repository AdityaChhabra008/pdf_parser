"""
Streamlit Web Application for PDF Parser

A beautiful web interface for extracting and translating zoning bylaw documents.
"""

import streamlit as st
import json
import tempfile
import os
import time
from pathlib import Path

from step1_extractor import ZoningPDFExtractor
from step2_translator import SemanticTranslator

st.set_page_config(
    page_title="PDF Section Parser",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    .stApp {
        font-family: 'Inter', sans-serif;
    }
    
    .main-header {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 40px rgba(30, 58, 95, 0.3);
    }
    
    .main-header h1 {
        color: #ffffff;
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.5px;
    }
    
    .main-header p {
        color: #a8c5e2;
        font-size: 1.1rem;
        margin: 0.5rem 0 0 0;
        font-weight: 400;
    }
    
    .step-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        transition: all 0.2s ease;
    }
    
    .step-card:hover {
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
        border-color: #cbd5e1;
    }
    
    .step-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 1rem;
    }
    
    .step-number {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        color: white;
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        font-size: 0.9rem;
    }
    
    .step-title {
        font-size: 1.25rem;
        font-weight: 600;
        color: #1e293b;
        margin: 0;
    }
    
    .section-item {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.75rem;
    }
    
    .section-number {
        background: #dbeafe;
        color: #1d4ed8;
        padding: 0.25rem 0.75rem;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
        margin-bottom: 0.5rem;
    }
    
    .section-title-text {
        color: #334155;
        font-weight: 500;
        font-size: 1rem;
    }
    
    .section-body {
        color: #64748b;
        font-size: 0.9rem;
        line-height: 1.6;
        margin-top: 0.5rem;
    }
    
    .stat-box {
        background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
        border: 1px solid #bae6fd;
        border-radius: 10px;
        padding: 1rem 1.25rem;
        text-align: center;
    }
    
    .stat-number {
        font-size: 2rem;
        font-weight: 700;
        color: #0369a1;
        line-height: 1;
    }
    
    .stat-label {
        font-size: 0.8rem;
        color: #0c4a6e;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 0.25rem;
    }
    
    .progress-item {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.75rem 1rem;
        background: #f8fafc;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        border-left: 3px solid #3b82f6;
    }
    
    .progress-item.completed {
        border-left-color: #10b981;
        background: #f0fdf4;
    }
    
    .progress-item.processing {
        border-left-color: #f59e0b;
        background: #fffbeb;
    }
    
    .translation-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1.25rem;
        margin-bottom: 1rem;
    }
    
    .translation-field {
        margin-bottom: 1rem;
    }
    
    .translation-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #64748b;
        margin-bottom: 0.25rem;
        font-weight: 600;
    }
    
    .translation-value {
        color: #1e293b;
        font-size: 0.95rem;
        line-height: 1.6;
    }
    
    .exception-box {
        background: #fef3c7;
        border: 1px solid #fcd34d;
        border-radius: 8px;
        padding: 1rem;
        margin-top: 0.5rem;
    }
    
    .download-btn {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 0.75rem 1.5rem;
        border-radius: 8px;
        font-weight: 600;
        text-decoration: none;
        display: inline-block;
        transition: all 0.2s ease;
    }
    
    .upload-area {
        border: 2px dashed #cbd5e1;
        border-radius: 12px;
        padding: 2rem;
        text-align: center;
        background: #f8fafc;
        transition: all 0.2s ease;
    }
    
    .upload-area:hover {
        border-color: #3b82f6;
        background: #eff6ff;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: #f1f5f9;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        color: white;
    }
</style>
""", unsafe_allow_html=True)


def render_header():
    st.markdown("""
    <div class="main-header">
        <h1>📄 PDF Section Parser</h1>
        <p>Extract and translate document sections into structured, readable formats</p>
    </div>
    """, unsafe_allow_html=True)


def render_stats(step1_data, step2_data=None):
    cols = st.columns(4)
    
    total_sections = len(step1_data.get('sections', []))
    sections_with_body = len([s for s in step1_data.get('sections', []) if s.get('section_body_text')])
    sections_with_title = len([s for s in step1_data.get('sections', []) if s.get('section_title')])
    translated = len(step2_data.get('translated_sections', [])) if step2_data else 0
    
    with cols[0]:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{total_sections}</div>
            <div class="stat-label">Total Sections</div>
        </div>
        """, unsafe_allow_html=True)
    
    with cols[1]:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{sections_with_body}</div>
            <div class="stat-label">With Content</div>
        </div>
        """, unsafe_allow_html=True)
    
    with cols[2]:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{sections_with_title}</div>
            <div class="stat-label">With Titles</div>
        </div>
        """, unsafe_allow_html=True)
    
    with cols[3]:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{translated}</div>
            <div class="stat-label">Translated</div>
        </div>
        """, unsafe_allow_html=True)


def render_section_card(section):
    section_num = section.get('section', '')
    title = section.get('section_title', '')
    body = section.get('section_body_text', '')
    parent = section.get('parent_section', '')
    pages = f"Page {section.get('section_start_page', '')}"
    if section.get('section_start_page') != section.get('section_end_page'):
        pages += f" - {section.get('section_end_page', '')}"
    
    with st.container():
        col1, col2 = st.columns([0.85, 0.15])
        with col1:
            st.markdown(f'<span class="section-number">§ {section_num}</span>', unsafe_allow_html=True)
            if title:
                st.markdown(f'<div class="section-title-text">{title}</div>', unsafe_allow_html=True)
        with col2:
            st.caption(pages)
        
        if body:
            with st.expander("View content", expanded=False):
                st.markdown(f'<div class="section-body">{body[:1000]}{"..." if len(body) > 1000 else ""}</div>', unsafe_allow_html=True)
        
        if parent:
            st.caption(f"Parent: § {parent}")
        
        st.divider()


def render_translation_card(translation):
    section_id = translation.get('id', '')
    description = translation.get('description', '')
    condition = translation.get('condition_english', '')
    requirement = translation.get('requirement_english', '')
    exception = translation.get('exception')
    
    with st.container():
        st.markdown(f'<span class="section-number">§ {section_id}</span>', unsafe_allow_html=True)
        
        if description:
            st.markdown(f"""
            <div class="translation-field">
                <div class="translation-label">Summary</div>
                <div class="translation-value">{description}</div>
            </div>
            """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if condition:
                st.markdown(f"""
                <div class="translation-field">
                    <div class="translation-label">📋 When it Applies</div>
                    <div class="translation-value">{condition}</div>
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            if requirement:
                st.markdown(f"""
                <div class="translation-field">
                    <div class="translation-label">✅ Requirements</div>
                    <div class="translation-value">{requirement}</div>
                </div>
                """, unsafe_allow_html=True)
        
        if exception and isinstance(exception, dict):
            exc_condition = exception.get('condition_english', '')
            exc_requirement = exception.get('requirement_english', '')
            if exc_condition or exc_requirement:
                st.markdown(f"""
                <div class="exception-box">
                    <div class="translation-label">⚠️ Exception</div>
                    <div class="translation-value">
                        <strong>When:</strong> {exc_condition}<br>
                        <strong>Then:</strong> {exc_requirement}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        st.divider()


def process_step2_with_progress(sections, api_key, progress_container, status_container):
    """Process Step 2 with real-time progress updates."""
    sections_with_text = [s for s in sections if s.get('section_body_text')]
    total = len(sections_with_text)
    
    if total == 0:
        return {"translated_sections": []}
    
    translator = SemanticTranslator(api_key=api_key)
    translated_sections = []
    
    progress_bar = progress_container.progress(0)
    
    for i, section in enumerate(sections_with_text):
        section_id = section.get('section', '?')
        
        status_container.markdown(f"""
        <div class="progress-item processing">
            <span>🔄</span>
            <span>Translating section <strong>{section_id}</strong> ({i + 1}/{total})</span>
        </div>
        """, unsafe_allow_html=True)
        
        try:
            translated = translator._translate_section(section)
            from dataclasses import asdict
            translated_sections.append(asdict(translated))
        except Exception as e:
            translated_sections.append({
                "id": section_id,
                "description": f"Error translating section: {str(e)}",
                "condition_english": None,
                "requirement_english": None,
                "exception": None
            })
        
        progress_bar.progress((i + 1) / total)
        time.sleep(0.3)
    
    status_container.markdown(f"""
    <div class="progress-item completed">
        <span>✅</span>
        <span>Translation complete! <strong>{total}</strong> sections processed</span>
    </div>
    """, unsafe_allow_html=True)
    
    return {"translated_sections": translated_sections}


def main():
    render_header()
    
    if 'step1_data' not in st.session_state:
        st.session_state.step1_data = None
    if 'step2_data' not in st.session_state:
        st.session_state.step2_data = None
    if 'uploaded_filename' not in st.session_state:
        st.session_state.uploaded_filename = None
    
    api_key = os.getenv('OPENAI_API_KEY', '')
    
    with st.sidebar:
        st.markdown("### 📤 Upload Document")
        
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=['pdf'],
            help="Upload a zoning bylaw or similar structured document"
        )
        
        if uploaded_file:
            st.success(f"📎 {uploaded_file.name}")
            
            if st.button("🚀 Extract Sections", type="primary", use_container_width=True):
                with st.spinner("Extracting sections..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_path = tmp_file.name
                    
                    try:
                        extractor = ZoningPDFExtractor(tmp_path)
                        st.session_state.step1_data = extractor.extract()
                        st.session_state.uploaded_filename = uploaded_file.name
                        st.session_state.step2_data = None
                        st.success("✅ Extraction complete!")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                    finally:
                        os.unlink(tmp_path)
        
        st.divider()
        
        if st.session_state.step1_data:
            st.markdown("### 📥 Downloads")
            
            step1_json = json.dumps(st.session_state.step1_data, indent=2)
            st.download_button(
                label="📄 Download Step 1 JSON",
                data=step1_json,
                file_name="step1_extracted_sections.json",
                mime="application/json",
                use_container_width=True
            )
            
            if st.session_state.step2_data:
                step2_json = json.dumps(st.session_state.step2_data, indent=2)
                st.download_button(
                    label="📄 Download Step 2 JSON",
                    data=step2_json,
                    file_name="step2_translated_sections.json",
                    mime="application/json",
                    use_container_width=True
                )
    
    if st.session_state.step1_data:
        render_stats(st.session_state.step1_data, st.session_state.step2_data)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["📋 Step 1: Extracted Sections", "🔄 Step 2: Translated Sections"])
        
        with tab1:
            st.markdown("""
            <div class="step-card">
                <div class="step-header">
                    <div class="step-number">1</div>
                    <h3 class="step-title">Extracted Sections</h3>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            sections = st.session_state.step1_data.get('sections', [])
            
            search_term = st.text_input("🔍 Search sections", placeholder="Filter by section number or title...")
            
            filtered_sections = sections
            if search_term:
                search_lower = search_term.lower()
                filtered_sections = [
                    s for s in sections
                    if search_lower in s.get('section', '').lower()
                    or search_lower in (s.get('section_title') or '').lower()
                    or search_lower in (s.get('section_body_text') or '').lower()
                ]
            
            st.caption(f"Showing {len(filtered_sections)} of {len(sections)} sections")
            
            for section in filtered_sections:
                render_section_card(section)
        
        with tab2:
            st.markdown("""
            <div class="step-card">
                <div class="step-header">
                    <div class="step-number">2</div>
                    <h3 class="step-title">Semantic Translation</h3>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if not st.session_state.step2_data:
                sections_to_translate = len([s for s in st.session_state.step1_data.get('sections', []) if s.get('section_body_text')])
                
                st.info(f"📊 **{sections_to_translate}** sections ready for translation")
                
                if not api_key:
                    st.warning("⚠️ Please set the OPENAI_API_KEY environment variable to enable translation")
                else:
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        if st.button("🔄 Start Translation", type="primary", use_container_width=True):
                            progress_container = st.empty()
                            status_container = st.empty()
                            
                            st.session_state.step2_data = process_step2_with_progress(
                                st.session_state.step1_data.get('sections', []),
                                api_key,
                                progress_container,
                                status_container
                            )
                            st.rerun()
            else:
                translations = st.session_state.step2_data.get('translated_sections', [])
                
                search_term2 = st.text_input("🔍 Search translations", placeholder="Filter by section ID or content...", key="search2")
                
                filtered_translations = translations
                if search_term2:
                    search_lower = search_term2.lower()
                    filtered_translations = [
                        t for t in translations
                        if search_lower in t.get('id', '').lower()
                        or search_lower in (t.get('description') or '').lower()
                        or search_lower in (t.get('condition_english') or '').lower()
                        or search_lower in (t.get('requirement_english') or '').lower()
                    ]
                
                st.caption(f"Showing {len(filtered_translations)} of {len(translations)} translations")
                
                for translation in filtered_translations:
                    render_translation_card(translation)
    
    else:
        st.markdown("""
        <div style="text-align: center; padding: 4rem 2rem;">
            <div style="font-size: 4rem; margin-bottom: 1rem;">📄</div>
            <h2 style="color: #334155; margin-bottom: 0.5rem;">Upload a PDF to get started</h2>
            <p style="color: #64748b;">Use the sidebar to upload a zoning bylaw or similar structured document</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("ℹ️ How it works"):
            st.markdown("""
            **Step 1: Extraction**
            - Upload your PDF document
            - The system extracts all numbered sections
            - Identifies titles, body text, and page locations
            - Builds parent-child relationships between sections
            
            **Step 2: Translation**
            - Uses AI to translate legal text to plain English
            - Identifies conditions, requirements, and exceptions
            - Generates readable summaries for each section
            """)


if __name__ == "__main__":
    main()

