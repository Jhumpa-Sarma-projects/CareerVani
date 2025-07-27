import os
import subprocess
import string
import tempfile
import logging
from io import BytesIO
from googletrans import Translator
import language_tool_python
import pronouncing
from flask_mail import Message
from xhtml2pdf import pisa
from flask import current_app

logger = logging.getLogger(__name__)

def transcribe(path, lang_code):
    whisper_dir = "whispercpp"
    whisper_cli = os.path.join(whisper_dir, "whisper-cli.exe")
    ffmpeg_bin = os.path.join(whisper_dir, "bin", "ffmpeg.exe")

    converted_path = os.path.join(whisper_dir, "input.wav")
    subprocess.run([
        ffmpeg_bin, "-y", "-i", path,
        "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", converted_path
    ], check=True)

    cmd = [whisper_cli, "-m", "ggml-base.bin", "-f", "input.wav", "-otxt", "-of", "input"]
    if lang_code and lang_code != "auto":
        cmd += ["--language", lang_code]

    subprocess.run(cmd, cwd=whisper_dir, check=True)
    output_txt_path = os.path.join(whisper_dir, "input.txt")
    with open(output_txt_path, "r", encoding="utf-8") as f:
        return f.read().strip()

def translate_if_needed(text, src_lang):
    if src_lang == "en":
        return text
    translator = Translator()
    return translator.translate(text, src=src_lang, dest="en").text

def grammar_analysis(text):
    try:
        tool = language_tool_python.LanguageTool('en-US', remote_server='http://localhost:8081')
    except:
        tool = language_tool_python.LanguageTool('en-US')
    matches = tool.check(text)
    return matches

def pronunciation_score(text):
    words = text.translate(str.maketrans('', '', string.punctuation)).lower().split()
    matched = sum(1 for w in words if pronouncing.phones_for_word(w))
    return int((matched / len(words)) * 10) if words else 0

def suggestions(score):
    if score >= 8:
        return "🟢 Excellent pronunciation! Just maintain consistency."
    elif score >= 5:
        return "🟡 Good effort. Focus on clarity, especially vowel sounds."
    else:
        return "🔴 Needs work. Practice difficult words and mimic native speakers."

def generate_pdf_report(text, grammar_matches, score, suggestion):
    html_content = f"""
    <html>
    <body>
        <h2>Spoken English Feedback Report</h2>
        <p><strong>Transcribed Text:</strong> {text}</p>
        <p><strong>Pronunciation Score:</strong> {score}/10</p>
        <p><strong>Suggestion:</strong> {suggestion}</p>
        <p><strong>Grammar Issues:</strong></p>
        <ul>
    """
    for match in grammar_matches:
        html_content += f"<li>{match.message} (Suggestion: {', '.join(match.replacements)})</li>"
    html_content += "</ul></body></html>"

    pdf_io = BytesIO()
    pisa.CreatePDF(BytesIO(html_content.encode("utf-8")), dest=pdf_io)
    pdf_io.seek(0)
    return pdf_io

def send_report_email(user_email, pdf_io):
    msg = Message("Your Spoken English Feedback Report",
                  sender=current_app.config['MAIL_USERNAME'],
                  recipients=[user_email])
    msg.body = "Dear user,\n\nPlease find attached your spoken English feedback report.\n\nRegards,\nCareerVani Team"
    msg.attach("SpokenEnglishReport.pdf", "application/pdf", pdf_io.read())
    try:
        mail = current_app.extensions.get("mail")
        if mail:
            mail.send(msg)
            logger.info("Feedback report emailed successfully.")
        else:
            logger.warning("Mail extension not initialized.")
    except Exception as e:
        logger.error(f"Error sending email: {e}")
