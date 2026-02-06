import streamlit as st
import json
import sys
from openai import OpenAI

# --- 1. SETUP: Fix Console Encoding ---
try:
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# --- 2. CONFIG: Page Setup ---
st.set_page_config(
    page_title="The Molecular Man - Mock Test",
    page_icon="🧬",
    layout="centered",
    initial_sidebar_state="collapsed" 
)

# --- 3. STYLING: HIGH VISIBILITY OVERRIDE ---
st.markdown("""
<style>
    /* GLOBAL: Force light mode text on teal background */
    .stApp {
        background: linear-gradient(135deg, #4a90a4 0%, #6bb5c7 50%, #8fd4e3 100%) !important;
        color: #000000 !important;
    }

    /* CONTAINER STYLING */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: rgba(255, 255, 255, 0.9);
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    /* INPUT FIELDS */
    .stTextInput input, 
    .stSelectbox div[data-baseweb="select"] > div, 
    .stNumberInput input {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #4a90a4 !important;
    }
    
    /* DROPDOWN MENUS */
    div[data-baseweb="popover"] {
        background-color: #ffffff !important;
    }
    div[data-baseweb="menu"] {
        background-color: #ffffff !important;
        color: #000000 !important;
    }
    div[role="option"] {
        color: #000000 !important;
    }

    /* TEXT AREAS */
    .stTextArea textarea {
        background-color: #ffffff !important;
        color: #000000 !important;
    }

    /* --- BUTTON STYLING FIX --- */
    /* Target Standard Buttons AND Form Submit Buttons */
    .stButton > button, div[data-testid="stFormSubmitButton"] > button {
        background: #1e3a5f !important;
        color: #ffffff !important;
        border: 2px solid white !important;
        font-weight: bold !important;
        padding: 10px 24px !important;
        border-radius: 8px !important;
        width: 100%;
    }
    
    /* CRITICAL FIX: Force inner text of the Submit button to be white */
    div[data-testid="stFormSubmitButton"] > button p {
        color: #ffffff !important;
    }

    /* HOVER EFFECT */
    .stButton > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {
        background: #2c5282 !important;
        transform: scale(1.02);
        border-color: #ffd700 !important;
    }
    /* Ensure hover text remains white */
    div[data-testid="stFormSubmitButton"] > button:hover p {
        color: #ffffff !important;
    }

    /* RADIO BUTTONS */
    .stRadio label {
        color: #000000 !important;
        font-weight: 500 !important;
    }

    /* HEADERS */
    h1, h2, h3, h4 {
        color: #0d1b2a !important;
        font-family: sans-serif;
    }
    
    /* HIDE MENU */
    #MainMenu {visibility: hidden;} 
    footer {visibility: hidden;}    
    .stDeployButton {display: none;} 
    section[data-testid="stSidebar"] {display: none;}
</style>
""", unsafe_allow_html=True)

# --- 4. STATE: Initialize Session Variables ---
if 'questions' not in st.session_state:
    st.session_state.questions = None
if 'user_answers' not in st.session_state:
    st.session_state.user_answers = {}
if 'feedback' not in st.session_state:
    st.session_state.feedback = None
if 'score' not in st.session_state:
    st.session_state.score = 0
if 'total_marks' not in st.session_state:
    st.session_state.total_marks = 0
if 'available_models' not in st.session_state:
    st.session_state.available_models = []
if 'q_type' not in st.session_state:
    st.session_state.q_type = "MCQ"

# --- 5. FUNCTIONS: API & Logic ---

def get_groq_client(api_key):
    return OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
    )

def fetch_available_models(api_key):
    try:
        client = get_groq_client(api_key)
        models = client.models.list()
        return sorted([m.id for m in models.data])
    except Exception:
        return []

def clean_input(text):
    if not text: return ""
    return text.encode('ascii', 'ignore').decode('ascii').strip()

def generate_questions_groq(api_key, model, board, cls, sub, chap, num, diff, q_type):
    client = get_groq_client(api_key)
    safe_sub = clean_input(sub)
    safe_chap = clean_input(chap)
    
    context = (
        f"You are a strict Textbook Author and Examiner for the {board} Board. "
        f"Subject: {safe_sub}, Class: {cls}, Chapter: '{safe_chap}'.\n"
        f"CRITICAL RULES:\n"
        f"1. Questions must be factually 100% correct according to standard {board} textbooks.\n"
        f"2. Avoid ambiguous questions. There must be exactly one indisputable correct answer.\n"
        f"3. Use questions from Past Year Papers where possible.\n"
    )

    if q_type == "MCQ":
        prompt = f"""
        {context}
        Create a strictly valid JSON list of {num} {diff}-level Multiple Choice Questions (MCQs).
        
        JSON Format:
        [
            {{
                "id": 1, 
                "question": "Question text?", 
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correct_answer": "Option A"
            }}
        ]
        VERIFICATION STEP: Before outputting, check that 'correct_answer' matches one of the 'options' exactly and is factually true.
        Return ONLY raw JSON.
        """
    else: # Descriptive
        prompt = f"""
        {context}
        Create a strictly valid JSON list of {num} {diff}-level Descriptive Questions.
        Include 'marks' (e.g., 2, 3, 5).
        
        JSON Format:
        [
            {{
                "id": 1, 
                "question": "Question text?", 
                "marks": 3
            }}
        ]
        Return ONLY raw JSON.
        """

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a precise academic assistant. You do not hallucinate facts. You output strictly valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1 
        )
        content = response.choices[0].message.content.strip()
        if "```" in content:
            content = content.replace("```json", "").replace("```", "")
        return json.loads(content)
    except Exception as e:
        st.error(f"Error generating questions: {str(e)}")
        return None

def grade_mcq(api_key, model, questions, user_answers, board, cls, sub):
    client = get_groq_client(api_key)
    score = 0
    incorrect_log = ""
    
    for q in questions:
        q_id = str(q['id'])
        u_ans = user_answers.get(q_id)
        c_ans = q['correct_answer']
        if u_ans == c_ans:
            score += 1
        else:
            incorrect_log += f"Q: {q['question']}\nStudent Answer: {u_ans}\nCorrect Answer: {c_ans}\n\n"
            
    st.session_state.score = score
    st.session_state.total_marks = len(questions)

    if score == len(questions):
        return "### Excellent! Perfect Score. \nYou have mastered this topic based on Board standards."
        
    prompt = f"""
    The student scored {score}/{len(questions)} in a {board} Class {cls} {sub} MCQ test.
    Mistakes:
    {incorrect_log}
    
    Provide a "Scope for Improvement" analysis. 
    Explain clearly WHY the student's answer was wrong and why the correct answer is correct.
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error analyzing performance: {str(e)}"

def grade_descriptive(api_key, model, questions, user_answers, board, cls, sub):
    client = get_groq_client(api_key)
    qa_data = ""
    total_possible_marks = 0
    
    for q in questions:
        q_id = str(q['id'])
        u_ans = user_answers.get(q_id, "No Answer")
        marks = q.get('marks', 1)
        total_possible_marks += marks
        qa_data += f"Q ({marks} marks): {q['question']}\nStudent Answer: {u_ans}\n\n"
    
    st.session_state.total_marks = total_possible_marks

    prompt = f"""
    You are a strict examiner for {board} Class {cls} {sub}.
    Evaluate these descriptive answers based on standard Board marking schemes.
    
    Data:
    {qa_data}
    
    Output Requirements:
    1. Award marks for EACH question.
    2. Calculate Total Score obtained out of {total_possible_marks}.
    3. Provide "Scope for Improvement" pointing out missing keywords or concepts.
    4. Format clearly in Markdown.
    """

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error grading descriptive answers: {str(e)}"

# --- 6. MAIN APP LOGIC ---

# Header
try:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("logo.png", use_container_width=True)
except Exception:
    st.markdown("<h1 style='text-align: center; color: #0d1b2a;'>🧬 The Molecular Man</h1>", unsafe_allow_html=True)

st.markdown("<h3 style='text-align: center; color: #1e3a5f;'>Expert Tuition Solutions - Mock Test</h3>", unsafe_allow_html=True)
st.markdown("---")

# API Connection Check
api_key = None
is_online = False
if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
    if not st.session_state.available_models:
        st.session_state.available_models = fetch_available_models(api_key)
    if st.session_state.available_models:
        is_online = True
else:
    st.error("🔴 Config Missing: Please set GROQ_API_KEY in Secrets.")
    st.stop()

# --- MODEL SELECTION (Hidden in Expander) ---
model_choice = None
if is_online and st.session_state.available_models:
    with st.expander("🛠️ Advanced Settings (AI Model)", expanded=False):
        default_ix = 0
        for i, m in enumerate(st.session_state.available_models):
            if "llama-3.3" in m:
                default_ix = i
                break
        model_choice = st.selectbox("Select Model", st.session_state.available_models, index=default_ix)

# ---------------------------------------------------------
# VIEW 1: CONFIGURATION DASHBOARD (If no questions generated)
# ---------------------------------------------------------
if not st.session_state.questions:
    st.markdown("#### ⚙️ Configure Your Test")
    
    with st.container(border=True):
        col_main1, col_main2 = st.columns(2, gap="medium")
        
        with col_main1:
            st.markdown("**1. Exam Details**")
            board = st.selectbox("Select Board", ["CBSE", "ICSE", "IGCSE", "State Board", "Other"])
            student_class = st.selectbox("Select Class", [str(i) for i in range(6, 13)] + ["Other"])
            difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])

        with col_main2:
            st.markdown("**2. Topic Details**")
            subject = st.text_input("Subject (e.g., Physics)")
            chapter = st.text_input("Chapter Name")
            
            sub_c1, sub_c2 = st.columns(2)
            with sub_c1:
                q_type = st.radio("Type", ["MCQ", "Descriptive"])
            with sub_c2:
                num_questions = st.number_input("Count", min_value=1, max_value=20, value=5)

    st.write("")
    if st.button("🚀 GENERATE MOCK TEST", type="primary", disabled=not is_online):
        if not subject or not chapter:
            st.warning("⚠️ Please enter Subject and Chapter details.")
        else:
            with st.spinner(f"Creating {board} pattern {q_type}s..."):
                st.session_state.user_answers = {}
                st.session_state.feedback = None
                st.session_state.score = 0
                st.session_state.q_type = q_type
                
                questions = generate_questions_groq(
                    api_key, model_choice, board, student_class, subject, chapter, num_questions, difficulty, q_type
                )
                
                if questions:
                    st.session_state.questions = questions
                    st.rerun()

# ---------------------------------------------------------
# VIEW 2: EXAM INTERFACE (If questions exist)
# ---------------------------------------------------------
else:
    # If feedback exists, show results
    if st.session_state.feedback:
        st.header("📊 Result Analysis")
        
        if st.session_state.q_type == "MCQ":
            total = st.session_state.total_marks
            score = st.session_state.score
            st.metric("Score", f"{score}/{total}")
        
        st.success("Analysis Complete")
        with st.container(border=True):
            st.markdown("### Examiner's Feedback")
            st.markdown(st.session_state.feedback)
        
        if st.session_state.q_type == "MCQ":
            with st.expander("View Answer Key"):
                for q in st.session_state.questions:
                    u_ans = st.session_state.user_answers.get(str(q['id']))
                    c_ans = q['correct_answer']
                    color = "green" if u_ans == c_ans else "red"
                    st.markdown(f"**Q{q['id']}:** {q['question']}")
                    st.markdown(f":{color}[Your Answer: {u_ans}]")
                    if u_ans != c_ans:
                        st.markdown(f"**Correct Answer:** {c_ans}")
                    st.markdown("---")

        st.write("")
        if st.button("🔄 START NEW TEST"):
            st.session_state.questions = None
            st.session_state.feedback = None
            st.session_state.user_answers = {}
            st.session_state.score = 0
            st.rerun()

    # If no feedback yet, show questions
    else:
        # Use safe indexing or subject name for title
        title_sub = st.session_state.questions[0].get('question', 'Test')[:0] 
        st.subheader(f"📝 Current Test") 
        
        with st.form("exam_form"):
            for q in st.session_state.questions:
                label = f"**Q{q['id']}. {q['question']}**"
                if st.session_state.q_type == "Descriptive":
                    label += f" *({q.get('marks', 1)} Marks)*"
                
                st.markdown(label)
                
                if st.session_state.q_type == "MCQ":
                    st.radio(
                        "Select Option:",
                        q['options'],
                        key=f"ans_{q['id']}",
                        index=None,
                        label_visibility="collapsed"
                    )
                else:
                    st.text_area(
                        "Write your answer:",
                        key=f"ans_{q['id']}",
                        height=100
                    )
                st.markdown("---")
            
            submit_btn = st.form_submit_button("Submit Exam")

        if submit_btn:
            all_answered = True
            for q in st.session_state.questions:
                key = f"ans_{q['id']}"
                val = st.session_state.get(key)
                if val is None or val == "":
                    all_answered = False
                st.session_state.user_answers[str(q['id'])] = val
            
            if not all_answered and st.session_state.q_type == "MCQ":
                st.error("Please answer all questions before submitting.")
            else:
                with st.spinner("Evaluating your performance..."):
                    if st.session_state.q_type == "MCQ":
                        feedback = grade_mcq(
                            api_key, model_choice,
                            st.session_state.questions, 
                            st.session_state.user_answers,
                            "Board", "Class", "Subject" 
                        )
                    else:
                        feedback = grade_descriptive(
                            api_key, model_choice,
                            st.session_state.questions, 
                            st.session_state.user_answers,
                            "Board", "Class", "Subject"
                        )
                    
                    st.session_state.feedback = feedback
                    st.rerun()
