import os
import re
import json
from typing import List, Dict, Any, Optional, Tuple
from langchain.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from serpapi import GoogleSearch
import time
from config import get_settings
from utils.cache import cached, redis_cache
from utils.logger import get_logger, log_performance

settings = get_settings()
logger = get_logger(__name__)

class FactChecker:
    """Enhanced agent for fact-checking with confidence scoring."""
    
    def __init__(self, model_type: str = None):
        """Initialize the fact-checker."""
        self.model_type = model_type or settings.default_model
        self.llm = self._initialize_llm()
        self.serpapi_key = settings.serpapi_api_key
        self.confidence_threshold = 0.7
        logger.info(f"Initialized FactChecker with {self.model_type}")
    
    def _initialize_llm(self):
        """Initialize the LLM."""
        try:
            if self.model_type == "groq":
                return ChatGroq(
                    model="llama3-70b-8192",
                    temperature=0.1,
                    max_tokens=1000,
                    api_key=settings.groq_api_key
                )
            elif self.model_type == "google":
                return ChatGoogleGenerativeAI(
                    model="gemini-pro",
                    temperature=0.1,
                    max_tokens=1000,
                    google_api_key=settings.google_api_key
                )
            elif self.model_type == "openai":
                return ChatOpenAI(
                    model="gpt-4-turbo-preview",
                    temperature=0.1,
                    max_tokens=1000,
                    api_key=settings.openai_api_key
                )
            else:
                raise ValueError(f"Unsupported model type: {self.model_type}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            raise
    
    def extract_claims(self, text: str) -> List[str]:
        """Extract factual claims with improved pattern matching."""
        claims = []
        
        # Enhanced patterns for factual claims
        patterns = [
            # Statistics and percentages
            r'(\d+%?)\s+(?:of|increase|decrease|growth|decline|rise|fall|improve|reduce)\s+',
            r'(?:over|more than|less than|about|approximately)\s+\d+\s+(?:percent|%|million|billion|years?|people|users|companies)',
            
            # Time-based claims
            r'(?:in|from|between)\s+\d{4}\s+(?:to|and)\s+\d{4}',
            r'(?:since|as of|by)\s+\d{4}',
            r'(?:last|past|next)\s+\d+\s+(?:years?|months?|weeks?|days?)',
            
            # Comparative claims
            r'(?:the\s+)?(?:average|median|mean|typical|standard)\s+\w+\s+(?:is|are|was|were)\s+\d+',
            r'(?:better|worse|higher|lower|more|less)\s+than\s+\d+',
            
            # Rankings and positions
            r'(?:ranked?|positioned?|listed?)\s+#?\d+',
            r'(?:top|leading|biggest|largest|smallest)\s+\d+',
            
            # Dollar amounts
            r'\$\d+(?:\.\d+)?\s*(?:million|billion|trillion)?',
            r'(?:revenue|profit|sales|spending|budget|cost)\s+(?:of|at|around)\s+\$?\d+',
            
            # Quantifiable claims
            r'(?:increase|decrease|growth|decline|rise|fall)\s+(?:by\s+)?\d+%?',
            r'(?:more|less)\s+than\s+\d+\s+(?:percent|%|times?|x)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = ' '.join(match)
                if len(str(match)) > 3:
                    claims.append(str(match).strip())
        
        # Use LLM for additional claims
        if len(claims) < 3:
            prompt = ChatPromptTemplate.from_template("""
            Extract factual claims from the following text. Focus on verifiable statements 
            that contain specific numbers, dates, statistics, or quantifiable information.
            Return only the claims, one per line.
            
            Text: {text}
            
            Claims:
            """)
            
            messages = prompt.format_messages(text=text)
            response = self.llm.invoke(messages)
            llm_claims = response.content.strip().split('\n')
            claims.extend([c.strip() for c in llm_claims if c.strip() and len(c.strip()) > 5])
        
        # Remove duplicates and clean
        claims = list(set(claims))
        claims = [c for c in claims if len(c) > 3]
        
        logger.info(f"Extracted {len(claims)} claims from text")
        return claims
    
    def _search_web(self, query: str, max_results: int = 3) -> List[str]:
        """Search the web with retry logic."""
        try:
            params = {
                "q": query,
                "api_key": self.serpapi_key,
                "num": max_results
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            
            snippets = []
            if "organic_results" in results:
                for result in results["organic_results"][:max_results]:
                    if "snippet" in result:
                        snippets.append(result["snippet"])
                    if "title" in result:
                        snippets.append(result["title"])
            
            logger.debug(f"Search for '{query}' returned {len(snippets)} results")
            return snippets
            
        except Exception as e:
            logger.error(f"Search error for '{query}': {e}")
            return []
    
    @cached(ttl=3600)
    def verify_claim(self, claim: str) -> Dict[str, Any]:
        """Verify a single claim with confidence scoring."""
        start_time = time.time()
        
        # Check cache
        cache_key = f"fact_check:{claim}"
        cached_result = redis_cache.get(cache_key)
        if cached_result:
            log_performance("verify_claim_cache_hit", time.time() - start_time, {'claim': claim[:50]})
            return cached_result
        
        # Search for evidence
        search_results = self._search_web(claim)
        
        if not search_results:
            return {
                "status": "unverified",
                "confidence": 0.0,
                "explanation": "No search results found to verify this claim.",
                "source": None,
                "evidence": []
            }
        
        # Use LLM to evaluate
        prompt = ChatPromptTemplate.from_template("""
        You are a fact-checker. Verify this claim based on the search results.
        
        Claim: {claim}
        
        Search Results:
        {search_results}
        
        Analyze the claim and provide:
        1. Status: "verified", "unverified", or "inaccurate"
        2. Confidence score (0.0-1.0)
        3. Brief explanation
        4. Source quote from search results
        
        Format your response as JSON:
        {{
            "status": "verified|unverified|inaccurate",
            "confidence": 0.0-1.0,
            "explanation": "brief explanation",
            "source": "exact quote from source",
            "evidence": ["piece of evidence 1", "piece of evidence 2"]
        }}
        """)
        
        messages = prompt.format_messages(
            claim=claim,
            search_results="\n".join(search_results[:5])
        )
        
        try:
            response = self.llm.invoke(messages)
            result = json.loads(response.content)
            
            # Validate confidence
            if result.get('confidence', 0) < self.confidence_threshold:
                result['status'] = 'unverified'
            
            # Cache the result
            redis_cache.set(cache_key, result)
            
            duration = time.time() - start_time
            log_performance("verify_claim", duration, {'claim': claim[:50], 'status': result.get('status')})
            
            return result
            
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse LLM response for claim: {claim}")
            return {
                "status": "unverified",
                "confidence": 0.3,
                "explanation": "Could not verify this claim.",
                "source": None,
                "evidence": []
            }
        except Exception as e:
            logger.error(f"Verification error: {e}")
            return {
                "status": "unverified",
                "confidence": 0.1,
                "explanation": f"Error during verification: {str(e)}",
                "source": None,
                "evidence": []
            }
    
    def check_post(self, post_content: str, max_claims: int = 5) -> Dict[str, Any]:
        """Fact-check an entire post with scoring."""
        start_time = time.time()
        
        # Extract claims
        claims = self.extract_claims(post_content)
        
        if not claims:
            return {
                "status": "no_claims",
                "claims_checked": {},
                "summary": "No factual claims found to verify.",
                "overall_confidence": 1.0
            }
        
        # Limit claims
        claims = claims[:max_claims]
        
        # Verify each claim
        claims_checked = {}
        verified_count = 0
        inaccurate_count = 0
        unverified_count = 0
        total_confidence = 0.0
        
        for claim in claims:
            result = self.verify_claim(claim)
            claims_checked[claim] = result
            
            if result.get("status") == "verified":
                verified_count += 1
            elif result.get("status") == "inaccurate":
                inaccurate_count += 1
            else:
                unverified_count += 1
            
            total_confidence += result.get("confidence", 0.0)
        
        # Calculate statistics
        avg_confidence = total_confidence / len(claims) if claims else 0.0
        
        # Determine overall status
        if inaccurate_count > 0:
            status = "inaccurate"
            summary = f"Found {inaccurate_count} inaccurate claim(s). Please review these claims before publishing."
        elif verified_count == len(claims):
            status = "verified"
            summary = f"All {verified_count} claims verified successfully with {avg_confidence:.1%} average confidence."
        elif verified_count > 0:
            status = "partially_verified"
            summary = f"Verified {verified_count} of {len(claims)} claims. {unverified_count} claim(s) could not be verified."
        else:
            status = "unverified"
            summary = f"Could not verify any of the {len(claims)} claims found."
        
        duration = time.time() - start_time
        log_performance("check_post", duration, {'claims': len(claims), 'status': status})
        
        return {
            "status": status,
            "claims_checked": claims_checked,
            "summary": summary,
            "statistics": {
                "total_claims": len(claims),
                "verified": verified_count,
                "unverified": unverified_count,
                "inaccurate": inaccurate_count,
                "average_confidence": avg_confidence
            },
            "overall_confidence": avg_confidence
        }