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
        
        # NOTE: Removed forcing application/json to see if the model provides more context on failure
        generation_config = genai.GenerationConfig(temperature=0.1)
        
        with st.spinner("Building schema..."):
            try:
                # Updated to gemini-flash-latest
                model = genai.GenerativeModel(model_name='gemini-flash-latest', system_instruction=system_instruction)
                response = model.generate_content(prompt, generation_config=generation_config)
                
                # --- DEBUGGING BLOCK ---
                st.write("--- DEBUG: API RESPONSE ---")
                st.text(f"Finish Reason: {response.candidates[0].finish_reason}")
                st.text(f"Raw Text snippet: {response.text[:200] if response.text else 'EMPTY'}")
                
                # Attempt to parse
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
if 'quiz_data' in st.session_state:
    st.header("Review & Edit Questions")
    
    final_compiled_questions = []
    # Safety: Ensure it's a list
    data = st.session_state['quiz_data']
    if isinstance(data, str): data = json.loads(data)
    
    for i, q in enumerate(data):
        if isinstance(q, dict):
            with st.expander(f"Q{i+1}: {q.get('text', 'No text')[:50]}...", expanded=False):
                e_text = st.text_input("Question", value=q.get('text', ''), key=f"q_{i}")
                e_A = st.text_input("A", value=q.get('A', ''), key=f"A_{i}")
                e_B = st.text_input("B", value=q.get('B', ''), key=f"B_{i}")
