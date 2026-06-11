import streamlit as st
import google.generativeai as genai
import yaml
import json
import re
from github import Github 

# --- GITHUB INTEGRATION ---
def push_to_github(file_path, content, message, repo_name="science-boa/BOA-Quiz"):
    """Pushes the generated YAML content to the specified GitHub repository."""
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
    st.info("👉 Please ensure your Gemini API Key is set to activate the app.")
    st.stop()

# --- STEP 1: CONTEXT PARAMS ---
col1, col2 = st.columns([1, 3])
with col1:
    quiz_id_input = st.text_input("Quiz ID:", value="101")
with col2:
    video_url = st.text_input("Paste YouTube URL here:")

# --- STEP 2: DYNAMIC INSTRUCTIONS ---
if video_url:
    st.markdown("### Next Step: Get the Transcript")
    gemini_instruction = (
        f"Extract the complete caption/transcript text of this video: {video_url}\n\n"
        "Format: Strip fillers, collapse analogies, keep all facts, new line per sentence, output in plain text block."
    )
    st.code(gemini_instruction, language="text")

st.divider()
transcript_text = st.text_area("2. Paste your video transcript text below", height=300)

# --- AI GENERATION ---
if st.button("Generate Questions from Transcript", type="primary"):
    if not transcript_text:
        st.warning("Please paste a transcript.")
    else:
        status_placeholder = st.empty()
        system_instruction = "You are an expert UK secondary school science teacher and GCSE examiner. Output ONLY valid, raw JSON. Do not include markdown code blocks or conversational filler."
        prompt = f"""
        Analyze this text: {transcript_text[:12000]}.
        Generate a JSON object with:
        1. "title": GCSE Science Assessment title.
        2. "questions": Exactly 15 multiple choice objects (keys: text, A, B, C, D, answer, explanation, points).
        3. "long_answer": 1 object (keys: text, rubric, points).
        """
        
        with st.spinner("Building schema..."):
            try:
                model = genai.GenerativeModel(model_name='gemini-flash-latest')
                response = model.generate_content(prompt)
                
                # CLEANING: Strip markdown and whitespace
                raw_text = response.text
                clean_json = re.sub(r'^```json\s*', '', raw_text, flags=re.IGNORECASE)
                clean_json = re.sub(r'\s*```$', '', clean_json)
                
                compiled_data = json.loads(clean_json)
                
                st.session_state['quiz_title'] = compiled_data.get('title', 'Video Assessment')
                st.session_state['quiz_data'] = compiled_data.get('questions', [])
                st.session_state['long_answer_data'] = compiled_data.get('long_answer', {})
                st.session_state['saved_url'] = video_url
                st.session_state['saved_quiz_id'] = quiz_id_input
                st.rerun() 
            except Exception as e:
                st.error(f"Generation Error: {e}")

# --- EDITABLE REVIEW INTERFACE ---
if 'quiz_data' in st.session_state:
    st.header("Review & Edit Questions")
    edited_title = st.text_input("Quiz Title", value=st.session_state.get('quiz_title', ''))
    
    final_compiled_questions = []
    for i, q in enumerate(st.session_state['quiz_data']):
        with st.expander(f"Q{i+1}: {q.get('text', '')[:50]}...", expanded=False):
            e_text = st.text_input(f"Question {i+1}", value=q.get('text', ''), key=f"q_{i}")
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
    
    # Long Answer Section
    la = st.session_state.get('long_answer_data', {})
    e_la_text = st.text_area("Long Answer Question", value=la.get('text', ''), key="la_t")
    e_la_rubric = st.text_area("Rubric", value=la.get('rubric', ''), key="la_r")
    
    # YAML Export
    st.divider()
    quiz_id = st.session_state['saved_quiz_id']
    yaml_data = {
        "quiz_id": quiz_id,
        "title": edited_title,
        "multiple_choice": final_compiled_questions,
        "long_answer": {"text": e_la_text, "rubric": e_la_rubric, "points": 6}
    }
    yaml_string = yaml.dump(yaml_data, allow_unicode=True, default_flow_style=False)
    
    st.download_button("💾 Download YAML", data=yaml_string, file_name=f"QUIZ_{quiz_id}.yaml")

    if st.button("Push to GitHub 🚀"):
        if push_to_github(f"quizzes/QUIZ_{quiz_id}.yaml", yaml_string, f"Add quiz {quiz_id}"):
            st.success("Successfully pushed to GitHub!")
