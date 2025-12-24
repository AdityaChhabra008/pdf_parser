"""
Step 1: PDF Section Extractor for Zoning Bylaws

This module extracts structured sections from zoning bylaw PDFs into a JSON format.
It identifies section numbers, parent-child relationships, titles, body text, and page locations.

"""

import re
import json
import argparse
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict
import pdfplumber


@dataclass
class Section:
    """Represents a single section extracted from the PDF."""
    parent_section: str
    section: str
    section_title: Optional[str]
    section_body_text: Optional[str]
    section_start_page: int
    section_end_page: int


class ZoningPDFExtractor:
    """
    Extracts structured sections from zoning bylaw PDF documents.
    
    The extractor identifies sections by their numbering patterns (e.g., 1, 1.1, 2.2.1)
    and preserves hierarchical relationships between parent and child sections.
    
    Uses heuristic-based detection to distinguish between section titles and body text,
    making it adaptable to various zoning bylaw document formats.
    """
    
    FOOTER_PATTERNS = [
        r'^Page\s*\d+',
        r'^\d{4}$',
        r'^[A-Z][a-z]+\s+\d{4}$',
        r'^[-_]{3,}$',
    ]
    
    def __init__(self, pdf_path: str, district_code: str = None):
        """
        Initialize the extractor with a PDF file path.
        
        Args:
            pdf_path: Path to the zoning bylaw PDF file
            district_code: Optional district code to filter from headers (e.g., "R1-1")
        """
        self.pdf_path = pdf_path
        self.district_code = district_code
        self.pages_text: List[Dict] = []
        self.sections: List[Section] = []
        self._detected_headers: set = set()
        
    def _detect_repeating_headers(self, pages_text: List[str]) -> set:
        """
        Detect text that appears on multiple pages (likely headers/footers).
        
        Args:
            pages_text: List of text content from each page
            
        Returns:
            Set of text patterns that appear to be headers/footers
        """
        line_counts = {}
        
        for page_text in pages_text:
            lines = page_text.split('\n')
            check_lines = lines[:5] + lines[-5:] if len(lines) > 10 else lines
            
            for line in check_lines:
                stripped = line.strip()
                if stripped and len(stripped) < 100:
                    line_counts[stripped] = line_counts.get(stripped, 0) + 1
        
        repeating = set()
        threshold = max(2, len(pages_text) // 3)
        
        for line, count in line_counts.items():
            if count >= threshold:
                repeating.add(line)
        
        return repeating
        
    def _clean_text(self, text: str) -> str:
        """
        Remove headers, footers, and clean up text formatting.
        
        Args:
            text: Raw text from PDF page
            
        Returns:
            Cleaned text with headers/footers removed
        """
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            skip_line = False
            stripped = line.strip()
            
            if stripped in self._detected_headers:
                skip_line = True
            
            if self.district_code and stripped == self.district_code:
                skip_line = True
            
            for pattern in self.FOOTER_PATTERNS:
                if re.match(pattern, stripped, re.IGNORECASE):
                    skip_line = True
                    break
            
            if stripped.startswith('---') or stripped == '____':
                skip_line = True
                
            if not skip_line:
                cleaned_lines.append(line)
        
        text = '\n'.join(cleaned_lines)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    
    def _extract_text_from_pdf(self) -> None:
        """Extract and clean text from all pages of the PDF."""
        raw_pages = []
        
        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                raw_text = page.extract_text() or ""
                raw_pages.append(raw_text)
        
        self._detected_headers = self._detect_repeating_headers(raw_pages)
        
        for page_num, raw_text in enumerate(raw_pages, start=1):
            cleaned_text = self._clean_text(raw_text)
            self.pages_text.append({
                'page_number': page_num,
                'text': cleaned_text
            })
    
    def _get_parent_section(self, section_number: str) -> str:
        """
        Determine the parent section for a given section number.
        
        Args:
            section_number: The section number (e.g., "2.2.1")
            
        Returns:
            Parent section number (e.g., "2.2") or empty string for top-level sections
        """
        parts = section_number.split('.')
        if len(parts) <= 1:
            return ""
        return '.'.join(parts[:-1])
    
    def _is_valid_title(self, text: str, section_num: str) -> bool:
        """
        Determine if text is a valid section title vs body text using heuristics.
        
        Titles are short descriptive labels. Body text contains regulatory content.
        This method uses multiple heuristics to make the distinction without
        relying on hardcoded title lists.
        
        Args:
            text: Text to evaluate
            section_num: The section number for context
            
        Returns:
            True if the text is a valid title, False if it's body text
        """
        if not text:
            return False
        
        text = text.strip()
        
        if len(text) > 60:
            return False
        
        words = text.split()
        word_count = len(words)
        
        if word_count > 6:
            return False
        
        if text.endswith(':') or text.endswith('.') or text.endswith(',') or text.endswith(';'):
            return False
        
        if '(' in text or ')' in text:
            return False
        
        if re.search(r'\d+\s*m[²2]|\d+\s*%|\d+\.\d+\s*m\b', text):
            return False
        
        if re.search(r'section\s+\d', text, re.IGNORECASE):
            return False
        
        body_starters = [
            r'^a\s+\w+\s+\w+',
            r'^the\s+\w+\s+(is|are|must|may|will|shall|can|should|of)\b',
            r'^for\s+(the|a|an|all|any|each|multiple|every)\b',
            r'^if\s+',
            r'^where\s+',
            r'^when\s+',
            r'^unless\s+',
            r'^except\s+',
            r'^despite\s+',
            r'^no\s+\w+\s+(may|can|shall|must|is|are)\b',
            r'^all\s+\w+\s+(are|must|shall|may|is)\b',
            r'^any\s+\w+\s+(that|which|is|are|must|may)\b',
            r'^on\s+a\s+site\b',
            r'^\w+\s+buildings?\s+(customarily|that|which|are|is|must|may)\b',
            r'^\w+\s+dwelling\b',
            r'^\w+\s+house\b',
            r'^\w+\s+units?\b',
            r'^minimum\s+',
            r'^maximum\s+',
            r'^(is|are|must|may|shall|will|can)\s+',
        ]
        
        for pattern in body_starters:
            if re.match(pattern, text, re.IGNORECASE):
                return False
        
        if re.search(r'\b(permitted|required|allowed|prohibited|must|shall|may not)\b', text, re.IGNORECASE):
            if word_count > 3:
                return False
        
        if text.isupper():
            if word_count <= 5 and not re.search(r'\d', text):
                return True
        
        title_case_count = sum(1 for w in words if w and w[0].isupper())
        connectors = {'and', 'or', 'of', 'the', 'in', 'for', 'to', 'with', 'a', 'an', 'by', 'on'}
        non_connector_words = [w for w in words if w.lower() not in connectors]
        
        if title_case_count >= len(non_connector_words) and word_count <= 5:
            if all(w[0].isupper() or w.lower() in connectors for w in words if w):
                return True
        
        if word_count <= 3:
            if all(w[0].isupper() for w in words if w and w[0].isalpha()):
                if not any(w.lower() in ['is', 'are', 'was', 'were', 'be', 'been', 'being', 
                                         'has', 'have', 'had', 'do', 'does', 'did',
                                         'will', 'shall', 'may', 'can', 'must', 'should'] 
                          for w in words):
                    return True
        
        return False
    
    def _get_page_for_position(self, position: int, page_boundaries: List[Dict]) -> int:
        """Get the page number for a given text position."""
        for boundary in page_boundaries:
            if boundary['start'] <= position < boundary['end']:
                return boundary['page']
        return page_boundaries[-1]['page'] if page_boundaries else 1
    
    def _is_valid_section_number(self, section_num: str) -> bool:
        """
        Validate if a string is a legitimate section number.
        
        Args:
            section_num: The potential section number string
            
        Returns:
            True if it's a valid section number format
        """
        if len(section_num.replace('.', '')) > 8:
            return False
        
        parts = section_num.split('.')
        
        if len(parts) > 5:
            return False
        
        try:
            for p in parts:
                num = int(p)
                if num > 99 or num < 1:
                    return False
        except ValueError:
            return False
        
        return True
    
    def _parse_sections(self) -> None:
        """
        Parse the extracted text to identify and structure sections.
        
        This method processes all page text to identify section boundaries,
        extract section numbers, titles, and body text, and track page locations.
        """
        full_text = ""
        page_boundaries = []
        current_pos = 0
        
        for page_data in self.pages_text:
            page_boundaries.append({
                'page': page_data['page_number'],
                'start': current_pos,
                'end': current_pos + len(page_data['text'])
            })
            full_text += page_data['text'] + "\n\n"
            current_pos = len(full_text)
        
        section_pattern = re.compile(
            r'^(\d+(?:\.\d+)*)\s+(.*)$',
            re.MULTILINE
        )
        
        raw_matches = []
        for match in section_pattern.finditer(full_text):
            section_num = match.group(1)
            following_text = match.group(2).strip()
            
            if not self._is_valid_section_number(section_num):
                continue
            
            raw_matches.append({
                'section': section_num,
                'following_text': following_text,
                'position': match.start(),
                'match_end': match.end(),
                'full_match': match.group(0)
            })
        
        raw_matches.sort(key=lambda x: x['position'])
        
        seen_sections = {}
        unique_matches = []
        for match in raw_matches:
            sec = match['section']
            if sec not in seen_sections:
                seen_sections[sec] = match
                unique_matches.append(match)
        
        processed_sections = []
        
        for i, match in enumerate(unique_matches):
            section_num = match['section']
            following_text = match['following_text']
            start_pos = match['position']
            
            if i + 1 < len(unique_matches):
                end_pos = unique_matches[i + 1]['position']
            else:
                end_pos = len(full_text)
            
            remaining_text = full_text[match['match_end']:end_pos].strip()
            
            is_title = self._is_valid_title(following_text, section_num)
            
            if is_title:
                title = following_text
                body_text = remaining_text if remaining_text else None
            else:
                title = None
                if following_text:
                    body_text = following_text + ('\n' + remaining_text if remaining_text else '')
                else:
                    body_text = remaining_text if remaining_text else None
            
            if body_text:
                body_text = re.sub(r'\n{3,}', '\n\n', body_text).strip()
                if len(body_text) < 3:
                    body_text = None
            
            start_page = self._get_page_for_position(start_pos, page_boundaries)
            end_page = self._get_page_for_position(end_pos - 1, page_boundaries)
            
            processed_sections.append({
                'section': section_num,
                'title': title,
                'body_text': body_text,
                'start_page': start_page,
                'end_page': end_page
            })
        
        for sec_data in processed_sections:
            section = Section(
                parent_section=self._get_parent_section(sec_data['section']),
                section=sec_data['section'],
                section_title=sec_data['title'],
                section_body_text=sec_data['body_text'],
                section_start_page=sec_data['start_page'],
                section_end_page=sec_data['end_page']
            )
            self.sections.append(section)
    
    def extract(self) -> dict:
        """
        Execute the full extraction pipeline.
        
        Returns:
            Dictionary containing all extracted sections
        """
        self._extract_text_from_pdf()
        self._parse_sections()
        
        self.sections.sort(key=lambda x: [int(n) for n in x.section.split('.')])
        
        return {
            "sections": [asdict(section) for section in self.sections]
        }
    
    def save_to_json(self, output_path: str) -> None:
        """
        Extract sections and save to a JSON file.
        
        Args:
            output_path: Path where the JSON file will be saved
        """
        result = self.extract()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"Extraction complete. {len(result['sections'])} sections saved to {output_path}")


def main():
    """Entry point for command-line execution."""
    parser = argparse.ArgumentParser(
        description='Extract sections from zoning bylaw PDFs into structured JSON'
    )
    parser.add_argument(
        '--input',
        type=str,
        required=True,
        help='Path to the input PDF file'
    )
    parser.add_argument(
        '--output',
        type=str,
        required=True,
        help='Path for the output JSON file'
    )
    parser.add_argument(
        '--district-code',
        type=str,
        default=None,
        help='District code to filter from headers (e.g., R1-1, RT-7)'
    )
    
    args = parser.parse_args()
    
    extractor = ZoningPDFExtractor(args.input, district_code=args.district_code)
    extractor.save_to_json(args.output)


if __name__ == '__main__':
    main()
