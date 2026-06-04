import streamlit as st
import google.generativeai as genai
from fpdf import FPDF
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

# --- STEP 1: VIDEO URL INPUT ---
video_url = st.text_input("1. Paste YouTube URL here:", placeholder="https://www.youtube.com/watch?v=...")

# --- STEP 2: DYNAMIC INSTRUCTIONS (Only shows after URL is filled) ---
if video_url:
    st.markdown("### Next Step: Get the Transcript")
    st.markdown("Open a [gemini chat window](https://gemini.google.com) and use the following instruction to generate a transcript:")
    
    # Custom Gemini instruction requested by user
    gemini_instruction = (
        f"Extract the complete caption/transcript text of this video: {video_url}\n\n"
        f"Format Requirements:\n"
        f"1. Put a new line at the end of each sentence.\n"
        f"2. Produce the entire final output inside a plain text code block so that it has a copy button."
    )
    
    # st.code automatically creates a box with a "Copy" button on the top right
    st.code(gemini_instruction, language="text")

st.divider()

# --- STEP 3: TRANSCRIPT INPUT & PROCESSING ---
transcript_text = st.text_area("2. Paste your video transcript text below to generate a formatted quiz", height=300, placeholder="Paste your copied text transcript blocks here...")

# --- PDF COMPILER ---
def generate_pdf(url_str, questions_list):
    # Dynamically calculate a tall canvas height to accommodate the extra paragraph breaks comfortably
    calculated_height = 200 + (len(questions_list) * 110)
    
    # Initialize FPDF with a custom size layout using the calculated height
    pdf = FPDF(orientation='P', unit='mm', format=(210, calculated_height))
    pdf.set_auto_page_break(False)  # Forces everything onto a single continuous page
    pdf.add_page()
    pdf.set_font("Courier", size=11)
    
    def add_line(text):
        # If the line contains text, render it and automatically add a paragraph line break spacing after it
        if text.strip():
            safe_text = text.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 5, txt=safe_text)
            pdf.ln(5)  # This creates the physical paragraph break gap after the line
    
    # URL printed at the top
    add_line(url_str if url_str else "No URL Provided")
    
    explanations = []
    
    for i, q in enumerate(questions_list):
        add_line(f"{i+1}) {q['question']}")
        for option in q['options']:
            add_line(option)
        add_line(f"ANSWER: {q['Answer']}")
        add_line(f"POINT: {q.get('points', 1)}")
        explanations.append(q['explanation'])
        
    add_line("Question: Metadata")
    metadata_string = "**".join(explanations)
    add_line(metadata_string)
    
    return pdf.output(dest='S').encode('latin-1')

# --- BUTTON EVENT ---
if st.button("Generate Questions from Transcript", type="primary"):
    if not transcript_text:
        st.warning("Please paste a transcript block before generating.")
    else:
        with st.spinner("Gemini 3.5 Flash is building your 15 questions..."):
            try:
                model = genai.GenerativeModel('gemini-3.5-flash')
                
                prompt = f"""
                Analyze the following video text content.
                Generate exactly 15 multiple choice questions based on the core educational content.
                
                CONTENT TEXT:
                {transcript_text}
                
                You MUST return the result as a raw, valid JSON object following this exact structure:
                {{
                  "questions": [
                    {{
                      "question": "The question text here?",
                      "options": ["A. First option", "B. Second option", "C. Third option", "D. Fourth option"],
                      "Answer": "A",
                      "explanation": "One clear sentence explaining why the answer is correct.",
                      "points": 1
                    }}
                  ]
                }}
                """
                
                response = model.generate_content(
                    prompt,
                    generation_config=genai.GenerationConfig(
                        response_mime_type="application/json",
                    )
                )
                
                data = json.loads(response.text)
                st.session_state['quiz_data'] = data['questions']
                st.session_state['saved_url'] = video_url
                st.success("🎉 Questions generated successfully! Review them below.")
                
            except Exception as e:
                st.error(f"AI Generation Error: {e}")

# --- EDITABLE LIVE REVIEW INTERFACE ---
if 'quiz_data' in st.session_state:
    st.header("Review, Edit & Select Questions")
    st.write("You can directly click inside any box below to make custom edits before compiling the PDF.")
    
    final_compiled_questions = []
    
    for i, q in enumerate(st.session_state['quiz_data']):
        with st.expander(f"Question {i+1}: {q['question'][:60]}...", expanded=True):
            
            # 1. Editable Question Text Box
            edited_question = st.text_input(f"Question {i+1} Text", value=q['question'], key=f"q_text_{i}")
            
            # 2. Editable Multiple Choice Options
            edited_options = []
            for opt_idx, option in enumerate(q['options']):
                letter = chr(65 + opt_idx)  # A, B, C, D
                edited_opt = st.text_input(f"Option {letter}", value=option, key=f"opt_{i}_{opt_idx}")
                edited_options.append(edited_opt)
            
            # 3. Editable Answer Letter
            edited_answer = st.text_input(f"Correct Answer Letter (A, B, C, or D)", value=q['Answer'], key=f"ans_{i}").upper().strip()
            
            # 4. Editable Explanation Block
            edited_explanation = st.text_area(f"Explanation", value=q['explanation'], key=f"exp_{i}", height=70)
            
            # 5. Optional Point Value Tracker
            default_points = q.get('points', 1)
            edited_points = st.number_input(f"Points Allocation", value=int(default_points), min_value=0, key=f"pts_{i}")
            
            # Checkbox to completely exclude a question if needed
            keep_question = st.checkbox(f"Include Question {i+1} in PDF", value=True, key=f"keep_{i}")
            
            if keep_question:
                final_compiled_questions.append({
                    "question": edited_question,
                    "options": edited_options,
                    "Answer": edited_answer,
                    "explanation": edited_explanation,
                    "points": edited_points
                })

    # --- PDF GENERATION ---
    st.divider()
    
    if len(final_compiled_questions) > 0:
        pdf_bytes = generate_pdf(st.session_state['saved_url'], final_compiled_questions)
        st.download_button(
            label=f"💾 Download PDF ({len(final_compiled_questions)} Questions)",
            data=pdf_bytes,
            file_name="youtube_quiz.pdf",
            mime="application/pdf",
            type="primary"
        )
    else:
        st.warning("You must select at least one question to generate a PDF.")
