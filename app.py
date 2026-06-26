import streamlit as st
from datetime import datetime
import time
import pandas as pd
import plotly.express as px

from config import get_settings
from agents import PostGenerator, FactChecker, AgentOrchestrator
from utils import (
    PerformanceAnalyzer, AnalyticsTracker, 
    LanguageTranslator, PostScheduler,
    get_logger, log_performance
)
from models import init_db, get_db

# Configuration
settings = get_settings()
logger = get_logger(__name__)

# Page config
st.set_page_config(
    page_title="AI LinkedIn Post Generator & Fact-Checker",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize components
@st.cache_resource
def init_components():
    """Initialize all components with caching."""
    init_db()
    return {
        'orchestrator': AgentOrchestrator(),
        'analytics': AnalyticsTracker(),
        'translator': LanguageTranslator(),
        'scheduler': PostScheduler(),
        'analyzer': PerformanceAnalyzer()
    }

components = init_components()

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    .post-card {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #2a5298;
    }
    .metric-card {
        background: white;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .status-verified { color: #28a745; }
    .status-unverified { color: #ffc107; }
    .status-inaccurate { color: #dc3545; }
    .stButton > button {
        width: 100%;
    }
    .feature-badge {
        background: #e9ecef;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        margin: 0.25rem;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🚀 AI LinkedIn Post Generator</h1>
    <p>Generate, fact-check, and optimize your LinkedIn content with AI</p>
    <div>
        <span class="feature-badge">🤖 AI-Powered</span>
        <span class="feature-badge">✅ Fact-Checking</span>
        <span class="feature-badge">📊 Analytics</span>
        <span class="feature-badge">🌍 Multi-Language</span>
        <span class="feature-badge">🔄 Scheduling</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Model selection
    model_type = st.selectbox(
        "🤖 AI Model",
        options=["groq", "google", "openai"],
        help="Groq is fastest, Google is balanced, OpenAI is most capable"
    )
    
    # Language
    lang_options = components['translator'].get_language_options()
    target_language = st.selectbox(
        "🌍 Output Language",
        options=lang_options,
        format_func=lambda x: components['translator'].get_language_name(x)
    )
    
    # Post settings
    st.subheader("📝 Post Settings")
    tone = st.selectbox(
        "Tone",
        options=["professional", "casual", "inspirational", "educational", "thought-leadership"]
    )
    length = st.selectbox(
        "Length",
        options=["short", "medium", "long"]
    )
    audience = st.text_input("Target Audience", value="professionals")
    num_posts = st.slider("Number of Posts", 1, 5, 3)
    temperature = st.slider("Creativity", 0.0, 1.0, 0.7, 0.1)
    
    # Features
    st.subheader("🔧 Features")
    enable_fact_check = st.toggle("✅ Fact-Checking", True)
    enable_analytics = st.toggle("📊 Analytics", True)
    enable_scheduling = st.toggle("🔄 Scheduling", True)
    
    # API Status
    st.divider()
    st.subheader("🔑 System Status")
    st.write(f"Database: {'✅' if settings.database_url else '❌'}")
    st.write(f"Cache: {'✅' if settings.enable_caching else '❌'}")
    st.write(f"Model: {model_type.upper()}")

# Main tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📝 Generate", "📊 Analytics", "🔄 Scheduling", 
    "🌍 Multi-Language", "💡 Insights"
])

# Initialize session state
if 'generated_posts' not in st.session_state:
    st.session_state.generated_posts = []
if 'pipeline_result' not in st.session_state:
    st.session_state.pipeline_result = None

# Tab 1: Generate
with tab1:
    st.header("📝 Generate Posts")
    
    # Input
    topic = st.text_area(
        "What's your topic?",
        placeholder="e.g., The future of AI in healthcare, 5 leadership lessons, How to build a personal brand",
        height=100
    )
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        generate_button = st.button("🚀 Generate Posts", type="primary", use_container_width=True)
    with col2:
        style = st.selectbox("Style", ["default", "storytelling", "data_driven", "thought_leadership"])
    with col3:
        st.write("")  # Spacer
    
    if generate_button and topic:
        with st.spinner("Generating posts... This may take a moment."):
            try:
                orchestrator = AgentOrchestrator(model_type=model_type)
                
                result = orchestrator.create_post_pipeline(
                    topic=topic,
                    tone=tone,
                    length=length,
                    audience=audience,
                    num_posts=num_posts,
                    enable_fact_check=enable_fact_check,
                    language=target_language,
                    style=style
                )
                
                st.session_state.pipeline_result = result
                st.session_state.generated_posts = result['posts']
                
                if 'error' in result['summary']:
                    st.error(f"❌ Error: {result['summary']['error']}")
                else:
                    st.success(f"✅ Generated {len(result['posts'])} posts successfully!")
                    
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                logger.error(f"Generation error: {e}")
    
    # Display generated posts
    if st.session_state.generated_posts:
        posts = st.session_state.generated_posts
        
        st.subheader(f"📄 Generated Posts ({len(posts)})")
        
        for i, post in enumerate(posts, 1):
            with st.container():
                st.markdown(f"### 📌 Post {i}")
                
                # Language badge
                lang = post.get('language', 'en')
                st.caption(f"🌍 {components['translator'].get_language_name(lang)}")
                
                # Post content
                st.markdown(f"> {post.get('content', '')}")
                
                # Hashtags
                hashtags = post.get('hashtags', [])
                if hashtags:
                    st.markdown("**Hashtags:** " + " ".join([f"#{tag.strip()}" for tag in hashtags]))
                
                # Fact-check status
                if 'fact_check' in post:
                    fc = post['fact_check']
                    status = fc.get('status', 'unknown')
                    status_emoji = {
                        'verified': '✅', 'unverified': '⚠️', 
                        'inaccurate': '❌', 'no_claims': 'ℹ️',
                        'partially_verified': '🟡'
                    }.get(status, '📝')
                    
                    st.markdown(f"**Fact-Check:** {status_emoji} {status.upper()}")
                    
                    with st.expander("🔍 View Details"):
                        st.info(fc.get('summary', ''))
                        if 'statistics' in fc:
                            stats = fc['statistics']
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Total Claims", stats.get('total_claims', 0))
                            with col2:
                                st.metric("✅ Verified", stats.get('verified', 0))
                            with col3:
                                st.metric("⚠️ Unverified", stats.get('unverified', 0))
                            with col4:
                                st.metric("❌ Inaccurate", stats.get('inaccurate', 0))
                        
                        claims = fc.get('claims_checked', {})
                        if claims:
                            st.write("**Claims Checked:**")
                            for claim, result in claims.items():
                                status_icon = {
                                    'verified': '✅',
                                    'unverified': '⚠️',
                                    'inaccurate': '❌'
                                }.get(result.get('status', ''), '❓')
                                st.markdown(f"- {status_icon} **{claim}**")
                                if 'explanation' in result:
                                    st.caption(f"  {result['explanation']}")
                                if 'confidence' in result:
                                    st.progress(result['confidence'], text=f"Confidence: {result['confidence']:.0%}")
                
                # Analysis
                if 'analysis' in post:
                    analysis = post['analysis']
                    st.progress(analysis['score'] / 100, text=f"Engagement Score: {analysis['score']}/100")
                    
                    with st.expander("📊 Performance Analysis"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write("**Strengths:**")
                            for strength in analysis.get('strengths', []):
                                st.write(f"✅ {strength}")
                        with col2:
                            st.write("**Improvements:**")
                            for improvement in analysis.get('improvements', []):
                                st.write(f"💡 {improvement}")
                        
                        if analysis.get('suggested_hashtags'):
                            st.write("**Suggested Hashtags:**")
                            st.write(" ".join(analysis['suggested_hashtags']))
                
                st.divider()
        
        # Export options
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            export_md = "\n\n".join([
                f"## Post {i}\n{post['content']}\nHashtags: {', '.join(post.get('hashtags', []))}"
                for i, post in enumerate(posts, 1)
            ])
            st.download_button(
                "📥 Markdown",
                export_md,
                file_name=f"posts_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
            )
        with col2:
            export_txt = "\n\n".join([f"Post {i}: {post['content']}" for i, post in enumerate(posts, 1)])
            st.download_button(
                "📥 Plain Text",
                export_txt,
                file_name=f"posts_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
            )
        with col3:
            export_json = pd.DataFrame(posts).to_json()
            st.download_button(
                "📥 JSON",
                export_json,
                file_name=f"posts_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
            )
        with col4:
            if st.button("🗑️ Clear All"):
                st.session_state.generated_posts = []
                st.session_state.pipeline_result = None
                st.rerun()

# Tab 2: Analytics
with tab2:
    st.header("📊 Analytics Dashboard")
    
    if settings.enable_analytics:
        # Trends
        trends = components['analytics'].get_trends(days=30)
        
        if trends and 'error' not in trends:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Average Engagement", f"{trends.get('average_engagement', 0):.1f}%")
            with col2:
                st.metric("Best Tone", trends.get('best_tone', 'N/A'))
            with col3:
                st.metric("Most Used Tone", trends.get('most_used_tone', 'N/A'))
            with col4:
                st.metric("Total Posts", trends.get('total_posts', 0))
            
            # Chart
            chart = components['analytics'].get_engagement_chart(days=30)
            if chart:
                st.plotly_chart(chart, use_container_width=True)
            
            # Trends table
            if 'trends' in trends:
                st.subheader("Detailed Trends")
                df = pd.DataFrame(trends['trends'])
                st.dataframe(df, use_container_width=True)
        else:
            st.info("📊 Generate some posts to see analytics here")
    else:
        st.warning("Analytics feature is disabled in settings")

# Tab 3: Scheduling
with tab3:
    st.header("🔄 Automated Scheduling")
    
    if settings.enable_scheduling:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📅 Schedule New Post")
            schedule_topic = st.text_input("Topic", key="schedule_topic")
            schedule_interval = st.number_input(
                "Interval (hours)", 
                min_value=1, 
                max_value=168, 
                value=24,
                help="How often to generate posts"
            )
            schedule_tone = st.selectbox(
                "Tone", 
                options=["professional", "casual", "inspirational", "educational"],
                key="schedule_tone"
            )
            
            if st.button("📅 Schedule", type="primary"):
                if schedule_topic:
                    try:
                        job_id = components['scheduler'].schedule_post(
                            topic=schedule_topic,
                            interval_hours=schedule_interval,
                            parameters={
                                'tone': schedule_tone,
                                'length': length,
                                'audience': audience
                            }
                        )
                        st.success(f"✅ Scheduled! ID: {job_id[:20]}...")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
                else:
                    st.warning("Please enter a topic")
        
        with col2:
            st.subheader("📋 Scheduled Posts")
            scheduled = components['scheduler'].get_scheduled_posts()
            
            if scheduled:
                for job in scheduled:
                    with st.container():
                        st.markdown(f"**Topic:** {job['topic']}")
                        st.caption(f"Tone: {job['tone']} | Interval: {job['interval_hours']} hours")
                        if job['next_run']:
                            st.caption(f"Next: {job['next_run'][:16]}")
                        if st.button(f"❌ Remove", key=f"remove_{job['id']}"):
                            if components['scheduler'].unschedule_post(job['job_id']):
                                st.success("Removed!")
                                st.rerun()
                        st.divider()
            else:
                st.info("No posts scheduled")
        
        # Scheduler status
        st.subheader("📊 Scheduler Status")
        status = components['scheduler'].get_status()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Running", "✅" if status['running'] else "❌")
        with col2:
            st.metric("Active Jobs", status['jobs'])
        with col3:
            st.metric("Scheduled Posts", status['scheduled_posts'])
    else:
        st.warning("Scheduling feature is disabled in settings")

# Tab 4: Multi-Language
with tab4:
    st.header("🌍 Multi-Language Support")
    
    if settings.enable_multi_language:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Language Detection")
            sample_text = st.text_area("Paste text to detect language:", height=100)
            if sample_text and st.button("🔍 Detect"):
                detected = components['translator'].detect_language(sample_text)
                st.success(f"Detected: {detected['name']} ({detected['language']})")
                st.progress(detected['confidence'], text=f"Confidence: {detected['confidence']:.0%}")
        
        with col2:
            st.subheader("Supported Languages")
            lang_df = pd.DataFrame([
                {'Code': code, 'Name': name}
                for code, name in components['translator'].SUPPORTED_LANGUAGES.items()
            ])
            st.dataframe(lang_df, use_container_width=True)
        
        # Bulk translation
        if st.session_state.generated_posts:
            st.subheader("🔄 Translate Generated Posts")
            target_bulk_lang = st.selectbox(
                "Translate to:",
                options=lang_options,
                key="bulk_lang",
                format_func=lambda x: components['translator'].get_language_name(x)
            )
            
            if st.button("🌐 Translate All Posts"):
                with st.spinner("Translating..."):
                    translated_posts = [
                        components['translator'].translate_post(post, target_bulk_lang)
                        for post in st.session_state.generated_posts
                    ]
                    st.session_state.generated_posts = translated_posts
                    st.success("✅ All posts translated!")
                    st.rerun()
    else:
        st.warning("Multi-language feature is disabled in settings")

# Tab 5: Insights
with tab5:
    st.header("💡 Insights & Best Practices")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Performance Insights")
        
        # Show best practices
        best_practices = components['analyzer'].get_best_practices()
        for i, practice in enumerate(best_practices, 1):
            st.markdown(f"{i}. {practice}")
        
        # Engagement tips
        st.subheader("🎯 Engagement Tips")
        st.markdown("""
        - **Post at optimal times:** LinkedIn engagement peaks on Tuesdays-Thursdays, 8-10 AM and 12-1 PM
        - **Use visual content:** Posts with images get 2x more engagement
        - **Engage back:** Reply to comments within 1 hour for 3x more visibility
        - **Consistency matters:** Post 3-5 times per week for best results
        - **Tag relevant people:** Increases reach and credibility
        """)
    
    with col2:
        st.subheader("📊 Post Optimization Checklist")
        
        # Create checklist
        checklist = [
            "✅ Strong hook in first 2-3 lines",
            "✅ Personal insight or experience",
            "✅ Value-added content for audience",
            "✅ Clear call to action",
            "✅ 3-5 relevant hashtags",
            "✅ Optimal length (100-200 words)",
            "✅ Question to encourage discussion",
            "✅ Proofread for errors",
            "✅ Mobile-friendly format",
            "✅ Relevant media attachment"
        ]
        
        for item in checklist:
            st.markdown(item)
        
        # Statistics
        st.subheader("📈 LinkedIn Statistics")
        stats = {
            "Optimal post length": "100-200 words",
            "Best hashtag count": "3-5",
            "Best posting times": "Tue-Thu, 8-10 AM",
            "Ideal post frequency": "3-5x/week",
            "Engagement rate": "2-4% for B2B"
        }
        
        for key, value in stats.items():
            st.markdown(f"**{key}:** {value}")

# Footer
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.caption(f"🚀 Version 2.0 | Built with ❤️")
with col2:
    st.caption(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
with col3:
    st.caption(f"📊 {len(st.session_state.generated_posts)} posts generated this session")

# Auto-refresh scheduler status
if settings.enable_scheduling:
    import threading
    if not hasattr(st.session_state, 'scheduler_thread'):
        def run_scheduler():
            components['scheduler'].start()
        thread = threading.Thread(target=run_scheduler, daemon=True)
        thread.start()
        st.session_state.scheduler_thread = True