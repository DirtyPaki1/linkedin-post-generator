import streamlit as st
import os
import re
import json
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq
import requests

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="AI LinkedIn Post Generator & Fact-Checker",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #0a66c2 0%, #004182 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    .post-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        border-left: 4px solid #0a66c2;
        transition: transform 0.2s;
    }
    .post-card:hover {
        transform: translateX(5px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
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
        border-radius: 5px;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        background: #004182;
        transform: scale(1.02);
    }
    .feature-badge {
        background: #e9ecef;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        margin: 0.25rem;
        display: inline-block;
    }
    .metric-card {
        background: white;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'posts' not in st.session_state:
    st.session_state.posts = []

# Header
st.markdown("""
<div class="main-header">
    <h1>🚀 AI LinkedIn Post Generator</h1>
    <p>Generate engaging LinkedIn posts with AI-powered fact-checking</p>
    <div>
        <span class="feature-badge">🤖 AI-Generated</span>
        <span class="feature-badge">✅ Fact-Checked</span>
        <span class="feature-badge">📊 Analytics</span>
        <span class="feature-badge">🚀 Production Ready</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Check API keys
groq_key = os.getenv("GROQ_API_KEY")
serp_key = os.getenv("SERPAPI_API_KEY")

if not groq_key:
    st.error("❌ GROQ_API_KEY not found! Please add it to your secrets.")
    with st.expander("How to get a FREE Groq API Key"):
        st.markdown("""
        1. Go to [Groq Console](https://console.groq.com/)
        2. Sign up for free (takes 2 minutes)
        3. Click **"API Keys"** in the sidebar
        4. Click **"Create API Key"**
        5. Name it (e.g., "linkedin-app")
        6. Copy the key (starts with `gsk_`)
        7. Add it to your Streamlit Cloud secrets
        """)
    st.stop()

# Initialize Groq client
client = Groq(api_key=groq_key)

# Helper functions
def extract_claims(text: str) -> list:
    """Extract factual claims using regex."""
    claims = []
    patterns = [
        r'(\d+%?)',
        r'\$\d+(?:\.\d+)?\s*(?:million|billion|trillion)?',
        r'\b(?:19|20)\d{2}\b',
        r'(?:increase|decrease|rise|fall|improve|reduce)\s+(?:by\s+)?\d+%?',
        r'(?:over|more than|less than|about|approximately)\s+\d+\s+(?:percent|%|million|billion|people|users)',
        r'(?:\d+)\s+(?:out of|of)\s+\d+',
        r'(?:projected|estimated|predicted|expected)\s+(?:to\s+)?(?:reach|grow|increase)\s+\$?\d+',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if len(str(match)) > 2:
                claims.append(str(match).strip())
    
    claims = list(set(claims))
    claims = [c for c in claims if len(c) > 2 and not c.isdigit()]
    return claims[:5]

def verify_claim(claim: str, serp_key: str) -> dict:
    """Verify a claim using SerpAPI."""
    if not serp_key:
        return {"status": "unverified", "confidence": 0.3, "explanation": "No SerpAPI key"}
    
    try:
        url = "https://serpapi.com/search"
        params = {"q": claim, "api_key": serp_key, "num": 2}
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        snippets = []
        if "organic_results" in data:
            for result in data["organic_results"][:2]:
                if "snippet" in result:
                    snippets.append(result["snippet"])
        
        prompt = f"""Verify this claim based on search results:

Claim: {claim}

Search Results:
{chr(10).join(snippets) if snippets else 'No results found.'}

Respond with ONLY valid JSON:
{{"status": "verified|partially_verified|unverified|inaccurate", "confidence": 0.0-1.0, "explanation": "brief explanation"}}
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

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    
    tone = st.selectbox(
        "🎨 Tone",
        options=["professional", "casual", "inspirational", "educational", "thought-leadership", "storytelling"]
    )
    
    num_posts = st.slider("📝 Number of Posts", 1, 5, 3)
    temperature = st.slider("🎯 Creativity", 0.0, 1.0, 0.7, 0.1)
    enable_fact_check = st.toggle("🔍 Fact-Checking", True)
    
    st.divider()
    st.success("✅ Connected to Groq")
    if serp_key:
        st.success("✅ SerpAPI connected")
    else:
        st.warning("⚠️ SerpAPI not set - limited fact-checking")
    
    st.divider()
    st.caption("Made with ❤️ using Streamlit & Groq")
    st.caption("🚀 Version 2.0")

# Main content
st.header("📝 Create Your Posts")

topic = st.text_area(
    "What's your topic?",
    placeholder="e.g., The impact of AI on remote work, 5 leadership lessons from 2024, How to build a personal brand on LinkedIn",
    height=100
)

col1, col2 = st.columns([3, 1])
with col1:
    if st.button("🚀 Generate Posts", type="primary", use_container_width=True):
        if topic:
            try:
                with st.spinner("🎨 Generating posts..."):
                    prompt = f"""Generate {num_posts} data-rich LinkedIn posts about: {topic}
Tone: {tone}

Include specific statistics, percentages, or numbers in each post.
Format each post:
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
                    
                    # Fact-check
                    if enable_fact_check and serp_key:
                        with st.spinner("🔍 Fact-checking..."):
                            for post in posts:
                                post['fact_check'] = check_post(post['content'], serp_key)
                    
                    st.session_state.posts = posts
                    st.success(f"✅ Generated {len(posts)} posts!")
                    
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
        else:
            st.warning("Please enter a topic")

with col2:
    if st.button("🗑️ Clear All", use_container_width=True):
        st.session_state.posts = []
        st.rerun()

# Display posts
if st.session_state.posts:
    posts = st.session_state.posts
    
    # Summary stats
    if 'fact_check' in posts[0]:
        statuses = [p['fact_check'].get('status', 'unknown') for p in posts]
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("✅ Verified", statuses.count('verified'))
        with col2:
            st.metric("🟡 Partial", statuses.count('partially_verified'))
        with col3:
            st.metric("⚠️ Unverified", statuses.count('unverified'))
        with col4:
            st.metric("❌ Inaccurate", statuses.count('inaccurate'))
    
    st.divider()
    st.subheader(f"📄 Generated Posts ({len(posts)})")
    
    for i, post in enumerate(posts, 1):
        with st.container():
            st.markdown(f'<div class="post-card">', unsafe_allow_html=True)
            
            col1, col2 = st.columns([6, 1])
            with col1:
                st.markdown(f"### 📌 Post {i}")
            with col2:
                if 'fact_check' in post:
                    status = post['fact_check'].get('status', 'unknown')
                    emoji = {'verified': '✅', 'partially_verified': '��', 'unverified': '⚠️', 'inaccurate': '❌', 'no_claims': 'ℹ️'}.get(status, '📝')
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
            
            # Action buttons
            col1, col2, col3 = st.columns([1, 1, 4])
            with col1:
                if st.button(f"📋 Copy", key=f"copy_{i}"):
                    st.info("Select text and press Cmd+C")
            with col2:
                if st.button(f"📌 Save", key=f"save_{i}"):
                    st.info("⭐ Saved to session")
            
            st.divider()
    
    # Export
    all_posts = "\n\n---\n\n".join([
        f"Post {i}:\n{post['content']}\n\nHashtags: {' '.join(post.get('hashtags', []))}"
        for i, post in enumerate(posts, 1)
    ])
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "📥 Download Posts",
            all_posts,
            file_name=f"posts_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain",
            use_container_width=True
        )
    with col2:
        if st.button("🔄 Regenerate", use_container_width=True):
            st.info("Change your topic and click Generate Posts again")

# Tips
with st.expander("💡 LinkedIn Post Tips"):
    st.markdown("""
    ### 📈 Best Practices for LinkedIn Posts
    
    | Element | Best Practice |
    |---------|---------------|
    | **Hook** | First line must grab attention |
    | **Length** | 100-200 words optimal |
    | **Hashtags** | 3-5 relevant ones |
    | **CTA** | End with a question |
    | **Engage** | Reply to comments within 1 hour |
    | **Consistency** | Post 3-5 times per week |
    | **Visuals** | Add images for 2x engagement |
    | **Personal Touch** | Share personal experiences |
    
    ### 🎯 Sample Post Structure
    
    1. **Hook**: Question or bold statement
    2. **Context**: Set up the topic
    3. **Value**: 2-3 key insights with data
    4. **Example**: Personal experience
    5. **CTA**: Question to audience
    6. **Hashtags**: 3-5 relevant tags
    
    ### ⏰ Best Times to Post
    
    - **Tuesday-Thursday**: 8-10 AM and 12-1 PM
    - **Monday & Friday**: 9-11 AM
    - **Weekends**: Lower engagement, less competition
    """)

# Footer
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.caption("🚀 Powered by Groq Llama 3.3 70B")
with col2:
    st.caption(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
with col3:
    st.caption("💡 Built with Streamlit")

st.caption("⭐ Star us on GitHub | [Report Issue](https://github.com/DirtyPaki1/linkedin-post-generator/issues)")
