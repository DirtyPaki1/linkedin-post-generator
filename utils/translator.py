from googletrans import Translator, LANGUAGES
from typing import List, Dict, Any, Optional
import re
from textblob import TextBlob
from utils.logger import get_logger
from utils.cache import cached

logger = get_logger(__name__)

class LanguageTranslator:
    """Enhanced multi-language support with detection and adaptation."""
    
    SUPPORTED_LANGUAGES = {
        'en': 'English',
        'es': 'Spanish',
        'fr': 'French',
        'de': 'German',
        'it': 'Italian',
        'pt': 'Portuguese',
        'ja': 'Japanese',
        'ko': 'Korean',
        'zh-cn': 'Chinese (Simplified)',
        'zh-tw': 'Chinese (Traditional)',
        'hi': 'Hindi',
        'ar': 'Arabic',
        'ru': 'Russian',
        'nl': 'Dutch',
        'pl': 'Polish',
        'tr': 'Turkish',
        'vi': 'Vietnamese',
        'th': 'Thai',
        'id': 'Indonesian'
    }
    
    def __init__(self):
        self.translator = Translator()
        logger.info("Translator initialized")
    
    @cached(ttl=3600)
    def detect_language(self, text: str) -> Dict[str, Any]:
        """Detect language with confidence score."""
        try:
            result = self.translator.detect(text)
            return {
                'language': result.lang,
                'confidence': result.confidence,
                'name': LANGUAGES.get(result.lang, 'Unknown')
            }
        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return {'language': 'en', 'confidence': 0.0, 'name': 'English'}
    
    @cached(ttl=3600)
    def translate_text(self, text: str, target_lang: str, source_lang: Optional[str] = None) -> Dict[str, Any]:
        """Translate text with metadata."""
        try:
            if target_lang not in self.SUPPORTED_LANGUAGES:
                raise ValueError(f"Unsupported language: {target_lang}")
            
            # Detect source if not provided
            if not source_lang:
                detected = self.detect_language(text)
                source_lang = detected['language']
            
            # Translate
            result = self.translator.translate(text, dest=target_lang, src=source_lang)
            
            return {
                'text': result.text,
                'source_language': source_lang,
                'target_language': target_lang,
                'confidence': result.extra_data.get('confidence', 1.0)
            }
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return {'text': text, 'error': str(e)}
    
    def translate_post(self, post: Dict[str, Any], target_lang: str) -> Dict[str, Any]:
        """Translate an entire post."""
        if target_lang not in self.SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {target_lang}")
        
        translated_post = post.copy()
        
        try:
            # Detect original language
            detected = self.detect_language(post['content'])
            translated_post['original_language'] = detected
            
            # Translate content
            translated = self.translate_text(
                post['content'],
                target_lang,
                detected['language']
            )
            translated_post['content'] = translated['text']
            
            # Translate hashtags (keep # prefix)
            if 'hashtags' in post:
                translated_hashtags = []
                for tag in post['hashtags']:
                    clean_tag = tag.strip('#')
                    translated_tag = self.translate_text(clean_tag, target_lang)
                    translated_hashtags.append(f"#{translated_tag['text']}")
                translated_post['hashtags'] = translated_hashtags
            
            translated_post['language'] = target_lang
            translated_post['translation_confidence'] = translated.get('confidence', 1.0)
            
            logger.info(f"Translated post to {target_lang}")
            return translated_post
            
        except Exception as e:
            logger.error(f"Post translation failed: {e}")
            translated_post['translation_error'] = str(e)
            return translated_post
    
    def get_language_options(self) -> List[str]:
        """Get list of supported language codes."""
        return list(self.SUPPORTED_LANGUAGES.keys())
    
    def get_language_name(self, code: str) -> str:
        """Get language name from code."""
        return self.SUPPORTED_LANGUAGES.get(code, 'Unknown')
    
    def adapt_for_culture(self, text: str, target_lang: str) -> str:
        """Adapt content for cultural context."""
        # This would include culture-specific modifications
        # For now, just translate
        result = self.translate_text(text, target_lang)
        return result['text']