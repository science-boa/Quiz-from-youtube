import streamlit as st
import google.generativeai as genai
import yaml
import json
from github import Github 

# --- GITHUB INTEGRATION ---
def push_to_github(file_path, content, message, repo_name="science-boa/BOA-Quiz"):
    """Pushes content to a GitHub repository."""
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

transcript_text = st.text_area("2. Paste your video transcript text below", height=300)

# --- AI GENERATION ---
if st.button("Generate Questions from Transcript", type="primary"):
    if not transcript_text:
        st.warning("Please paste a transcript block.")
    else:
        status_placeholder = st.empty()
        system_instruction = "You are an expert UK science teacher. Generate strict JSON."
        safe_transcript = transcript_text[:12000]
        prompt = f"Analyze: {safe_transcript}. Generate JSON with 'title', 'questions' (15 items), 'long_answer'."
        
        generation_config = genai.GenerationConfig(response_mime_type="application/json", temperature=0.1)
        
        with st.spinner("Quiz Architect is building your schema..."):
            try:
                status_placeholder.info("🚀 Sending to Gemini (flash-lite)...")
                # Updated model name as requested
                model = genai.GenerativeModel(model_name='gemini-flash-lite-latest', system_instruction=system_instruction)
                status_placeholder.info("⏳ Waiting for Gemini response...")
                response = model.generate_content(prompt, generation_config=generation_config)
                compiled_data = json.loads(response.text)
                
                st.session_state['quiz_title'] = compiled_data.get('title', 'Video Assessment')
                st.session_state['quiz_data'] = compiled_data['questions']
                st.session_state['long_answer_data'] = compiled_data.get('long_answer')
                st.session_state['saved_url'] = video_url
                st.session_state['saved_quiz_id'] = quiz_id_input
                status_placeholder.success("🎉 Assessment compiled successfully!")
            except Exception as e:
                status_placeholder.error(f"❌ Error: {e}")

# --- EDITABLE REVIEW INTERFACE ---
if 'quiz_data' in st.session_state:
    st.header("Review & Edit Questions")
    edited_title = st.text_input("Quiz Title", value=st.session_state.get('quiz_title', ''))
    
    st.subheader("Multiple Choice Questions")
    final_compiled_questions = []
    
    for i, q in enumerate(st.session_state['quiz_data']):
        with st.expander(f"Q{i+1}: {q.get('text', '')[:50]}...", expanded=False):
            e_text = st.text_input("Question", value=q.get('text', ''), key=f"q_{i}")
            e_A = st.text_input("A", value=q.get('A', ''), key=f"A_{i}")
            e_B = st.text_input("B", value=q.get('B', ''), key=f"B_{i}")
            e_C = st.text_input("C", value=q.get('C', ''), key=f"C_{i}")
            e_D = st.text_input("D", value=q.get('D', ''), key=f"D_{i}")
            e_ans = st.text_input("Correct Answer", value=q.get('answer', ''), key=f"ans_{i}")
            e_exp = st.text_area("Explanation", value=q.get('explanation', ''), key=f"exp_{i}")
            
            if st.checkbox(f"Include Q{i+1}", value=True, key=f"keep_{i}"):
                final_compiled_questions.append({
                    "question_num": len(final_compiled_questions) + 1,
                    "text": e_text, "A": e_A, "B": e_B, "C": e_C, "D": e_D,
                    "answer": e_ans, "explanation": e_exp, "points": 1
                })

    st.subheader("Long Answer Question")
    la = st.session_state.get('long_answer_data', {})
    with st.expander("Edit Long Answer Task", expanded=True):
        e_la_text = st.text_area("Question Text", value=la.get('text', ''), key="la_t")
        e_la_rubric = st.text_area("Rubric", value=la.get('rubric', ''), key="la_r")
        e_la_pts = st.number_input("Points", value=int(la.get('points', 6)), key="la_p")
    
    final_la = {"question_num": 1, "text": e_la_text, "points": e_la_pts, "rubric": e_la_rubric}

    # --- EXPORT & PUSH ---
    st.divider()
    quiz_id = st.session_state['saved_quiz_id']
    yaml_data = {
        "quiz_id": int(quiz_id) if str(quiz_id).isdigit() else quiz_id,
        "title": edited_title,
        "multiple_choice": final_compiled_questions,
        "long_answer": final_la
    }
    
    yaml_string = yaml.dump(yaml_data, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    st.download_button("💾 Download YAML", data=yaml_string, file_name=f"QUIZ_{quiz_id}.yaml", mime="text/yaml")

    if st.button("Push to GitHub 🚀"):
        with st.spinner("⏳ Waiting for GitHub..."):
            file_name = f"quizzes/QUIZ_{quiz_id}.yaml"
            if push_to_github(file_name, yaml_string, f"Add quiz {quiz_id}"):
                st.success(f"Successfully pushed to GitHub as {file_name}!")
