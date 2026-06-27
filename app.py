import streamlit as st
import os
import re
import json
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq
import requests

load_dotenv()

st.set_page_config(
    page_title="AI LinkedIn Post Generator & Fact-Checker",
    page_icon="🚀",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .post-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        border-left: 4px solid #0a66c2;
    }
    .status-verified { color: #28a745; font-weight: bold; }
    .status-partially_verified { color: #fd7e14; font-weight: bold; }
    .status-unverified { color: #ffc107; font-weight: bold; }
    .status-inaccurate { color: #dc3545; font-weight: bold; }
    .status-no_claims { color: #6c757d; font-weight: bold; }
    .stButton > button {
        background: #0a66c2;
        color: white;
        font-weight: bold;
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

st.title("🚀 AI LinkedIn Post Generator & Fact-Checker")
st.markdown("Generate posts with AI-powered fact-checking")

# Check API keys
groq_key = os.getenv("GROQ_API_KEY")
serp_key = os.getenv("SERPAPI_API_KEY")

if not groq_key:
    st.error("❌ GROQ_API_KEY not found! Please add it to secrets.")
    st.stop()

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    tone = st.selectbox("Tone", ["professional", "casual", "inspirational", "educational"])
    num_posts = st.slider("Number of Posts", 1, 5, 3)
    temperature = st.slider("Creativity", 0.0, 1.0, 0.7, 0.1)
    enable_fact_check = st.toggle("🔍 Fact-Checking", True)
    
    st.divider()
    st.success("✅ Connected to Groq")
    if serp_key:
        st.success("✅ SerpAPI connected")
    else:
        st.warning("⚠️ SerpAPI not set - fact-checking limited")

# Initialize Groq client
client = Groq(api_key=groq_key)

def extract_claims(text: str) -> list:
    """Extract factual claims using regex."""
    claims = []
    patterns = [
        r'(\d+%?)',
        r'\$\d+(?:\.\d+)?\s*(?:million|billion)?',
        r'\b(?:19|20)\d{2}\b',
        r'(?:increase|decrease|rise|fall)\s+(?:by\s+)?\d+%?',
        r'(?:over|more than|less than|about)\s+\d+\s+(?:percent|%|million|billion)',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if len(str(match)) > 2:
                claims.append(str(match).strip())
    
    # Remove duplicates and short claims
    claims = list(set(claims))
    claims = [c for c in claims if len(c) > 2 and not c.isdigit()]
    return claims[:5]

def verify_claim(claim: str, serp_key: str) -> dict:
    """Verify a claim using SerpAPI."""
    if not serp_key:
        return {"status": "unverified", "confidence": 0.3, "explanation": "No SerpAPI key"}
    
    try:
        # Search the web
        url = "https://serpapi.com/search"
        params = {"q": claim, "api_key": serp_key, "num": 2}
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        snippets = []
        if "organic_results" in data:
            for result in data["organic_results"][:2]:
                if "snippet" in result:
                    snippets.append(result["snippet"])
        
        # Use Groq to evaluate
        prompt = f"""Verify this claim based on search results:

Claim: {claim}

Search Results:
{chr(10).join(snippets) if snippets else 'No results found.'}

Respond with ONLY valid JSON:
{{"status": "verified|partially_verified|unverified|inaccurate", "confidence": 0.0-1.0, "explanation": "brief"}}
"""
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=200
        )
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        return {"status": "unverified", "confidence": 0.0, "explanation": str(e)[:50]}

def check_post(content: str, serp_key: str) -> dict:
    """Fact-check a post."""
    claims = extract_claims(content)
    
    if not claims:
        return {"status": "no_claims", "claims_checked": {}, "summary": "No claims found"}
    
    checked = {}
    for claim in claims[:3]:
        checked[claim] = verify_claim(claim, serp_key)
    
    # Count statuses
    statuses = [r.get('status', '') for r in checked.values()]
    verified = statuses.count('verified')
    partial = statuses.count('partially_verified')
    inaccurate = statuses.count('inaccurate')
    
    if inaccurate > 0:
        overall = "inaccurate"
    elif verified > 0 and partial == 0:
        overall = "verified"
    elif verified > 0 or partial > 0:
        overall = "partially_verified"
    else:
        overall = "unverified"
    
    return {
        "status": overall,
        "claims_checked": checked,
        "summary": f"Checked {len(checked)} claims: {verified} verified, {partial} partial, {inaccurate} inaccurate"
    }

# Main content
st.header("📝 Create Your Posts")
topic = st.text_area("What's your topic?", height=100)

if st.button("🚀 Generate Posts", type="primary", use_container_width=True):
    if topic:
        try:
            with st.spinner("Generating posts..."):
                prompt = f"""Generate {num_posts} data-rich LinkedIn posts about: {topic}
Tone: {tone}

Include specific statistics, percentages, or numbers in each post.
Format:
---POST 1---
[Content with facts]
Hashtags: #tag1 #tag2
"""
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=2000
                )
                
                content = response.choices[0].message.content
                blocks = re.split(r'---POST \d+---', content)
                posts = []
                
                for block in blocks:
                    if block.strip():
                        hashtag_match = re.search(r'Hashtags?:\s*(.+?)(?:\n|$)', block, re.IGNORECASE)
                        hashtags = []
                        if hashtag_match:
                            hashtags = [tag.strip() for tag in re.findall(r'#\w+', hashtag_match.group(1))]
                        
                        text = block
                        if hashtag_match:
                            text = block[:block.lower().find('hashtags:')]
                        text = text.strip()
                        
                        if text and len(text) > 20:
                            posts.append({'content': text, 'hashtags': hashtags})
                
                # Fact-check each post
                if enable_fact_check and serp_key:
                    with st.spinner("🔍 Fact-checking..."):
                        for post in posts:
                            post['fact_check'] = check_post(post['content'], serp_key)
                
                st.session_state['posts'] = posts
                st.success(f"✅ Generated {len(posts)} posts!")
                
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.info("💡 Make sure your API keys are valid")

# Display posts
if 'posts' in st.session_state:
    posts = st.session_state['posts']
    
    # Summary stats
    if 'fact_check' in posts[0]:
        statuses = [p['fact_check'].get('status', 'unknown') for p in posts]
        st.info(f"📊 Fact-Check Summary: ✅ {statuses.count('verified')} verified | 🟡 {statuses.count('partially_verified')} partial | ⚠️ {statuses.count('unverified')} unverified | ❌ {statuses.count('inaccurate')} inaccurate")
    
    for i, post in enumerate(posts, 1):
        with st.container():
            st.markdown(f'<div class="post-card">', unsafe_allow_html=True)
            
            col1, col2 = st.columns([6, 1])
            with col1:
                st.markdown(f"### 📌 Post {i}")
            with col2:
                if 'fact_check' in post:
                    status = post['fact_check'].get('status', 'unknown')
                    emoji = {'verified': '✅', 'partially_verified': '🟡', 'unverified': '⚠️', 'inaccurate': '❌', 'no_claims': 'ℹ️'}.get(status, '📝')
                    st.markdown(f"**{emoji}**")
            
            st.markdown(post.get('content', ''))
            if post.get('hashtags'):
                st.markdown("**Hashtags:** " + " ".join(post['hashtags']))
            
            if 'fact_check' in post:
                fc = post['fact_check']
                status = fc.get('status', 'unknown')
                st.markdown(f"**Fact-Check Status:** <span class='status-{status}'>{status.upper().replace('_', ' ')}</span>", unsafe_allow_html=True)
                
                if fc.get('claims_checked'):
                    with st.expander(f"🔍 View Details ({len(fc['claims_checked'])} claims)"):
                        st.caption(fc.get('summary', ''))
                        for claim, result in fc['claims_checked'].items():
                            status_icon = {'verified': '✅', 'partially_verified': '🟡', 'unverified': '⚠️', 'inaccurate': '❌'}.get(result.get('status', ''), '❓')
                            confidence = result.get('confidence', 0)
                            st.markdown(f"- {status_icon} **{claim[:60]}...**")
                            st.caption(f"  {result.get('explanation', '')} (Confidence: {confidence:.0%})")
            
            st.markdown('</div>', unsafe_allow_html=True)
            st.divider()
    
    # Export
    all_posts = "\n\n---\n\n".join([
        f"Post {i}:\n{post['content']}\n\nHashtags: {' '.join(post.get('hashtags', []))}"
        for i, post in enumerate(posts, 1)
    ])
    st.download_button("📥 Download Posts", all_posts, file_name=f"posts_{datetime.now().strftime('%Y%m%d_%H%M')}.txt", mime="text/plain")

st.markdown("---")
st.caption("🚀 Powered by Groq Llama 3.3 70B | Fact-checking by SerpAPI")
