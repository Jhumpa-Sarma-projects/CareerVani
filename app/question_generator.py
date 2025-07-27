# question_generator.py

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Example follow-up question bank
FOLLOW_UP_QUESTIONS = {
    "banking": [
        "Can you explain how interest rates affect customer loans?",
        "Have you ever dealt with a difficult banking customer?",
        "What are current challenges in the banking sector?",
        "How do you maintain compliance with regulations?",
        "What do you understand about AML practices?"
    ],
    "it": [
        "Can you describe a debugging challenge you overcame?",
        "What’s your favorite programming language and why?",
        "How do you approach system design?",
        "Have you worked with REST APIs?",
        "Describe a project where you implemented security best practices."
    ],
    "behavioral": [
        "How do you handle feedback from a supervisor?",
        "Describe a time you resolved a team conflict.",
        "How do you stay organized under pressure?",
        "What’s your approach to time management?",
        "Give an example of when you had to quickly adapt to change."
    ]
}

def get_best_followups(transcript, domain, top_n=5):
    questions = FOLLOW_UP_QUESTIONS.get(domain, [])
    corpus = [transcript] + questions
    tfidf = TfidfVectorizer().fit_transform(corpus)
    scores = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()
    top_indices = scores.argsort()[-top_n:][::-1]
    return [questions[i] for i in top_indices]

