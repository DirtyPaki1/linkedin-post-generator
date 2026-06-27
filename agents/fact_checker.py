import re
import json
from typing import List, Dict, Any
from groq import Groq
from serpapi import Client
from config import get_settings

settings = get_settings()

class FactChecker:
    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key)
        self.serpapi_key = settings.serpapi_api_key
        self.serp_client = Client(api_key=self.serpapi_key)
        self.model = "llama-3.3-70b-versatile"
    
    def extract_claims(self, text: str) -> List[str]:
        """Extract factual claims using improved patterns."""
        claims = []
        
        # Enhanced patterns for finding facts
        patterns = [
            r'(\d+%?)',
            r'\$\d+(?:\.\d+)?\s*(?:million|billion|trillion)?',
            r'\b(?:19|20)\d{2}\b',
            r'(?:increase|decrease|rise|fall|improve|reduce)\s+(?:by\s+)?\d+%?',
            r'(?:over|more than|less than|about|approximately)\s+\d+\s+(?:percent|%|million|billion|people|users|companies)',
            r'(?:\d+)\s+(?:out of|of)\s+\d+',
            r'(?:projected|estimated|predicted|expected)\s+(?:to\s+)?(?:reach|grow|increase)\s+\$?\d+',
            r'(?:ranked?|positioned?|listed?)\s+#?\d+',
            r'(?:since|as of|by)\s+\d{4}',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = ' '.join(match)
                if len(str(match)) > 2:
                    claims.append(str(match).strip())
        
        # Extract full sentences with claims
        sentences = re.split(r'[.!?]+', text)
        for sentence in sentences:
            if re.search(r'\d+%?|\$|\d{4}|stud(y|ies)|research|report|according|study|data', sentence, re.IGNORECASE):
                if len(sentence.strip()) > 20:
                    claims.append(sentence.strip())
        
        # Use LLM for additional claim extraction
        if len(claims) < 3:
            prompt = f"""Extract specific factual claims from this text. 
            Look for statistics, percentages, numbers, dates, or verifiable statements.
            Return ONLY the claims, one per line, without numbers or bullets.
            
            Text: {text}
            
            Claims:"""
            
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=300
                )
                llm_claims = response.choices[0].message.content.strip().split('\n')
                claims.extend([c.strip() for c in llm_claims if c.strip() and len(c.strip()) > 10])
            except:
                pass
        
        claims = list(set(claims))
        claims = [c for c in claims if len(c) > 3 and not c.isdigit()]
        
        return claims[:5]
    
    def _search_web(self, query: str) -> List[str]:
        """Search the web using SerpAPI Client."""
        try:
            result = self.serp_client.search(
                q=query,
                num=3
            )
            
            snippets = []
            if "organic_results" in result:
                for item in result["organic_results"][:3]:
                    if "snippet" in item:
                        snippets.append(item["snippet"])
                    if "title" in item:
                        snippets.append(item["title"])
            
            return snippets
            
        except Exception as e:
            print(f"Search error: {e}")
            return []
    
    def verify_claim(self, claim: str) -> Dict[str, Any]:
        """Verify a claim with more nuanced statuses."""
        try:
            snippets = self._search_web(claim)
            
            prompt = f"""Carefully verify this claim based on search results:

Claim: {claim}

Search Results:
{chr(10).join(snippets) if snippets else 'No results found.'}

Respond with ONLY valid JSON using these statuses:
- "verified": Claim is supported by multiple credible sources
- "partially_verified": Claim is partially true but may be outdated or exaggerated
- "unverified": No clear evidence found (claim may be true or false)
- "inaccurate": Claim is contradicted by multiple credible sources

Format:
{{"status": "verified|partially_verified|unverified|inaccurate", "confidence": 0.0-1.0, "explanation": "brief explanation of what sources say"}}
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=250
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Default to unverified if confidence is too low
            if result.get('confidence', 0) < 0.3:
                result['status'] = 'unverified'
            
            return result
            
        except Exception as e:
            return {"status": "unverified", "confidence": 0.1, "explanation": f"Could not verify due to: {str(e)[:50]}"}
    
    def check_post(self, content: str) -> Dict[str, Any]:
        """Check all claims in a post with improved scoring."""
        claims = self.extract_claims(content)
        
        if not claims:
            return {
                "status": "no_claims", 
                "claims_checked": {}, 
                "summary": "No specific factual claims found to verify"
            }
        
        checked = {}
        for claim in claims[:5]:  # Check up to 5 claims
            checked[claim] = self.verify_claim(claim)
        
        # Calculate statistics
        statuses = [r.get('status', '') for r in checked.values()]
        verified = statuses.count('verified')
        partial = statuses.count('partially_verified')
        unverified = statuses.count('unverified')
        inaccurate = statuses.count('inaccurate')
        
        # Determine overall status
        if inaccurate > 0:
            overall_status = "inaccurate"
        elif verified > 0 and partial == 0 and unverified == 0:
            overall_status = "verified"
        elif verified > 0 or partial > 0:
            overall_status = "partially_verified"
        else:
            overall_status = "unverified"
        
        return {
            "status": overall_status,
            "claims_checked": checked,
            "summary": f"Found {len(checked)} claims: {verified} verified, {partial} partial, {unverified} unverified, {inaccurate} inaccurate"
        }
