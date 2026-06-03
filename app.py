import streamlit as st
import google.generativeai as genai
from fpdf import FPDF
import json
import re
from youtube_transcript_api import YouTubeTranscriptApi

# --- CONFIGURATION & SETUP ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("API Key missing! Please set GEMINI_API_KEY in your Streamlit Cloud Secrets.")
    st.stop()

st.title("YouTube to Quiz Architect")
st.write("Generate, review, and export custom video quizzes.")

# --- HELPER FUNCTIONS ---
def get_youtube_id(url):
    """Extracts the 11-character video ID from a standard YouTube URL."""
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    return match.group(1) if match else None

def get_video_transcript(video_id):
    """Fetches the transcript text using the YouTube API with robust fallbacks."""
    try:
        # First attempt: Try standard English
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'en-US', 'en-GB'])
        full_text = " ".join([item['text'] for item in transcript_list])
        return full_text
        
    except Exception:
        # Second attempt: If standard English fails, find ANY available transcript
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Grab the first available transcript (whether manual or auto-generated)
            for transcript in transcript_list:
                # Fetch it and translate it to English on the fly
                translated_transcript = transcript.translate('en').fetch()
                full_text = " ".join([item['text'] for item in translated_transcript])
                return full_text
                
        except Exception as e:
            return f"Error fetching fallback transcript: {e}"

def generate_pdf(video_url, questions_list):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Courier", size=11)
    
    def add_line(text):
        safe_text = text.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 5, txt=safe_text)
    
    add_line(video_url)
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

# --- MAIN APP LOGIC ---
url = st.text_input("Paste YouTube URL here:")

if st.button("Generate Questions"):
    if not url:
        st.warning("Please enter a URL first.")
    else:
        video_id = get_youtube_id(url)
        
        if not video_id:
            st.error("Could not find a valid YouTube Video ID in that URL.")
        else:
            with st.spinner("Fetching video transcript..."):
                transcript = get_video_transcript(video_id)
                
            if "Error fetching" in transcript:
                st.error("Could not get transcript. Make sure the video has closed captions/subtitles enabled.")
            else:
                with st.spinner("Gemini 3.5 Flash is analyzing the content..."):
                    try:
                        model = genai.GenerativeModel('gemini-3.5-flash')
                        
                        # Note how the prompt now includes the actual TRANSCRIPT text
                        prompt = f"""
                        Analyze the following transcript from a YouTube video. 
                        Generate exactly 15 multiple choice questions based on the core educational content.
                        
                        TRANSCRIPT:
                        {transcript}
                        
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
                        st.session_state['url'] = url
                        st.success("Questions generated successfully! Review them below.")
                        
                    except Exception as e:
                        st.error(f"An error occurred: {e}. Please try again.")

# --- LIVE REVIEW EDITOR ---
if 'quiz_data' in st.session_state:
    st.header("Review & Select Questions")
    st.write("Uncheck the box next to any question you want to remove from the final PDF.")
    
    selected_indices = []
    
    for i, q in enumerate(st.session_state['quiz_data']):
        with st.expander(f"Question {i+1}: {q['question'][:50]}...", expanded=True):
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
        pdf_bytes = generate_pdf(st.session_state['url'], selected_questions)
        st.download_button(
            label=f"Download PDF ({len(selected_questions)} Questions)",
            data=pdf_bytes,
            file_name="youtube_quiz.pdf",
            mime="application/pdf",
            type="primary"
        )
    else:
        st.warning("You must select at least one question to generate a PDF.")
