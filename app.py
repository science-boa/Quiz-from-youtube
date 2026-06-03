import streamlit as st
from fpdf import FPDF
import google.generativeai as genai

# --- CONFIGURATION ---
# Replace with your actual Gemini API Key
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- FUNCTIONS ---
def generate_pdf(text_content):
    pdf = FPDF()
    pdf.add_page()
    # Using Courier for strict monospaced alignment
    pdf.set_font("Courier", size=11)
    
    # Clean the text: remove markdown code block markers if the AI accidentally adds them
    clean_text = text_content.replace("```text", "").replace("
```", "").strip()
    
    # Force line breaks to ensure MS Forms parser reads the structure correctly
    for line in clean_text.split('\n'):
        # Encode to latin-1 to avoid character errors
        encoded_line = line.encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(200, 5, txt=encoded_line, ln=True)
    
    return pdf.output(dest='S').encode('latin-1')

# --- UI LOGIC ---
st.title("Quiz-to-PDF Architect")

url = st.text_input("Paste YouTube URL:")

if url:
    # 1. API Call
    if st.button("Generate Questions"):
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        Analyze the YouTube URL: {url} and generate a 12-question multiple-choice quiz.
        
        STRICT FORMATTING RULES:
        1. First line: "Embed this video in the first section header: {url}"
        2. Questions 1-12: Numbered "1. ", "2. ". Exactly 4 options: "a)", "b)", "c)", "d)".
        3. Correct answer: Append " - Correct" to the correct option line (no bolding).
        4. Question 13: Title "13. Metadata".
        5. Question 13 Body: One continuous text block. Format: [Q1-[letter]|Tip:[Explanation]]##[Q2-[letter]|Tip:[Explanation]].
        6. NO bullet points, NO tables, NO markdown formatting, NO conversational filler.
        """
        response = model.generate_content(prompt)
        st.session_state['quiz'] = response.text

    # 2. Live Editor
    if 'quiz' in st.session_state:
        edited_quiz = st.text_area("Review/Edit Quiz:", st.session_state['quiz'], height=500)
        
        # 3. Render PDF
        if st.button("Generate Import-Ready PDF"):
            pdf_bytes = generate_pdf(edited_quiz)
            st.download_button(
                label="Download quiz_import.pdf",
                data=pdf_bytes,
                file_name="quiz_import.pdf",
                mime="application/pdf"
            )
            st.success("PDF generated successfully!")
