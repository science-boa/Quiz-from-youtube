import streamlit as st
import google.generativeai as genai
import yaml
import json
from github import Github 

# --- GITHUB INTEGRATION FUNCTION ---
def push_to_github(file_path, content, message, repo_name="science-boa/BOA-Quiz"):
    """Pushes content to a GitHub repository."""
    g = Github(st.secrets["GITHUB_TOKEN"])
    repo = g.get_repo(repo_name)
    try:
        contents = repo.get_contents(file_path)
        repo.update_file(contents.path, message, content, contents.sha)
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

# --- INPUTS ---
col1, col2 = st.columns([1, 3])
with col1:
    quiz_id_input = st.text_input("Quiz ID:", value="101")
with col2:
    video_url = st.text_input("Paste YouTube URL here:")

transcript_text = st.text_area("2. Paste your video transcript text below", height=200)

# --- GENERATION LOGIC ---
if st.button("Generate Questions from Transcript", type="primary"):
    if not transcript_text:
        st.warning("Please paste a transcript.")
    else:
        status = st.empty()
        
        system_instruction = "You are an expert UK secondary school science teacher and GCSE examiner. Generate strict JSON."
        prompt = f"Analyze this text: {transcript_text[:12000]}. Generate a JSON object with 'title', 'questions' (15 items), and 'long_answer'."
        
        generation_config = genai.GenerationConfig(response_mime_type="application/json", temperature=0.1)
        
        compiled_data = None
        
        # Execution Loop
        status.info("📤 Sending transcript to Gemini...")
        try:
            model = genai.GenerativeModel(model_name='gemini-3.5-flash', system_instruction=system_instruction)
            status.info("⏳ Waiting for Gemini response...")
            response = model.generate_content(prompt, generation_config=generation_config)
            compiled_data = json.loads(response.text)
            status.success("✅ AI generation complete.")
            
            st.session_state['quiz_data'] = compiled_data['questions']
            st.session_state['long_answer_data'] = compiled_data.get('long_answer')
            st.session_state['quiz_title'] = compiled_data.get('title')
            st.session_state['saved_url'] = video_url
            st.session_state['saved_quiz_id'] = quiz_id_input
        except Exception as e:
            status.error(f"Error during AI generation: {e}")

# --- REVIEW & PUSH INTERFACE ---
if 'quiz_data' in st.session_state:
    st.header("Review & Edit")
    # (Edit logic remains the same)
    edited_title = st.text_input("Quiz Title", value=st.session_state.get('quiz_title', ''))
    
    # ... [Rest of your review code: Loop for questions, long answer editor, etc.] ...

    st.divider()
    quiz_id = st.session_state.get('saved_quiz_id', '101')
    yaml_data = {
        "quiz_id": quiz_id,
        "title": edited_title,
        "multiple_choice": st.session_state['quiz_data'],
        "long_answer": st.session_state['long_answer_data']
    }
    yaml_string = yaml.dump(yaml_data)
    
    if st.button("Push to GitHub 🚀"):
        github_status = st.empty()
        github_status.info(f"📤 Pushing QUIZ_{quiz_id}.yaml to GitHub (science-boa/BOA-Quiz)...")
        try:
            push_to_github(f"quizzes/QUIZ_{quiz_id}.yaml", yaml_string, f"Add quiz {quiz_id}")
            github_status.success("✅ Successfully pushed to GitHub!")
        except Exception as e:
            github_status.error(f"❌ Failed to push to GitHub: {e}")
