import streamlit as st
import google.generativeai as genai
import yaml
import json
from github import Github 

# --- GITHUB INTEGRATION ---
def push_to_github(file_path, content, message, repo_name="science-boa/BOA-Quiz"):
    g = Github(st.secrets["GITHUB_TOKEN"])
    repo = g.get_repo(repo_name)
    try:
        contents = repo.get_contents(file_path)
        repo.update_file(contents.path, message, content, contents.sha)
        return True
    except:
        repo.create_file(file_path, message, content)
        return True

st.set_page_config(page_title="YouTube to Quiz Architect", layout="wide")
st.title("YouTube to Quiz Architect 🛠️")

# --- API KEY HANDLING ---
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_sidebar = st.sidebar.text_input("Enter Gemini API Key:", type="password")
    api_key = api_sidebar if api_sidebar else None

if api_key:
    genai.configure(api_key=api_key)
else:
    st.info("👉 Please ensure your Gemini API Key is set.")
    st.stop()

# --- INPUTS ---
col1, col2 = st.columns([1, 3])
with col1:
    quiz_id_input = st.text_input("Quiz ID:", value="101")
with col2:
    video_url = st.text_input("Paste YouTube URL here:")

transcript_text = st.text_area("2. Paste your video transcript text below", height=300)

# --- AI GENERATION ---
if st.button("Generate Questions", type="primary"):
    if not transcript_text:
        st.warning("Please paste a transcript.")
    else:
        system_instruction = "You are an expert UK science teacher. Generate strict JSON."
        prompt = f"Analyze: {transcript_text[:12000]}. Generate JSON with 'title', 'questions' (list of dicts), 'long_answer' (dict)."
        
        with st.spinner("Building schema..."):
            try:
                model = genai.GenerativeModel(model_name='gemini-flash-lite-latest')
                response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                
                # CRITICAL FIX: Ensure the output is parsed as a dict
                compiled_data = json.loads(response.text)
                
                st.session_state['quiz_title'] = compiled_data.get('title', 'Video Assessment')
                st.session_state['quiz_data'] = compiled_data.get('questions', [])
                st.session_state['long_answer_data'] = compiled_data.get('long_answer', {})
                st.session_state['saved_url'] = video_url
                st.session_state['saved_quiz_id'] = quiz_id_input
                st.rerun() 
            except Exception as e:
                st.error(f"Generation Error: {e}")

# --- EDITABLE REVIEW INTERFACE ---
# Check if quiz_data exists and is actually a list
if 'quiz_data' in st.session_state:
    # If for some reason it's a string, attempt to parse it again
    if isinstance(st.session_state['quiz_data'], str):
        try:
            st.session_state['quiz_data'] = json.loads(st.session_state['quiz_data'])
        except:
            st.error("Data error: Quiz format is invalid.")
            st.stop()

    st.header("Review & Edit Questions")
    
    final_compiled_questions = []
    for i, q in enumerate(st.session_state['quiz_data']):
        # Safety check: make sure q is a dict
        if isinstance(q, dict):
            with st.expander(f"Q{i+1}: {q.get('text', 'No text')[:50]}...", expanded=False):
                e_text = st.text_input("Question", value=q.get('text', ''), key=f"q_{i}")
                e_A = st.text_input("A", value=q.get('A', ''), key=f"A_{i}")
                e_B = st.text_input("B", value=q.get('B', ''), key=f"B_{i}")
                e_C = st.text_input("C", value=q.get('C', ''), key=f"C_{i}")
                e_D = st.text_input("D", value=q.get('D', ''), key=f"D_{i}")
                e_ans = st.text_input("Correct Answer", value=q.get('answer', ''), key=f"ans_{i}")
                e_exp = st.text_area("Explanation", value=q.get('explanation', ''), key=f"exp_{i}")
                
                if st.checkbox(f"Include Q{i+1}", value=True, key=f"keep_{i}"):
                    final_compiled_questions.append({
                        "text": e_text, "A": e_A, "B": e_B, "C": e_C, "D": e_D,
                        "answer": e_ans, "explanation": e_exp, "points": 1
                    })
    
    # ... [Keep your existing Long Answer and GitHub push logic here]
