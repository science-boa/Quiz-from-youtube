import streamlit as st
import google.generativeai as genai
import yaml
import json
from github import Github 

def push_to_github(file_path, content, message, repo_name="science-boa/BOA-Quiz"):
    """Pushes content to a GitHub repository."""
    # Ensure GITHUB_TOKEN is in your st.secrets
    g = Github(st.secrets["GITHUB_TOKEN"])
    repo = g.get_repo(repo_name)
    try:
        # Check if file exists to update it or create it
        contents = repo.get_contents(file_path)
        repo.update_file(contents.path, message, content, contents.sha)
        return True
    except:
        # Create new file if it doesn't exist
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

# --- STEP 1: CONTEXT PARAMS (QUIZ ID & VIDEO URL) ---
col1, col2 = st.columns([1, 3])
with col1:
    quiz_id_input = st.text_input("Quiz ID:", value="101", placeholder="e.g., 101")
with col2:
    video_url = st.text_input("Paste YouTube URL here:", placeholder="https://www.youtube.com/watch?v=...")

# --- STEP 2: DYNAMIC INSTRUCTIONS ---
if video_url:
    st.markdown("### Next Step: Get the Transcript")
    st.markdown("Open a [gemini chat window](https://gemini.google.com) and use the following instruction to generate a transcript:")
    
    gemini_instruction = (
        f"Extract the complete caption/transcript text of this video: {video_url}\n\n"
        f"Format Requirements:\n"
        f"1. Strip out all casual conversational filler, greetings, sponsor segments, and channel plugs.\n"
        f"2. Collapse long analogies into direct, concise technical explanations.\n"
        f"3. Do not omit any specific facts, data, rules, definitions, or examples mentioned.\n"
        f"4. Put a new line at the end of each sentence.\n"
        f"5. Produce the entire final output inside a plain text code block so that it has a copy button."
    )
    st.code(gemini_instruction, language="text")

st.divider()

# --- STEP 3: TRANSCRIPT INPUT & PROCESSING ---
transcript_text = st.text_area("2. Paste your video transcript text below", height=300, placeholder="Paste your copied transcript here...")

# --- AI GENERATION WITH FALLBACK LOGIC ---
if st.button("Generate Questions from Transcript", type="primary"):
    if not transcript_text:
        st.warning("Please paste a transcript block before generating.")
    else:
        status_placeholder = st.empty()
        
        # METHOD 2 INTEGRATED: Shifted the AI's persona to an expert UK Secondary School Science Teacher / GCSE Examiner
        system_instruction = (
            "You are an expert UK secondary school science teacher and GCSE examiner. "
            "Your task is to generate strict JSON educational assessments calibrated specifically "
            "to the UK GCSE standard (suited for 14-15 year olds). Every explanation and rubric you write "
            "must be pedagogically sound and aligned with GCSE curriculum expectations. Never use lazy phrases "
            "like 'according to the text', 'the video states', or 'as mentioned'. Do not include "
            "conversational filler outside the JSON."
        )
        safe_transcript = transcript_text[:12000]
        
        # METHOD 1 INTEGRATED: Injected GCSE qualitative constraints and level-of-response rubric formatting
        prompt = f"""
        Analyze this text: {safe_transcript}

        Generate a JSON object with:
        1. "title": A descriptive title suited for a GCSE Science Assessment.
        2. "questions": Exactly 15 multiple choice objects appropriate for GCSE students. Each must have:
           "text", "A", "B", "C", "D", 
           "answer" (the exact full text string of the correct choice, matching either option A, B, C, or D perfectly), 
           "explanation" (a clear, curriculum-aligned scientific explanation of why the answer is factually correct, focusing on core concepts taught at the 14-15 year old level), 
           "points" (default 1).
        3. "long_answer": Exactly 1 object representing a classic GCSE 6-mark extended-response question. It must have:
           "text" (A 6-mark question appropriate for a 14-15 year old GCSE student, focusing on key physical, chemical, or biological processes found in the transcript. Use prompt command terms like 'Explain', 'Describe', 'Evaluate', or 'Compare'),
           "rubric" (A level-of-response grading rubric mimicking standard GCSE mark schemes. Structure it clearly into:
               - Level 1 (1-2 marks): Simple statements or disjointed points.
               - Level 2 (3-4 marks): Clear descriptions with some logical scientific linkages.
               - Level 3 (5-6 marks): Detailed, structured, and logical scientific explanations with complete sequential steps.
               - Indicative Content: A list of key factual bullet points the student should ideally include.),
           "points" (default 6).

        Strict JSON structure:
        {{
          "title": "...",
          "questions": [{{ "text": "...", "A": "...", "B": "...", "C": "...", "D": "...", "answer": "exact text of the correct option", "explanation": "clear GCSE-level explanation", "points": 1 }}],
          "long_answer": {{ "text": "...", "rubric": "...", "points": 6 }}
        }}
        """
        
        generation_config = genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.1
        )
        
        compiled_data = None
        model_used = ""

        # --- RUNTIME ARCHITECTURE EXECUTION LOOP ---
        with st.spinner("Quiz Architect is building your schema structure..."):
            # Attempt 1: Gemini 3.5 Flash
            try:
                status_placeholder.info("🚀 Attempting compilation using **Gemini 3.5 Flash**...")
                model_35 = genai.GenerativeModel(model_name='gemini-3.5-flash', system_instruction=system_instruction)
                response = model_35.generate_content(prompt, generation_config=generation_config)
                compiled_data = json.loads(response.text)
                model_used = "Gemini 3.5 Flash"
            
            except Exception as error_35:
                status_placeholder.warning(f"⚠️ Gemini 3.5 Flash encountered an error: {error_35}. Switching to fallback engine...")
                
                # Attempt 2: Fallback to Gemini 2.5 Flash
                try:
                    st.info("🔄 Re-routing payload to backup cluster via **Gemini 2.5 Flash**...")
                    model_25 = genai.GenerativeModel(model_name='gemini-2.5-flash', system_instruction=system_instruction)
                    response = model_25.generate_content(prompt, generation_config=generation_config)
                    compiled_data = json.loads(response.text)
                    model_used = "Gemini 2.5 Flash"
                except Exception as error_25:
                    status_placeholder.error(f"❌ Comprehensive failure: Both 3.5 and Fallback 2.5 chains returned errors. Message: {error_25}")

        # Post-Processing if either pipeline succeeded
        if compiled_data:
            st.session_state['quiz_title'] = compiled_data.get('title', 'Video Assessment')
            st.session_state['quiz_data'] = compiled_data['questions']
            st.session_state['long_answer_data'] = compiled_data.get('long_answer')
            st.session_state['saved_url'] = video_url
            st.session_state['saved_quiz_id'] = quiz_id_input
            status_placeholder.success(f"🎉 Assessment compiled successfully using **{model_used}**!")

# --- EDITABLE REVIEW INTERFACE ---
if 'quiz_data' in st.session_state:
    st.header("Review & Edit Questions")
    edited_title = st.text_input("Quiz Title", value=st.session_state.get('quiz_title', ''))
    
    st.subheader("Multiple Choice Questions")
    final_compiled_questions = []
    
    for i, q in enumerate(st.session_state['quiz_data']):
        with st.expander(f"Q{i+1}: {q.get('text', '')[:50]}...", expanded=False):
            e_text = st.text_input(f"Question {i+1}", value=q.get('text', ''), key=f"q_{i}")
            e_A = st.text_input(f"A", value=q.get('A', ''), key=f"A_{i}")
            e_B = st.text_input(f"B", value=q.get('B', ''), key=f"B_{i}")
            e_C = st.text_input(f"C", value=q.get('C', ''), key=f"C_{i}")
            e_D = st.text_input(f"D", value=q.get('D', ''), key=f"D_{i}")
            
            e_ans = st.text_input(f"Correct Answer Text", value=q.get('answer', ''), key=f"ans_{i}")
            e_exp = st.text_area(f"Explanation", value=q.get('explanation', ''), key=f"exp_{i}")
            e_pts = st.number_input(f"Points", value=int(q.get('points', 1)), key=f"pts_{i}")
            
            if st.checkbox(f"Include Q{i+1}", value=True, key=f"keep_{i}"):
                final_compiled_questions.append({
                    "question_num": len(final_compiled_questions) + 1,
                    "text": e_text, "A": e_A, "B": e_B, "C": e_C, "D": e_D,
                    "answer": e_ans, "points": e_pts, "explanation": e_exp
                })

    st.subheader("Long Answer Question")
    la = st.session_state.get('long_answer_data', {})
    with st.expander("Edit Long Answer Task", expanded=True):
        e_la_text = st.text_area("Question Text", value=la.get('text', ''), key="la_t")
        e_la_rubric = st.text_area("Rubric", value=la.get('rubric', ''), key="la_r")
        e_la_pts = st.number_input("Points", value=int(la.get('points', 6)), key="la_p")
    
    final_la = {"question_num": 1, "text": e_la_text, "points": e_la_pts, "rubric": e_la_rubric}

    # --- YAML EXPORT ---
    st.divider()
    quiz_id = st.session_state['saved_quiz_id']
    
    yaml_data = {
        "quiz_id": int(quiz_id) if quiz_id.isdigit() else quiz_id,
        "video_url": st.session_state['saved_url'],
        "title": edited_title,
        "multiple_choice": final_compiled_questions,
        "long_answer": final_la
    }
    
    yaml_string = yaml.dump(yaml_data, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    st.download_button(
        label=f"💾 Download QUIZ_{quiz_id}.yaml",
        data=yaml_string,
        file_name=f"QUIZ_{quiz_id}.yaml",
        mime="text/yaml",
        type="primary"
    )
if st.button("Push to GitHub 🚀"):
    file_name = f"quizzes/QUIZ_{quiz_id}.yaml"
    if push_to_github(file_name, yaml_string, f"Add quiz {quiz_id}"):
        st.success(f"Successfully pushed to GitHub as {file_name}!")
