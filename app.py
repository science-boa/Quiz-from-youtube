import streamlit as st
import google.generativeai as genai
import yaml
import json

st.set_page_config(page_title="YouTube to Quiz Architect", layout="wide")
st.title("YouTube to Quiz Architect 🛠️")

# --- API KEY HANDLING ---
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("Enter Gemini API Key:", type="password")

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
        f"1. Put a new line at the end of each sentence.\n"
        f"2. Produce the entire final output inside a plain text code block so that it has a copy button."
    )
    st.code(gemini_instruction, language="text")

st.divider()

# --- STEP 3: TRANSCRIPT INPUT & PROCESSING ---
transcript_text = st.text_area("2. Paste your video transcript text below to generate a formatted quiz", height=300, placeholder="Paste your copied text transcript blocks here...")

# --- AI GENERATION BUTTON LOGIC ---
if st.button("Generate Questions from Transcript", type="primary"):
    if not transcript_text:
        st.warning("Please paste a transcript block before generating.")
    else:
        with st.spinner("Gemini 3.5 Flash is compiling your comprehensive quiz configuration..."):
            try:
                model = genai.GenerativeModel('gemini-3.5-flash')
                
                prompt = f"""
                Analyze the following video text content.
                Generate a dynamic descriptive quiz title, exactly 15 multiple choice questions based on the core content, and exactly 1 open-ended conceptual long-answer question text with an evaluation rubric.
                
                CONTENT TEXT:
                {transcript_text}
                
                You MUST return the result as a raw, valid JSON object following this exact structure:
                {{
                  "title": "Descriptive Topic Title Here",
                  "questions": [
                    {{
                      "text": "The question text here?",
                      "A": "First option text",
                      "B": "Second option text",
                      "C": "Third option text",
                      "D": "Fourth option text",
                      "answer": "A",
                      "explanation": "One clear sentence explaining why the answer is correct.",
                      "points": 5
                    }}
                  ],
                  "long_answer": {{
                    "text": "The comprehensive open-ended question text here?",
                    "rubric": "Describe what parameters are explicitly required to earn full marks based on content boundaries.",
                    "points": 6
                  }}
                }}
                """
                
                response = model.generate_content(
                    prompt,
                    generation_config=genai.GenerationConfig(
                        response_mime_type="application/json",
                    )
                )
                
                data = json.loads(response.text)
                st.session_state['quiz_title'] = data.get('title', 'Video Assessment Quiz')
                st.session_state['quiz_data'] = data['questions']
                st.session_state['long_answer_data'] = data.get('long_answer', {
                    "text": "Describe the main takeaway and execution principles covered in the video.",
                    "rubric": "Full marks require addressing core functionality and architectural scope explicitly.",
                    "points": 6
                })
                st.session_state['saved_url'] = video_url
                st.session_state['saved_quiz_id'] = quiz_id_input
                st.success("🎉 Assessment schema compiled successfully! Review parameters below.")
                
            except Exception as e:
                st.error(f"AI Generation Error: {e}")

# --- EDITABLE LIVE REVIEW & STAGING INTERFACE ---
if 'quiz_data' in st.session_state:
    st.header("Review, Edit & Select Questions")
    st.write("Modify any field below to tweak parameters prior to generating the final configuration file.")
    
    st.subheader("Global Metadata Properties")
    edited_title = st.text_input("Quiz Title", value=st.session_state.get('quiz_title', ''))
    
    st.subheader("Multiple Choice Items Block")
    final_compiled_questions = []
    
    for i, q in enumerate(st.session_state['quiz_data']):
        with st.expander(f"Question {i+1}: {q.get('text', '')[:60]}...", expanded=False):
            
            # 1. Question Prompt
            edited_text = st.text_input(f"Question {i+1} Text", value=q.get('text', ''), key=f"q_text_{i}")
            
            # 2. Options Ingestion
            edited_A = st.text_input(f"Option A", value=q.get('A', ''), key=f"opt_A_{i}")
            edited_B = st.text_input(f"Option B", value=q.get('B', ''), key=f"opt_B_{i}")
            edited_C = st.text_input(f"Option C", value=q.get('C', ''), key=f"opt_C_{i}")
            edited_D = st.text_input(f"Option D", value=q.get('D', ''), key=f"opt_D_{i}")
            
            # 3. Correct Answer Variable Block
            edited_answer = st.text_input(f"Correct Answer Letter (A, B, C, or D)", value=q.get('answer', 'A'), key=f"ans_{i}").upper().strip()
            
            # 4. Inline Explanation Tracking
            edited_explanation = st.text_area(f"Explanation Feedback", value=q.get('explanation', ''), key=f"exp_{i}", height=60)
            
            # 5. Question Point Metric
            edited_points = st.number_input(f"Points Allocation", value=int(q.get('points', 5)), min_value=0, key=f"pts_{i}")
            
            keep_question = st.checkbox(f"Include Question {i+1} in YAML Configuration", value=True, key=f"keep_{i}")
            
            if keep_question:
                final_compiled_questions.append({
                    "question_num": len(final_compiled_questions) + 1,
                    "text": edited_text,
                    "A": edited_A,
                    "B": edited_B,
                    "C": edited_C,
                    "D": edited_D,
                    "answer": edited_answer,
                    "points": edited_points,
                    "explanation": edited_explanation
                })

    # --- LONG ANSWER COMPONENT REVIEW ---
    st.subheader("Long Answer Free Text Assignment")
    la_payload = st.session_state.get('long_answer_data', {"text": "", "rubric": "", "points": 6})
    
    with st.expander("Edit Long Answer Configuration Block", expanded=True):
        edited_la_text = st.text_area("Long Answer Core Prompt", value=la_payload.get("text", ""), key="la_text_input")
        edited_la_rubric = st.text_area("Evaluation Criteria Rubric", value=la_payload.get("rubric", ""), key="la_rubric_input", height=100)
        edited_la_points = st.number_input("Maximum Mark Value", value=int(la_payload.get("points", 6)), min_value=0, key="la_points_input")
        
    final_la_compiled = {
        "question_num": 1,
        "text": edited_la_text,
        "points": edited_la_points,
        "rubric": edited_la_rubric
    }

    # --- YAML EXPORT AND EMISSION COMPILER ---
    st.divider()
    
    # Try converting input safely into an integer key to stay clean with schema rules
    try:
        clean_quiz_id = int(st.session_state['saved_quiz_id'])
    except ValueError:
        clean_quiz_id = st.session_state['saved_quiz_id']

    # Build sequential dictionary structure matching the project specifications
    yaml_structure = {
        "quiz_id": clean_quiz_id,
        "video_url": st.session_state['saved_url'],
        "title": edited_title,
        "multiple_choice": final_compiled_questions,
        "long_answer": final_la_compiled
    }
    
    # Convert standard Python mapping natively to human-editable format block
    yaml_string = yaml.dump(yaml_structure, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    st.download_button(
        label=f"💾 Download QUIZ_{st.session_state['saved_quiz_id']}.yaml File",
        data=yaml_string,
        file_name=f"QUIZ_{st.session_state['saved_quiz_id']}.yaml",
        mime="text/yaml",
        type="primary"
    )
