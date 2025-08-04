import streamlit as st
import json
import time
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Any
import re
import anthropic

# Page configuration
st.set_page_config(
    page_title="Amazon SDE II Interview Prep - AI Assistant",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for LockedIn AI style
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #FF9500 0%, #FF6B00 100%);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #FF9500;
        margin: 0.5rem 0;
    }
    .question-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .feedback-positive {
        background: #d4edda;
        border-left: 4px solid #28a745;
        padding: 1rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
    .feedback-negative {
        background: #f8d7da;
        border-left: 4px solid #dc3545;
        padding: 1rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
    .chat-message {
        padding: 0.5rem 1rem;
        margin: 0.5rem 0;
        border-radius: 10px;
    }
    .user-message {
        background: #e3f2fd;
        margin-left: 20%;
    }
    .ai-message {
        background: #f5f5f5;
        margin-right: 20%;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.current_session = datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.chat_history = []
    st.session_state.interview_sessions = []
    st.session_state.performance_data = {
        'dsa_scores': [],
        'system_design_scores': [],
        'behavioral_scores': [],
        'timestamps': []
    }
    st.session_state.current_question = None
    st.session_state.current_category = None
    st.session_state.question_start_time = None
    st.session_state.total_study_time = 0
    st.session_state.claude_client = None

# Amazon Leadership Principles
LEADERSHIP_PRINCIPLES = [
    "Customer Obsession", "Ownership", "Invent and Simplify", "Are Right, A Lot",
    "Learn and Be Curious", "Hire and Develop the Best", "Insist on the Highest Standards",
    "Think Big", "Bias for Action", "Frugality", "Earn Trust", "Dive Deep",
    "Have Backbone; Disagree and Commit", "Deliver Results", "Strive to be Earth's Best Employer",
    "Success and Scale Bring Broad Responsibility"
]

# Question banks
DSA_QUESTIONS = [
    {
        "id": 1,
        "difficulty": "Medium",
        "topic": "Arrays",
        "question": "Given an array of integers, find two numbers such that they add up to a specific target number. Return indices of the two numbers.",
        "hints": ["Think about using a hash map", "What's the time complexity?"],
        "expected_approach": "Hash map for O(n) solution"
    },
    {
        "id": 2,
        "difficulty": "Hard",
        "topic": "Dynamic Programming",
        "question": "Given a string s, find the longest palindromic substring in s. You may assume that the maximum length of s is 1000.",
        "hints": ["Consider expand around centers", "Think about Manacher's algorithm"],
        "expected_approach": "Expand around centers or dynamic programming"
    },
    {
        "id": 3,
        "difficulty": "Medium",
        "topic": "Trees",
        "question": "Given a binary tree, determine if it is a valid binary search tree (BST).",
        "hints": ["In-order traversal should be sorted", "Think about bounds"],
        "expected_approach": "In-order traversal or bounds checking"
    }
]

SYSTEM_DESIGN_QUESTIONS = [
    {
        "id": 1,
        "question": "Design a URL shortening service like bit.ly",
        "focus_areas": ["Scalability", "Database design", "Caching", "Load balancing"],
        "key_components": ["URL encoding", "Database schema", "Cache layer", "Analytics"]
    },
    {
        "id": 2,
        "question": "Design a chat system like WhatsApp",
        "focus_areas": ["Real-time messaging", "Message delivery", "Scalability", "Security"],
        "key_components": ["WebSocket connections", "Message queuing", "Database design", "Push notifications"]
    },
    {
        "id": 3,
        "question": "Design Amazon's recommendation system",
        "focus_areas": ["Machine learning", "Big data processing", "Real-time updates", "Personalization"],
        "key_components": ["Collaborative filtering", "Content-based filtering", "Real-time processing", "A/B testing"]
    }
]

BEHAVIORAL_QUESTIONS = [
    {
        "principle": "Customer Obsession",
        "question": "Tell me about a time when you had to make a decision between what was best for the customer and what was best for the business."
    },
    {
        "principle": "Ownership",
        "question": "Describe a situation where you took ownership of a problem that wasn't necessarily your responsibility."
    },
    {
        "principle": "Dive Deep",
        "question": "Tell me about a time when you had to dig deep into data or details to solve a problem."
    },
    {
        "principle": "Deliver Results",
        "question": "Give me an example of a time when you had to deliver results under a tight deadline."
    }
]

def initialize_claude_client():
    """Initialize Claude API client"""
    api_key = st.sidebar.text_input("Enter Claude API Key", type="password")
    if api_key:
        try:
            client = anthropic.Anthropic(api_key=api_key)
            st.session_state.claude_client = client
            return client
        except Exception as e:
            st.error(f"Error initializing Claude: {e}")
            return None
    return None

def get_ai_response(prompt: str, context: str = "") -> str:
    """Get response from Claude API"""
    if not st.session_state.claude_client:
        return "Please configure Claude API key in the sidebar."
    
    try:
        full_prompt = f"""
        You are an expert Amazon SDE II interview coach. You provide detailed, constructive feedback and guidance.
        
        Context: {context}
        
        User: {prompt}
        
        Provide a comprehensive response that includes:
        1. Direct answer to the question/request
        2. Specific feedback and suggestions
        3. Areas for improvement
        4. Follow-up questions if appropriate
        """
        
        message = st.session_state.claude_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1500,
            messages=[{"role": "user", "content": full_prompt}]
        )
        return message.content[0].text
    except Exception as e:
        return f"Error getting AI response: {e}"

def evaluate_answer(question: Dict, answer: str, category: str) -> Dict:
    """Evaluate user's answer using AI"""
    evaluation_prompt = f"""
    Evaluate this {category} interview answer for Amazon SDE II position:
    
    Question: {question}
    Answer: {answer}
    
    Provide evaluation in this format:
    Score: X/10
    Strengths: [list strengths]
    Weaknesses: [list areas for improvement]
    Suggestions: [specific suggestions]
    """
    
    ai_feedback = get_ai_response(evaluation_prompt)
    
    # Parse AI response to extract score
    score_match = re.search(r'Score:\s*(\d+)', ai_feedback)
    score = int(score_match.group(1)) if score_match else 5
    
    return {
        'score': score,
        'feedback': ai_feedback,
        'timestamp': datetime.now()
    }

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🚀 Amazon SDE II Interview Prep - AI Assistant</h1>
        <p>Advanced AI-powered preparation tool similar to LockedIn AI</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize Claude client
    if not st.session_state.claude_client:
        st.sidebar.header("🔑 API Configuration")
        initialize_claude_client()
        if not st.session_state.claude_client:
            st.warning("Please enter your Claude API key in the sidebar to continue.")
            return
    
    # Sidebar navigation
    st.sidebar.header("📊 Dashboard")
    page = st.sidebar.selectbox(
        "Choose Mode",
        ["🏠 Dashboard", "💬 AI Chat Coach", "📝 Mock Interview", "📈 Progress Tracking", "📚 Resources"]
    )
    
    if page == "🏠 Dashboard":
        show_dashboard()
    elif page == "💬 AI Chat Coach":
        show_chat_coach()
    elif page == "📝 Mock Interview":
        show_mock_interview()
    elif page == "📈 Progress Tracking":
        show_progress_tracking()
    elif page == "📚 Resources":
        show_resources()

def show_dashboard():
    """Main dashboard showing overview"""
    st.header("📊 Interview Preparation Dashboard")
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3>🎯 Readiness Score</h3>
            <h2>75%</h2>
            <p>Good progress!</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <h3>⏱️ Study Time</h3>
            <h2>12.5h</h2>
            <p>This week</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <h3>📝 Questions Solved</h3>
            <h2>47</h2>
            <p>Total completed</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="metric-card">
            <h3>🎯 Mock Interviews</h3>
            <h2>8</h2>
            <p>Completed</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Progress charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Performance Trends")
        # Sample data for demonstration
        dates = pd.date_range(start='2024-01-01', periods=10, freq='D')
        scores = [6, 6.5, 7, 7.2, 7.5, 7.8, 8, 8.2, 8.1, 8.3]
        
        fig = px.line(x=dates, y=scores, title="Average Interview Scores Over Time")
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🎯 Skill Breakdown")
        skills = ['DSA', 'System Design', 'Behavioral', 'Coding Style']
        scores = [8.2, 7.5, 8.8, 7.9]
        
        fig = go.Figure(data=go.Scatterpolar(
            r=scores,
            theta=skills,
            fill='toself'
        ))
        fig.update_layout(height=300, polar=dict(radialaxis=dict(range=[0, 10])))
        st.plotly_chart(fig, use_container_width=True)
    
    # Quick actions
    st.subheader("🚀 Quick Actions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Start DSA Practice", use_container_width=True):
            st.session_state.quick_start = "dsa"
            st.rerun()
    
    with col2:
        if st.button("System Design Mock", use_container_width=True):
            st.session_state.quick_start = "system_design"
            st.rerun()
    
    with col3:
        if st.button("Behavioral Practice", use_container_width=True):
            st.session_state.quick_start = "behavioral"
            st.rerun()

def show_chat_coach():
    """AI Chat Coach interface"""
    st.header("💬 AI Interview Coach")
    st.write("Chat with your AI coach for personalized guidance and feedback.")
    
    # Chat interface
    chat_container = st.container()
    
    with chat_container:
        # Display chat history
        for i, message in enumerate(st.session_state.chat_history):
            if message['role'] == 'user':
                st.markdown(f"""
                <div class="chat-message user-message">
                    <strong>You:</strong> {message['content']}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="chat-message ai-message">
                    <strong>AI Coach:</strong> {message['content']}
                </div>
                """, unsafe_allow_html=True)
    
    # Chat input
    user_input = st.chat_input("Ask your AI coach anything about the interview...")
    
    if user_input:
        # Add user message to history
        st.session_state.chat_history.append({
            'role': 'user',
            'content': user_input,
            'timestamp': datetime.now()
        })
        
        # Get AI response
        context = f"Amazon SDE II interview preparation. User has been practicing for the interview in 3 days."
        ai_response = get_ai_response(user_input, context)
        
        # Add AI response to history
        st.session_state.chat_history.append({
            'role': 'assistant',
            'content': ai_response,
            'timestamp': datetime.now()
        })
        
        st.rerun()
    
    # Suggested questions
    st.subheader("💡 Suggested Questions")
    suggestions = [
        "How should I structure my system design answers?",
        "What are the most important Amazon Leadership Principles to focus on?",
        "How can I improve my coding interview performance?",
        "What are common mistakes in behavioral interviews?",
        "How should I prepare for the bar raiser round?"
    ]
    
    for suggestion in suggestions:
        if st.button(suggestion, key=f"suggestion_{suggestion}"):
            st.session_state.chat_history.append({
                'role': 'user',
                'content': suggestion,
                'timestamp': datetime.now()
            })
            
            context = f"Amazon SDE II interview preparation. User has been practicing for the interview in 3 days."
            ai_response = get_ai_response(suggestion, context)
            
            st.session_state.chat_history.append({
                'role': 'assistant',
                'content': ai_response,
                'timestamp': datetime.now()
            })
            
            st.rerun()

def show_mock_interview():
    """Mock interview interface"""
    st.header("📝 Mock Interview Session")
    
    # Interview type selection
    interview_type = st.selectbox(
        "Select Interview Type",
        ["Data Structures & Algorithms", "System Design", "Behavioral (Leadership Principles)"]
    )
    
    if interview_type == "Data Structures & Algorithms":
        show_dsa_interview()
    elif interview_type == "System Design":
        show_system_design_interview()
    else:
        show_behavioral_interview()

def show_dsa_interview():
    """DSA mock interview"""
    st.subheader("💻 Data Structures & Algorithms")
    
    if st.button("Generate New DSA Question"):
        question = DSA_QUESTIONS[len(st.session_state.chat_history) % len(DSA_QUESTIONS)]
        st.session_state.current_question = question
        st.session_state.current_category = "DSA"
        st.session_state.question_start_time = datetime.now()
    
    if st.session_state.current_question and st.session_state.current_category == "DSA":
        question = st.session_state.current_question
        
        st.markdown(f"""
        <div class="question-card">
            <h4>🎯 {question['topic']} - {question['difficulty']}</h4>
            <p><strong>Question:</strong> {question['question']}</p>
            <p><strong>Hints:</strong> {', '.join(question['hints'])}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Code input
        st.subheader("💻 Your Solution")
        language = st.selectbox("Programming Language", ["Python", "Java", "C++", "JavaScript"])
        
        code_solution = st.text_area(
            "Write your code solution:",
            height=300,
            placeholder="def solution(nums, target):\n    # Your code here\n    pass"
        )
        
        # Explanation input
        explanation = st.text_area(
            "Explain your approach and time/space complexity:",
            height=150,
            placeholder="My approach is to..."
        )
        
        if st.button("Submit Solution", type="primary"):
            if code_solution and explanation:
                # Evaluate the solution
                full_answer = f"Code:\n{code_solution}\n\nExplanation:\n{explanation}"
                evaluation = evaluate_answer(question['question'], full_answer, "DSA")
                
                # Store performance data
                st.session_state.performance_data['dsa_scores'].append(evaluation['score'])
                st.session_state.performance_data['timestamps'].append(datetime.now())
                
                # Show feedback
                if evaluation['score'] >= 7:
                    st.markdown(f"""
                    <div class="feedback-positive">
                        <h4>✅ Great Job! Score: {evaluation['score']}/10</h4>
                        <p>{evaluation['feedback']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="feedback-negative">
                        <h4>📈 Room for Improvement - Score: {evaluation['score']}/10</h4>
                        <p>{evaluation['feedback']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Clear current question
                st.session_state.current_question = None
                st.session_state.current_category = None
            else:
                st.error("Please provide both code solution and explanation.")

def show_system_design_interview():
    """System design mock interview"""
    st.subheader("🏗️ System Design")
    
    if st.button("Generate New System Design Question"):
        question = SYSTEM_DESIGN_QUESTIONS[len(st.session_state.chat_history) % len(SYSTEM_DESIGN_QUESTIONS)]
        st.session_state.current_question = question
        st.session_state.current_category = "System Design"
        st.session_state.question_start_time = datetime.now()
    
    if st.session_state.current_question and st.session_state.current_category == "System Design":
        question = st.session_state.current_question
        
        st.markdown(f"""
        <div class="question-card">
            <h4>🎯 {question['question']}</h4>
            <p><strong>Focus Areas:</strong> {', '.join(question['focus_areas'])}</p>
            <p><strong>Key Components:</strong> {', '.join(question['key_components'])}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # System design response sections
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📋 Requirements & Scale")
            requirements = st.text_area(
                "Functional and Non-functional Requirements:",
                height=150,
                placeholder="Functional: Users can...\nNon-functional: Handle 1M users..."
            )
            
            st.subheader("🎯 High-Level Design")
            high_level = st.text_area(
                "High-level architecture:",
                height=150,
                placeholder="Client -> Load Balancer -> API Gateway..."
            )
        
        with col2:
            st.subheader("🗄️ Database Design")
            database = st.text_area(
                "Database schema and choices:",
                height=150,
                placeholder="Tables, relationships, indexing..."
            )
            
            st.subheader("⚡ Deep Dive")
            deep_dive = st.text_area(
                "Detailed component discussion:",
                height=150,
                placeholder="Caching strategy, load balancing..."
            )
        
        if st.button("Submit Design", type="primary"):
            if all([requirements, high_level, database, deep_dive]):
                full_answer = f"Requirements: {requirements}\nHigh-level: {high_level}\nDatabase: {database}\nDeep dive: {deep_dive}"
                evaluation = evaluate_answer(question['question'], full_answer, "System Design")
                
                # Store performance data
                st.session_state.performance_data['system_design_scores'].append(evaluation['score'])
                st.session_state.performance_data['timestamps'].append(datetime.now())
                
                # Show feedback
                if evaluation['score'] >= 7:
                    st.markdown(f"""
                    <div class="feedback-positive">
                        <h4>✅ Excellent Design! Score: {evaluation['score']}/10</h4>
                        <p>{evaluation['feedback']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="feedback-negative">
                        <h4>📈 Areas to Improve - Score: {evaluation['score']}/10</h4>
                        <p>{evaluation['feedback']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Clear current question
                st.session_state.current_question = None
                st.session_state.current_category = None
            else:
                st.error("Please fill in all sections of the system design.")

def show_behavioral_interview():
    """Behavioral interview with STAR format"""
    st.subheader("🎭 Behavioral Interview (Leadership Principles)")
    
    if st.button("Generate New Behavioral Question"):
        question = BEHAVIORAL_QUESTIONS[len(st.session_state.chat_history) % len(BEHAVIORAL_QUESTIONS)]
        st.session_state.current_question = question
        st.session_state.current_category = "Behavioral"
        st.session_state.question_start_time = datetime.now()
    
    if st.session_state.current_question and st.session_state.current_category == "Behavioral":
        question = st.session_state.current_question
        
        st.markdown(f"""
        <div class="question-card">
            <h4>🎯 {question['principle']}</h4>
            <p><strong>Question:</strong> {question['question']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.subheader("⭐ STAR Format Response")
        st.info("Structure your answer using the STAR method: Situation, Task, Action, Result")
        
        # STAR format inputs
        col1, col2 = st.columns(2)
        
        with col1:
            situation = st.text_area(
                "🎬 Situation:",
                height=100,
                placeholder="Describe the context and background..."
            )
            
            action = st.text_area(
                "⚡ Action:",
                height=100,
                placeholder="What specific actions did you take..."
            )
        
        with col2:
            task = st.text_area(
                "📋 Task:",
                height=100,
                placeholder="What was your responsibility or goal..."
            )
            
            result = st.text_area(
                "🎯 Result:",
                height=100,
                placeholder="What was the outcome and impact..."
            )
        
        if st.button("Submit STAR Response", type="primary"):
            if all([situation, task, action, result]):
                full_answer = f"Situation: {situation}\nTask: {task}\nAction: {action}\nResult: {result}"
                evaluation = evaluate_answer(question['question'], full_answer, "Behavioral")
                
                # Store performance data
                st.session_state.performance_data['behavioral_scores'].append(evaluation['score'])
                st.session_state.performance_data['timestamps'].append(datetime.now())
                
                # Show feedback
                if evaluation['score'] >= 7:
                    st.markdown(f"""
                    <div class="feedback-positive">
                        <h4>✅ Strong STAR Response! Score: {evaluation['score']}/10</h4>
                        <p>{evaluation['feedback']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="feedback-negative">
                        <h4>📈 Strengthen Your STAR - Score: {evaluation['score']}/10</h4>
                        <p>{evaluation['feedback']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Clear current question
                st.session_state.current_question = None
                st.session_state.current_category = None
            else:
                st.error("Please complete all STAR components.")

def show_progress_tracking():
    """Progress tracking and analytics"""
    st.header("📈 Progress Tracking & Analytics")
    
    # Performance overview
    if st.session_state.performance_data['timestamps']:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.session_state.performance_data['dsa_scores']:
                avg_dsa = sum(st.session_state.performance_data['dsa_scores']) / len(st.session_state.performance_data['dsa_scores'])
                st.metric("DSA Average", f"{avg_dsa:.1f}/10", f"+{avg_dsa-5:.1f}")
        
        with col2:
            if st.session_state.performance_data['system_design_scores']:
                avg_sys = sum(st.session_state.performance_data['system_design_scores']) / len(st.session_state.performance_data['system_design_scores'])
                st.metric("System Design Average", f"{avg_sys:.1f}/10", f"+{avg_sys-5:.1f}")
        
        with col3:
            if st.session_state.performance_data['behavioral_scores']:
                avg_beh = sum(st.session_state.performance_data['behavioral_scores']) / len(st.session_state.performance_data['behavioral_scores'])
                st.metric("Behavioral Average", f"{avg_beh:.1f}/10", f"+{avg_beh-5:.1f}")
        
        # Detailed charts
        st.subheader("📊 Performance Trends")
        
        # Create a comprehensive performance DataFrame
        all_scores = []
        all_types = []
        all_timestamps = []
        
        for i, score in enumerate(st.session_state.performance_data['dsa_scores']):
            all_scores.append(score)
            all_types.append('DSA')
            all_timestamps.append(st.session_state.performance_data['timestamps'][i])
        
        if all_scores:
            df = pd.DataFrame({
                'Score': all_scores,
                'Type': all_types,
                'Timestamp': all_timestamps
            })
            
            fig = px.line(df, x='Timestamp', y='Score', color='Type', title="Score Progression Over Time")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Complete some mock interviews to see your progress here!")
    
    # Study recommendations
    st.subheader("🎯 Personalized Recommendations")
    
    recommendations = [
        "Focus on dynamic programming problems - detected weakness in recent DSA sessions",
        "Practice more system design scalability questions",
        "Work on Leadership Principle: 'Dive Deep' - strengthen your examples",
        "Schedule a full mock interview session tomorrow"
    ]
    
    for rec in recommendations:
        st.markdown(f"• {rec}")

def show_resources():
    """Curated resources and links"""
    st.header("📚 Interview Resources & Links")
    
    tabs = st.tabs(["🔗 External Resources", "📖 Study Guides", "🎥 Video Resources"])
    
    with tabs[0]:
        st.subheader("Essential Preparation Links")
        
        resources = {
            "LeetCode": "https://leetcode.com/problemset/all/",
            "System Design Primer": "https://github.com/donnemartin/system-design-primer",
            "Grokking the System Design": "https://www.educative.io/courses/grokking-the-system-design-interview",
            "Amazon Leadership Principles": "https://www.amazon.jobs/en/principles",
            "Glassdoor Amazon Reviews": "https://www.glassdoor.com/Interview/Amazon-Interview-Questions-E6036.htm"
        }
        
        for name, url in resources.items():
            st.markdown(f"[{name}]({url})")
    
    with tabs[1]:
        st.subheader("Study Guides")
        st.markdown("""
        ## DSA Study Plan (3 days)
        - **Day 1**: Arrays, Strings, Hash Maps (8 problems)
        - **Day 2**: Trees, Graphs, Dynamic Programming (6 problems)  
        - **Day 3**: Review and mock interviews
        
        ## System Design Checklist
        - [ ] Requirements gathering
        - [ ] Capacity estimation
        - [ ] High-level design
        - [ ] Database design
        - [ ] Detailed component design
        - [ ] Scaling and optimization
        
        ## Leadership Principles Focus
        - **Customer Obsession**: 2 stories prepared
        - **Ownership**: 2 stories prepared
        - **Dive Deep**: 1 technical deep-dive story
        - **Deliver Results**: 1 challenging project story
        """)
    
    with tabs[2]:
        st.subheader("Recommended Videos")
        video_resources = [
            "Amazon System Design Interview - Real Example",
            "Leadership Principles Deep Dive",
            "Coding Interview Strategies",
            "Behavioral Interview Best Practices"
        ]
        
        for video in video_resources:
            st.markdown(f"🎥 {video}")

if __name__ == "__main__":
    main()