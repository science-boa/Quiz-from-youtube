import streamlit as st
import google.generativeai as genai
from fpdf import FPDF
import json

# --- CONFIGURATION & SETUP ---
# Ensure your Streamlit Cloud Secrets has: GEMINI_API_KEY = "your_actual_key"
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("API Key missing! Please set GEMINI_API_KEY in your Streamlit Cloud Secrets.")
    st.stop()

st.title("YouTube to Quiz Architect")
st.write("Generate, review, and export custom video quizzes.")

# --- FUNCTIONS ---
def generate_pdf(video_url, questions_list):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Courier", size=11)
    
    # Helper to write lines and auto-wrap long text
    def add_line(text):
        # Encode to latin-1 to avoid fpdf character crashes
        safe_text = text.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 5, txt=safe_text)
    
    # 1. Output the URL at the top
    add_line(video_url)
    add_line("") # Blank line
    
    explanations = []
    
    # 2. Output the selected questions
    for i, q in enumerate(questions_list):
        add_line(f"{i+1}) {q['question']}")
        
        for option in q['options']:
            add_line(option)
            
        add_line("")
        add_line(f"Answer : {q['correct_answer_letter']}")
        add_line("")
        
        # Store the explanation for the metadata block
        explanations.append(q['explanation'])
        
    # 3. Output the final metadata block
    add_line("Question: Metadata")
    metadata_string = "**".join(explanations)
    add_line(metadata_string)
    
    return pdf.output(dest='S').encode('latin-1')

# --- MAIN APP LOGIC ---
url = st.text_input("Paste YouTube URL here:")

if st.button("Generate Questions"):
    if not url:
        st.warning("Please enter a URL first.")
    else:
        with st.spinner("Gemini 3.5 Flash is analyzing the video..."):
            try:
                model = genai.GenerativeModel('gemini-3.5-flash')
                
                # By forcing JSON output, we guarantee the app can read the data to build the checkboxes
                prompt = f"""
                Analyze the content of this YouTube video: {url}
                Generate exactly 15 multiple choice questions based on the core educational content.
                
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
                
                # Force structured JSON response
                response = model.generate_content(
                    prompt,
                    generation_config=genai.GenerationConfig(
                        response_mime_type="application/json",
                    )
                )
                
                # Parse the JSON and save to session state so it doesn't disappear when a checkbox is clicked
                data = json.loads(response.text)
                st.session_state['quiz_data'] = data['questions']
                st.session_state['url'] = url
                st.success("Questions generated successfully! Review them below.")
                
            except Exception as e:
                st.error(f"An error occurred: {e}. Please try again.")

# --- LIVE REVIEW EDITOR ---
if 'quiz_data' in st.session_state:
    st.header("Review & Select Questions")
    st.write("Uncheck the box next to any question you want to remove from the final PDF.")
    
    selected_indices = []
    
    # Loop through the JSON data to build the UI
    for i, q in enumerate(st.session_state['quiz_data']):
        # Put each question in an expandable box to keep the UI clean
        with st.expander(f"Question {i+1}: {q['question'][:50]}...", expanded=True):
            st.write(f"**Question:** {q['question']}")
            for opt in q['options']:
                st.write(opt)
            st.write(f"**Correct Answer:** {q['correct_answer_letter']}")
            st.write(f"**Explanation:** {q['explanation']}")
            
            # The toggle switch
            keep_question = st.checkbox(f"Include Question {i+1} in PDF", value=True, key=f"keep_{i}")
            if keep_question:
                selected_indices.append(i)

    # --- PDF GENERATION ---
    st.divider()
    selected_questions = [st.session_state['quiz_data'][i] for i in selected_indices]
    
    if len(selected_questions) > 0:
        pdf_bytes = generate_pdf(st.session_state['url'], selected_questions)
        
        # Streamlit's native download button
        st.download_button(
            label=f"Download PDF ({len(selected_questions)} Questions)",
            data=pdf_bytes,
            file_name="youtube_quiz.pdf",
            mime="application/pdf",
            type="primary"
        )
    else:
        st.warning("You must select at least one question to generate a PDF.")
