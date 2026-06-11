import streamlit as st
import google.generativeai as genai
import yaml
import json
import re # Added for text cleaning
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

# ... [Setup and UI Input remains same] ...

# --- AI GENERATION ---
if st.button("Generate Questions", type="primary"):
    if not transcript_text:
        st.warning("Please paste a transcript.")
    else:
        system_instruction = "You are an expert UK science teacher. Output ONLY raw JSON."
        prompt = f"Analyze: {transcript_text[:12000]}. Generate JSON with 'title', 'questions' (list of dicts), 'long_answer' (dict)."
        
        with st.spinner("Building schema..."):
            try:
                model = genai.GenerativeModel(model_name='gemini-flash-latest')
                response = model.generate_content(prompt)
                
                # --- CLEANING THE RESPONSE ---
                raw_text = response.text
                # Remove markdown code block markers if present
                clean_json = re.sub(r'^```json\s*', '', raw_text, flags=re.IGNORECASE)
                clean_json = re.sub(r'\s*```$', '', clean_json)
                
                # Parse the cleaned JSON
                compiled_data = json.loads(clean_json)
                
                st.session_state['quiz_title'] = compiled_data.get('title', 'Video Assessment')
                st.session_state['quiz_data'] = compiled_data.get('questions', [])
                st.session_state['long_answer_data'] = compiled_data.get('long_answer', {})
                st.session_state['saved_url'] = video_url
                st.session_state['saved_quiz_id'] = quiz_id_input
                st.rerun() 
            except Exception as e:
                st.error(f"Generation Error: {e}")
                st.text(f"Raw Output start: {response.text[:100]}") # Help debug if it still fails
