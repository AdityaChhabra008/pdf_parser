"""
Step 2: Semantic Translator for Documents Sections

This module translates extracted document sections into plain English components
using OpenAI's GPT model. It processes the JSON output from Step 1 and produces
structured semantic translations.

"""

import os
import re
import json
import time
import argparse
from dataclasses import dataclass, asdict
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ExceptionClause:
    """Represents an exception within a zoning section."""
    condition_english: str
    requirement_english: str


@dataclass
class TranslatedSection:
    """Represents a semantically translated zoning section."""
    id: str
    description: str
    condition_english: Optional[str]
    requirement_english: Optional[str]
    exception: Optional[dict]


class SemanticTranslator:
    """
    Translates zoning bylaw sections into plain English semantic components.
    
    Uses OpenAI's GPT model to parse legal/regulatory text and extract:
    - Conditions: When does this rule apply?
    - Requirements: What must be done to comply?
    - Exceptions: Under what circumstances can requirements be waived?
    - Description: Plain English summary of the section
    """
    
    MODEL_NAME = "gpt-5.2-2025-12-11"
    MAX_RETRIES = 3
    RETRY_DELAY = 2
    
    TRANSLATION_PROMPT = """You are a legal document translator specializing in zoning bylaws.
Your task is to translate a zoning bylaw section into plain English components.

IMPORTANT: You must respond with ONLY a valid JSON object. No markdown, no code blocks, no explanations.

For the given section, extract the following components:

1. "description": A plain English summary of the entire section. Should be readable by a regular person, not legal jargon. 2-4 sentences.

2. "condition_english": When does this rule apply? What triggers this section? If this is just a header/title section with no specific conditions, set to null.

3. "requirement_english": What must someone actually do to comply? What are the specific requirements? If there are no specific requirements (e.g., it's just a title), set to null.

4. "exception": An object with two fields IF there is an exception clause:
   - "condition_english": Under what circumstances can the requirement be changed?
   - "requirement_english": What happens if the exception applies?
   If there is no exception, set to null.

RESPOND WITH ONLY THE JSON OBJECT. Example format:
{{"description": "...", "condition_english": "...", "requirement_english": "...", "exception": {{"condition_english": "...", "requirement_english": "..."}}}}

Or if no exception:
{{"description": "...", "condition_english": "...", "requirement_english": "...", "exception": null}}

Section ID: {section_id}
Section Title: {section_title}
Section Text:
{section_text}

JSON Response:"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the translator with OpenAI API credentials.
        
        Args:
            api_key: OpenAI API key. If not provided, reads from OPENAI_API_KEY env var.
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError(
                "OpenAI API key is required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )
        self.client = OpenAI(api_key=self.api_key)
        self.translated_sections = []
    
    def _clean_json_response(self, response_text: str) -> str:
        """
        Clean the API response to extract valid JSON.
        
        Args:
            response_text: Raw response from the API
            
        Returns:
            Cleaned JSON string
        """
        text = response_text.strip()
        
        if text.startswith('```json'):
            text = text[7:]
        elif text.startswith('```'):
            text = text[3:]
        
        if text.endswith('```'):
            text = text[:-3]
        
        text = text.strip()
        
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            text = json_match.group(0)
        
        return text
    
    def _call_openai(self, prompt: str) -> dict:
        """
        Make an API call to OpenAI with retry logic.
        
        Args:
            prompt: The formatted prompt to send
            
        Returns:
            Parsed JSON response as dictionary
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.client.chat.completions.create(
                    model=self.MODEL_NAME,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a precise JSON generator. Always respond with valid JSON only, no markdown formatting or explanations."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.1,
                    max_completion_tokens=2000
                )
                
                response_text = response.choices[0].message.content
                cleaned_json = self._clean_json_response(response_text)
                
                return json.loads(cleaned_json)
                
            except json.JSONDecodeError as e:
                print(f"JSON parsing error on attempt {attempt + 1}: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                else:
                    return self._create_fallback_response()
                    
            except Exception as e:
                print(f"API error on attempt {attempt + 1}: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
                else:
                    raise
        
        return self._create_fallback_response()
    
    def _create_fallback_response(self) -> dict:
        """
        Create a fallback response when API calls fail.
        
        Returns:
            Default response structure
        """
        return {
            "description": "Unable to parse section content.",
            "condition_english": None,
            "requirement_english": None,
            "exception": None
        }
    
    def _translate_section(self, section: dict) -> TranslatedSection:
        """
        Translate a single section into semantic components.
        
        Args:
            section: Dictionary containing section data from Step 1
            
        Returns:
            TranslatedSection with semantic components
        """
        section_id = section.get('section', '')
        section_title = section.get('section_title') or 'No title'
        section_text = section.get('section_body_text') or ''
        
        if not section_text:
            return TranslatedSection(
                id=section_id,
                description=f"Section header: {section_title}" if section_title != 'No title' else "Empty section",
                condition_english=None,
                requirement_english=None,
                exception=None
            )
        
        prompt = self.TRANSLATION_PROMPT.format(
            section_id=section_id,
            section_title=section_title,
            section_text=section_text[:8000]
        )
        
        result = self._call_openai(prompt)
        
        exception = result.get('exception')
        if exception and isinstance(exception, dict):
            if not exception.get('condition_english') and not exception.get('requirement_english'):
                exception = None
        
        return TranslatedSection(
            id=section_id,
            description=result.get('description', ''),
            condition_english=result.get('condition_english'),
            requirement_english=result.get('requirement_english'),
            exception=exception
        )
    
    def translate_all(self, sections: list, verbose: bool = True) -> list:
        """
        Translate all sections with body text.
        
        Args:
            sections: List of section dictionaries from Step 1
            verbose: Whether to print progress information
            
        Returns:
            List of TranslatedSection objects
        """
        sections_with_text = [s for s in sections if s.get('section_body_text')]
        
        if verbose:
            print(f"Found {len(sections_with_text)} sections with body text to translate")
        
        for i, section in enumerate(sections_with_text, 1):
            if verbose:
                print(f"Translating section {section.get('section', '?')} ({i}/{len(sections_with_text)})")
            
            translated = self._translate_section(section)
            self.translated_sections.append(translated)
            
            time.sleep(0.5)
        
        return self.translated_sections
    
    def get_results(self) -> dict:
        """
        Get the translation results in the required output format.
        
        Returns:
            Dictionary with translated_sections array
        """
        return {
            "translated_sections": [asdict(section) for section in self.translated_sections]
        }


class TranslationPipeline:
    """
    End-to-end pipeline for translating Step 1 output to semantic components.
    """
    
    def __init__(self, input_path: str, output_path: str, api_key: Optional[str] = None):
        """
        Initialize the translation pipeline.
        
        Args:
            input_path: Path to Step 1 JSON output
            output_path: Path for the translated JSON output
            api_key: Optional OpenAI API key
        """
        self.input_path = input_path
        self.output_path = output_path
        self.api_key = api_key
        
    def _load_sections(self) -> list:
        """
        Load sections from the Step 1 JSON file.
        
        Returns:
            List of section dictionaries
        """
        with open(self.input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data.get('sections', [])
    
    def _save_results(self, results: dict) -> None:
        """
        Save translation results to JSON file.
        
        Args:
            results: Dictionary containing translated sections
        """
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    
    def run(self, verbose: bool = True) -> dict:
        """
        Execute the full translation pipeline.
        
        Args:
            verbose: Whether to print progress information
            
        Returns:
            Dictionary with translated sections
        """
        if verbose:
            print(f"Loading sections from {self.input_path}")
        
        sections = self._load_sections()
        
        if verbose:
            print(f"Loaded {len(sections)} total sections")
        
        translator = SemanticTranslator(api_key=self.api_key)
        translator.translate_all(sections, verbose=verbose)
        
        results = translator.get_results()
        
        self._save_results(results)
        
        if verbose:
            print(f"Translation complete. {len(results['translated_sections'])} sections saved to {self.output_path}")
        
        return results


def main():
    """Entry point for command-line execution."""
    parser = argparse.ArgumentParser(
        description='Translate zoning bylaw sections into plain English semantic components'
    )
    parser.add_argument(
        '--input',
        type=str,
        required=True,
        help='Path to the Step 1 JSON output file'
    )
    parser.add_argument(
        '--output',
        type=str,
        required=True,
        help='Path for the translated JSON output file'
    )
    parser.add_argument(
        '--api-key',
        type=str,
        default=None,
        help='OpenAI API key (or set OPENAI_API_KEY environment variable)'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress progress output'
    )
    
    args = parser.parse_args()
    
    pipeline = TranslationPipeline(
        input_path=args.input,
        output_path=args.output,
        api_key=args.api_key
    )
    
    pipeline.run(verbose=not args.quiet)


if __name__ == '__main__':
    main()

