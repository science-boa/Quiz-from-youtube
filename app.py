import streamlit as st
import google.generativeai as genai
from docx import Document
from io import BytesIO
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

# --- DOCX COMPILER ---
def generate_docx(url_str, questions_list):
    doc = Document()
    
    # Add URL as its own paragraph at the top
    doc.add_paragraph(url_str if url_str else "No URL Provided")
    doc.add_paragraph("") # Structural paragraph gap

    explanations = []
    
    for i, q in enumerate(questions_list):
        # Every .add_paragraph() generates a genuine hard return/paragraph break
        doc.add_paragraph(f"{i+1}) {q['question']}")
        
        for option in q['options']:
            doc.add_paragraph(option)
        
        doc.add_paragraph(f"ANSWER: {q['Answer']}")
        doc.add_paragraph(f"POINT: {q.get('points', 1)}")
        doc.add_paragraph("") # Structural paragraph gap between questions
        
        explanations.append(q['explanation'])
        
    doc.add_paragraph("Question: Metadata")
    metadata_string = "**".join(explanations)
    doc.add_paragraph(metadata_string)
    
    # Save to an in-memory buffer for Streamlit downloading
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- BUTTON EVENT ---
if st.button("Generate Questions from Transcript", type="primary"):
    if not transcript_text:
        st.warning("Please paste a transcript block before generating.")
    else:
        with st.spinner("Gemini 3.5 Flash is building your 15 questions..."):
            try:
                # Restored directly to Gemini 3.5 Flash
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
                st.session_state
