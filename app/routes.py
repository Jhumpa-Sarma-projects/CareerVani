from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app, make_response, session, jsonify
from flask_login import login_required, current_user
from .models import SpeechFeedback
import os
import logging
import language_tool_python
import pronouncing
from googletrans import Translator
from langdetect import detect
from io import BytesIO
from .grammar_rules import CUSTOM_PATTERNS
import tempfile
import whisper
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

main = Blueprint("main", __name__)

@main.route("/")
def home():
    return render_template("index.html")

@main.route("/dashboard")
@login_required
def dashboard():
    name = getattr(current_user, 'name', current_user.email)
    feedback_list = SpeechFeedback.query.filter_by(user_id=current_user.id).order_by(SpeechFeedback.timestamp.desc()).all()
    return render_template("dashboard.html", name=name, feedback_list=feedback_list)

@main.route("/spoken")
@login_required
def spoken_input():
    return render_template("spoken_result.html", score=None)

@main.route("/regional_voice_input")
@login_required
def regional_voice_input():
    return render_template("regional_translate.html")

@main.route("/spoken_result", methods=["POST"])
@login_required
def spoken_result():
    if "transcript" in request.form:
        transcript = request.form["transcript"].strip()

        tool = language_tool_python.LanguageTool('en-US', remote_server='http://localhost:8081')
        matches = tool.check(transcript)
        suggestions = [f"📝 \"{match.context}\" ➔ {match.message}" for match in matches]
        corrected_text = language_tool_python.utils.correct(transcript, matches)

        custom_suggestion = ""
        for bad, good in CUSTOM_PATTERNS.items():
            if bad.lower() in transcript.lower():
                custom_suggestion = f"💡 Did you mean: \"{good}\"?"
                corrected_text = good
                break

        words = transcript.split()
        recognized = sum([1 for word in words if pronouncing.phones_for_word(word.lower())])
        total = len(words)
        raw_score = (recognized / total) * 10 if total > 0 else 0

        grammar_penalty = min(len(matches), 5)
        if len(words) < 4 or custom_suggestion:
            grammar_penalty += 2

        score = max(round(raw_score - grammar_penalty, 2), 0)
        score = min(score, 8.5)

        if score >= 9:
            badge = "🌟 Excellent"
        elif score >= 7:
            badge = "👍 Good"
        elif score >= 5:
            badge = "🖰 Needs Improvement"
        else:
            badge = "🚨 Practice More"

        feedback_entry = SpeechFeedback(
            user_id=current_user.id,
            transcript=transcript,
            grammar_issues="; ".join(suggestions),
            pron_score=int(score),
            badge=badge
        )
        from . import db
        db.session.add(feedback_entry)
        db.session.commit()

        return render_template("spoken_result.html", transcript=transcript, corrected_text=corrected_text,
                               suggestions=suggestions, score=score, badge=badge,
                               suggestion="See analysis below", grammar_matches=matches,
                               custom_suggestion=custom_suggestion)
    else:
        flash("No transcript received.", "danger")
        return redirect(url_for("main.dashboard"))

@main.route("/regional_translate", methods=["GET", "POST"])
@login_required
def regional_translate():
    if request.method == "POST":
        transcript = request.form.get("transcript", "").strip()
        if not transcript:
            flash("No transcript received.", "danger")
            return redirect(url_for("main.regional_voice_input"))

        try:
            detected_lang = detect(transcript)
            translator = Translator()
            translated_text = translator.translate(transcript, src=detected_lang, dest='en').text

            tool = language_tool_python.LanguageTool('en-US', remote_server='http://localhost:8081')
            matches = tool.check(translated_text)
            suggestions = [f"📝 \"{match.context}\" ➔ {match.message}" for match in matches]

            feedback_entry = SpeechFeedback(
                user_id=current_user.id,
                transcript=f"Original: {transcript} || Translated: {translated_text}",
                grammar_issues="; ".join(suggestions),
                pron_score=None,
                badge="🌐 Regional"
            )
            from . import db
            db.session.add(feedback_entry)
            db.session.commit()

            return render_template("regional_translate.html", transcript=transcript,
                                   translated_text=translated_text, suggestions=suggestions)
        except Exception as e:
            logging.error(f"Regional feedback error: {e}")
            flash("Processing failed. Try again.", "danger")
            return redirect(url_for("main.regional_voice_input"))

    return render_template("regional_translate.html")

@main.route("/download/<filename>")
@login_required
def download_feedback(filename):
    filepath = os.path.join(current_app.root_path, "static", "feedback_reports", filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    flash("Report file not found.", "danger")
    return redirect(url_for("main.dashboard"))

# ------------------- VIDEO INTERVIEW ROUTES ------------------- #

@main.route("/video_interview")
@login_required
def video_interview():
    return render_template("video_interview.html")

@main.route("/submit_video_response", methods=["POST"])
@login_required
def submit_video_response():
    if "video" not in request.files:
        return jsonify({"error": "No video uploaded."}), 400

    video = request.files["video"]
    domain = session.get("video_interview_domain", "it")  # Default domain
    history = session.get("video_qna", [])

    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_video:
        video.save(temp_video.name)
        temp_path = temp_video.name

    model = whisper.load_model("base")
    result = model.transcribe(temp_path)
    os.remove(temp_path)

    transcript = result.get("text", "").strip()
    history.append(transcript)

    follow_ups = get_follow_up_questions(domain, history)
    next_question = follow_ups[len(history) % len(follow_ups)]

    session["video_qna"] = history
    return jsonify({"next_question": next_question})

# ------------------- MOCK INTERVIEW MODULE ------------------- #

@main.route("/mock_interview")
@login_required
def mock_interview():
    return render_template("mock_interview.html")

@main.route("/start_mock_interview", methods=["POST"])
@login_required
def start_mock_interview():
    domain = request.form.get("domain")
    if domain not in ["banking", "it", "behavioral"]:
        flash("Invalid domain selected.", "danger")
        return redirect(url_for("main.mock_interview"))

    questions = get_domain_questions(domain)
    session["interview"] = {"domain": domain, "qna": [], "questions": questions}
    session["video_interview_domain"] = domain
    session["video_qna"] = []

    return render_template("interview_session.html", question=questions[0], index=0, total=len(questions), last=False)

@main.route("/submit_answer", methods=["POST"])
@login_required
def submit_answer():
    index = int(request.form.get("question_index"))
    answer = request.form.get("answer")

    if "interview" not in session:
        flash("Session expired. Please restart your mock interview.", "danger")
        return redirect(url_for("main.dashboard"))

    interview = session["interview"]
    questions = interview["questions"]
    current_question = questions[index]

    interview["qna"].append((current_question, answer))
    session["interview"] = interview

    if index + 1 < len(questions):
        next_question = questions[index + 1]
        return render_template("interview_session.html", question=next_question, index=index+1, total=len(questions), last=(index+1 == len(questions)-1))
    else:
        content = f"Mock Interview Summary - Domain: {interview['domain'].title()}\n\n"
        for i, (q, a) in enumerate(interview["qna"], 1):
            content += f"Q{i}: {q}\nA{i}: {a}\n\n"

        session.pop("interview", None)

        response = make_response(content)
        response.headers["Content-Disposition"] = "attachment; filename=mock_interview.txt"
        response.headers["Content-Type"] = "text/plain"
        return response

def get_domain_questions(domain):
    if domain == "banking":
        return [
            "What interests you about the banking sector?",
            "How do you stay updated with financial regulations?",
            "Describe a time you managed risk.",
            "What is your understanding of KYC?",
            "Explain a banking product you recently learned about."
        ]
    elif domain == "it":
        return [
            "Tell me about a recent IT project you worked on.",
            "How do you handle debugging complex issues?",
            "What technologies are you most comfortable with?",
            "Describe your experience with cloud services.",
            "How do you keep your skills updated?"
        ]
    elif domain == "behavioral":
        return [
            "Describe a time when you faced a conflict at work and how you resolved it.",
            "Tell me about a time you demonstrated leadership.",
            "What is your biggest professional failure and what did you learn?",
            "Describe a situation where you had to work under pressure.",
            "How do you handle constructive criticism?"
        ]
    return []

def get_follow_up_questions(domain, history):
    base_questions = get_domain_questions(domain)
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(base_questions + history)
    similarities = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1]).flatten()
    top_indices = similarities.argsort()[::-1][:5]
    return [base_questions[i] for i in top_indices]


@main.route("/video_interview_log")
@login_required
def video_interview_log():
    domain = session.get("video_interview_domain", "Unknown").title()
    responses = session.get("video_qna", [])

    if not responses:
        flash("No video interview responses found.", "warning")
        return redirect(url_for("main.dashboard"))

    questions = get_follow_up_questions(domain.lower(), responses)
    qa_pairs = list(zip(questions, responses))

    return render_template("video_interview_log.html", domain=domain, qa_pairs=qa_pairs)
