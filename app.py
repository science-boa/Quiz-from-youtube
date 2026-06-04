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
    # Dynamically calculate a tall canvas height to prevent pagination (approx 80mm per question block + metadata padding)
    calculated_height = 150 + (len(questions_list) * 80)
    
    # Initialize FPDF with a custom size layout using the calculated height
    pdf = FPDF(orientation='P', unit='mm', format=(210, calculated_height))
    pdf.set_auto_page_break(False)  # Forces everything onto a single continuous page
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
        add_line(f"ANSWER: {q['Answer']}")
        add_line(f"POINT: {q.get('points', 1)}")  # Updated format to match 'POINT: X' precisely
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
                  "
