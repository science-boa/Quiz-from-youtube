import streamlit as st
import google.generativeai as genai
from fpdf import FPDF
import json

st.set_page_config(page_title="YouTube to Quiz Architect", layout="wide")
st.title("YouTube to Quiz Architect 🛠️")
st.write("Paste your video transcript text below to generate a perfectly formatted quiz without extraction errors.")

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

# --- INPUT FIELDS ---
video_url = st.text_input("1. Reference YouTube URL (Will print at the top of the PDF):", placeholder="https://www.youtube.com/watch?v=...")
transcript_text = st.text_area("2. Paste the Video Transcript / Content here:", height=300, placeholder="Paste your copied text transcript blocks here...")

# --- PDF COMPILER ---
def generate_pdf(url_str, questions_list):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Courier", size=11)
    
    def add_line(text):
        safe_text = text.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 5, txt=safe_text)
    
    # URL printed at the top
    add_line(url_str if url_str else "No URL Provided")
    add_line("")
    
    explanations = []
    
    for i, q in enumerate(questions_list):
        add_line(f"{i+1}) {q['question']}")
        for option in q['options']:
            add_line(option)
        add_line("")
        add_line(f"Answer : {q['correct_answer_letter']}")
        add_line("")
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
                      "correct_answer_letter": "A",
                      "explanation": "One clear sentence explaining why the answer is correct."
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

# --- LIVE REVIEW INTERFACE ---
if 'quiz_data' in st.session_state:
    st.header("Review & Select Questions")
    
    selected_indices = []
    
    for i, q in enumerate(st.session_state['quiz_data']):
        with st.expander(f"Question {i+1}: {q['question'][:60]}...", expanded=True):
            st.write(f"**Question:** {q['question']}")
            for opt in q['options']:
                st.write(opt)
            st.write(f"**Correct Answer:** {q['correct_answer_letter']}")
            st.write(f"**Explanation:** {q['explanation']}")
            
            keep_question = st.checkbox(f"Include Question {i+1} in PDF", value=True, key=f"keep_{i}")
            if keep_question:
                selected_indices.append(i)

    # --- PDF GENERATION ---
    st.divider()
    selected_questions = [st.session_state['quiz_data'][i] for i in selected_indices]
    
    if len(selected_questions) > 0:
        pdf_bytes = generate_pdf(st.session_state['saved_url'], selected_questions)
        st.download_button(
            label=f"💾 Download PDF ({len(selected_questions)} Questions)",
            data=pdf_bytes,
            file_name="youtube_quiz.pdf",
            mime="application/pdf",
            type="primary"
        )
    else:
        st.warning("You must select at least one question to generate a PDF.")
