import streamlit as st
import os
from datetime import datetime
from dotenv import load_dotenv
from agents import PostGenerator, FactChecker
from config import get_settings

load_dotenv()
settings = get_settings()

st.set_page_config(
    page_title="AI LinkedIn Post Generator & Fact-Checker",
    page_icon="🚀",
    layout="wide"
)

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

st.title("�� AI LinkedIn Post Generator & Fact-Checker")
st.markdown("Generate data-driven LinkedIn posts with AI-powered fact-checking")

if not settings.groq_api_key:
    st.error("❌ GROQ_API_KEY not found! Please add it to .env file")
    st.stop()

with st.sidebar:
    st.header("⚙️ Settings")
    tone = st.selectbox("Tone", ["professional", "casual", "inspirational", "educational", "thought-leadership"])
    num_posts = st.slider("Number of Posts", 1, 5, 3)
    temperature = st.slider("Creativity", 0.0, 1.0, 0.7, 0.1)
    enable_fact_check = st.toggle("🔍 Fact-Checking", True)
    
    st.divider()
    st.success("✅ Connected to Groq")
    st.caption("🤖 Model: Llama 3.3 70B")

st.header("📝 Create Your Posts")

topic = st.text_area(
    "What's your topic?",
    placeholder="e.g., The impact of remote work on productivity, AI adoption statistics, Leadership trends in 2024",
    height=100
)

if st.button("🚀 Generate Posts", type="primary", use_container_width=True):
    if topic:
        try:
            with st.spinner("🎨 Generating posts..."):
                generator = PostGenerator(temperature=temperature)
                posts = generator.generate_posts(topic=topic, tone=tone, num_posts=num_posts)
                
                if enable_fact_check and settings.enable_fact_checking:
                    st.info("🔍 Fact-checking posts...")
                    checker = FactChecker()
                    for post in posts:
                        post['fact_check'] = checker.check_post(post['content'])
                
                st.session_state['posts'] = posts
                st.success(f"✅ Generated {len(posts)} posts!")
                
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.info("💡 Make sure your GROQ_API_KEY is valid")
    else:
        st.warning("Please enter a topic")

if 'posts' in st.session_state and st.session_state['posts']:
    posts = st.session_state['posts']
    
    st.divider()
    st.subheader(f"📄 Generated Posts ({len(posts)})")
    
    # Show summary stats
    if 'fact_check' in posts[0]:
        statuses = [p['fact_check'].get('status', 'unknown') for p in posts]
        emojis = {'verified': '✅', 'partially_verified': '🟡', 'unverified': '⚠️', 'inaccurate': '❌', 'no_claims': 'ℹ️'}
        summary = " | ".join([f"{emojis.get(s, '❓')} {s.replace('_', ' ').title()}" for s in set(statuses) if s in emojis])
        st.info(f"📊 Fact-Check Summary: {summary}")
        
        # Show detailed stats
        total_claims = 0
        verified_total = 0
        for post in posts:
            if 'fact_check' in post:
                fc = post['fact_check']
                if fc.get('claims_checked'):
                    total_claims += len(fc['claims_checked'])
                    statuses = [r.get('status', '') for r in fc['claims_checked'].values()]
                    verified_total += statuses.count('verified')
        
        if total_claims > 0:
            st.caption(f"📈 {total_claims} total claims checked across all posts")
    
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
            
            st.markdown(f"{post.get('content', '')}")
            
            if post.get('hashtags'):
                st.markdown("**Hashtags:** " + " ".join(post['hashtags']))
            
            if 'fact_check' in post:
                fc = post['fact_check']
                status = fc.get('status', 'unknown')
                st.markdown(f"**Fact-Check Status:** <span class='status-{status}'>{status.upper().replace('_', ' ')}</span>", unsafe_allow_html=True)
                
                if fc.get('claims_checked'):
                    with st.expander(f"🔍 View Fact-Check Details ({len(fc['claims_checked'])} claims)"):
                        st.caption(fc.get('summary', ''))
                        for claim, result in fc['claims_checked'].items():
                            status = result.get('status', 'unknown')
                            status_icon = {'verified': '✅', 'partially_verified': '🟡', 'unverified': '⚠️', 'inaccurate': '❌'}.get(status, '❓')
                            confidence = result.get('confidence', 0)
                            st.markdown(f"- {status_icon} **{claim[:80]}...**" if len(claim) > 80 else f"- {status_icon} **{claim}**")
                            st.caption(f"  {result.get('explanation', 'No explanation')} (Confidence: {confidence:.0%})")
                else:
                    st.caption("No factual claims found to verify")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button(f"📋 Copy", key=f"copy_{i}"):
                    st.info("Select text and press Cmd+C")
            
            st.divider()
    
    # Export
    all_posts = "\n\n---\n\n".join([
        f"Post {i}:\n{post['content']}\n\nHashtags: {' '.join(post.get('hashtags', []))}"
        for i, post in enumerate(posts, 1)
    ])
    
    st.download_button(
        "📥 Download All Posts",
        all_posts,
        file_name=f"posts_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
        mime="text/plain"
    )

# Footer
st.markdown("---")
st.caption("🚀 Powered by Groq Llama 3.3 70B | Built with Streamlit")
