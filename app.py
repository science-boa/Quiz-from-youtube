import streamlit as st
from fpdf import FPDF
import google.generativeai as genai

# --- CONFIGURATION ---
# Instead of hardcoding, tell Streamlit to look in its secure "secrets" vault
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("API Key not found! Please set GEMINI_API_KEY in Streamlit secrets.")
    st.stop()

# --- FUNCTIONS ---
def generate_pdf(text_content):
    pdf = FPDF()
    pdf.add_page()
    # Using Courier for strict monospaced alignment
    pdf.set_font("Courier", size=11)
    
    # Clean the text: remove markdown code block markers if the AI accidentally adds them
    clean_text = text_content.replace("```text", "").replace("```", "").strip()
    
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
        model = genai.GenerativeModel('gemini-3.5-flash')
        prompt = f"""

        Analyze the YouTube URL: {url} and generate a 12-question multiple-choice quiz.
        
        STRICT FORMATTING RULES:
        1. First line: "Embed this video in the first section header: {url}"
        2. THE 12 QUIZ QUESTIONS (QUESTIONS 1-12)
            - Generate exactly 12 multiple-choice questions testing core concepts discussed in the video.
            -  Format the question numbers with a period (e.g., "1. ", "2. ").
            - Provide exactly 4 options labeled uppercase as "A.", "B.", "C.", "D.".
            - Then add a single blank line.
            - Then include the correct answer letter in the format: "Answer: B"
            Do not use bolding or markdown 
            - Separate each question block with exactly one blank line.
        4. SECRET PROGRAMMATIC DESCRIPTION (QUESTION 13)
            - Create a final question numbered "13. " with the exact title text: "Metadata".
            - Directly underneath the title, map out an array containing the expanded pedagogical feedback string corresponding to every single question.
            - Format each item exactly like this: [Q1-[correct_letter]|Tip:[Detailed, formal educational breakdown of why the answer is correct or the core science principle behind it]].
            - Separate every bracketed item using a double-hash delimiter: "##" 
            - Example: [Q1-b|Tip:Detailed explanation...]##[Q2-c|Tip:Detailed explanation...]
        5. NO bullet points, NO tables, NO markdown formatting, NO conversational filler.
        6. MANDATORY OUTPUT FORMATTING
        - You must output the ENTIRE quiz (Steps 1, 2, and 3) inside a single, continuous Markdown code block (using ```text ... ```).
        - Ensure the metadata in Question 13 remains a continuous raw text string block without any bullet points, numbers, or visual formatting.
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
