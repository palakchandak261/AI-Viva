"""
AI Service — Google Gemini 1.5 Flash
Falls back to smart pre-built questions if API key is missing/invalid.
"""
import json
import re
import random
from app.core.config import settings

# ── Client setup ──────────────────────────────────────────────────────────────
_client = None
AI_AVAILABLE = False

def _init_client():
    global _client, AI_AVAILABLE
    key = settings.GEMINI_API_KEY.strip()
    if not key or key == "your-gemini-api-key-here":
        AI_AVAILABLE = False
        return
    try:
        from google import genai
        _client = genai.Client(api_key=key)
        AI_AVAILABLE = True
    except Exception:
        AI_AVAILABLE = False

_init_client()


def _gen_config(temperature: float = 0.4):
    from google.genai import types
    return types.GenerateContentConfig(
        temperature=temperature,
        response_mime_type="application/json",
    )


def _parse_json(text: str):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _call_gemini(prompt: str, temperature: float = 0.4) -> str:
    """Make a Gemini API call. Raises exception if unavailable."""
    response = _client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=_gen_config(temperature),
    )
    return response.text


# ── PROMPTS ───────────────────────────────────────────────────────────────────

KNOWLEDGE_MAP_PROMPT = """You are an expert academic examiner. Analyze this student project and extract a knowledge map.
Return ONLY valid JSON:
{
  "project_title": "inferred title",
  "tech_stack": ["tech1", "tech2"],
  "key_topics": [{"topic": "name", "importance": "high", "subtopics": ["s1"]}],
  "design_decisions": ["decision1"],
  "potential_weak_areas": ["area1"],
  "suggested_question_topics": ["topic1", "topic2"]
}
Project content:\n"""

QUESTION_GEN_PROMPT = """You are a strict viva examiner. Generate exactly {count} viva questions for this project at {difficulty} difficulty.
Mix types: conceptual, decision, code, scenario, probe.
Return ONLY valid JSON:
{{"questions": [{{"question": "text", "type": "conceptual", "topic": "topic", "difficulty": "medium", "expected_keywords": ["kw1"]}}]}}
Make questions SPECIFIC to this project. Reference actual tech and decisions.
Project context:\n"""

ANSWER_EVAL_PROMPT = """Evaluate this student viva answer. Score 0-10.
Scoring: Accuracy(0-4) + Depth(0-3) + Clarity(0-2) + Relevance(0-1)
Return ONLY valid JSON:
{{"score": 7.0, "is_weak": false, "feedback": "feedback here", "missing_points": [], "positive_points": []}}
Question: {question}
Expected concepts: {keywords}
Student answer: {answer}
Project context: {context}"""

FOLLOWUP_PROMPT = """Student gave a weak viva answer. Generate ONE follow-up probe question.
Return ONLY valid JSON:
{{"question": "follow-up question", "type": "probe", "topic": "topic", "difficulty": "hard", "expected_keywords": ["kw1"]}}
Original question: {question}
Weak answer: {answer}
Topic: {topic}"""

REPORT_PROMPT = """Generate a comprehensive viva performance report.
Return ONLY valid JSON:
{{"overall_grade":"B","overall_score":72.5,"summary":"assessment","strengths":["s1"],"weaknesses":["w1"],"topic_scores":{{"Topic":75.0}},"recommendations":["r1"],"detailed_feedback":"paragraph"}}
Student: {name} | Topics: {topics} | Tech: {tech}
Transcript:\n{transcript}"""


# ── SERVICE FUNCTIONS ─────────────────────────────────────────────────────────

async def generate_knowledge_map(project_content: str) -> dict:
    if not AI_AVAILABLE:
        return _fallback_knowledge_map(project_content)
    try:
        text = _call_gemini(KNOWLEDGE_MAP_PROMPT + project_content[:8000], 0.3)
        return _parse_json(text)
    except Exception:
        return _fallback_knowledge_map(project_content)


async def generate_questions(
    project_content: str,
    knowledge_map: dict,
    count: int = 10,
    difficulty: str = "medium"
) -> list[dict]:
    if not AI_AVAILABLE:
        return _smart_fallback_questions(knowledge_map, count, difficulty)
    try:
        context = f"Knowledge Map:\n{json.dumps(knowledge_map)}\n\nContent:\n{project_content[:5000]}"
        prompt = QUESTION_GEN_PROMPT.format(count=count, difficulty=difficulty) + context
        text = _call_gemini(prompt, 0.7)
        raw = _parse_json(text)
        questions = raw.get("questions", raw) if isinstance(raw, dict) else raw
        if len(questions) < count:
            questions += _smart_fallback_questions(knowledge_map, count - len(questions), difficulty)
        return questions[:count]
    except Exception:
        return _smart_fallback_questions(knowledge_map, count, difficulty)


async def generate_followup_question(
    original_question: str,
    student_answer: str,
    topic: str,
    project_context: str
) -> dict:
    if not AI_AVAILABLE:
        return {"question": f"You mentioned '{student_answer[:40]}...' — can you explain that in more technical detail?", "type": "probe", "topic": topic, "difficulty": "hard", "expected_keywords": []}
    try:
        prompt = FOLLOWUP_PROMPT.format(
            question=original_question, answer=student_answer,
            topic=topic, context=project_context[:1500]
        )
        return _parse_json(_call_gemini(prompt, 0.5))
    except Exception:
        return {"question": f"Can you elaborate more on {topic}?", "type": "probe", "topic": topic, "difficulty": "medium", "expected_keywords": []}


async def evaluate_answer(
    question: str,
    student_answer: str,
    expected_keywords: list[str],
    project_context: str
) -> dict:
    if not student_answer or len(student_answer.strip()) < 5:
        return {"score": 0.0, "is_weak": True, "feedback": "No meaningful answer provided.", "missing_points": expected_keywords, "positive_points": []}

    if not AI_AVAILABLE:
        return _heuristic_evaluate(student_answer, expected_keywords)

    try:
        prompt = ANSWER_EVAL_PROMPT.format(
            question=question,
            keywords=", ".join(expected_keywords) if expected_keywords else "none",
            answer=student_answer,
            context=project_context[:1500]
        )
        result = _parse_json(_call_gemini(prompt, 0.1))
        result["is_weak"] = bool(result.get("is_weak", result.get("score", 10) < 5))
        return result
    except Exception:
        return _heuristic_evaluate(student_answer, expected_keywords)


async def generate_performance_report(
    exchanges: list[dict],
    knowledge_map: dict,
    student_name: str
) -> dict:
    transcript = "\n\n".join(
        f"Q{e['sequence_number']} [{e.get('topic','')}]: {e['question']}\n"
        f"Answer: {e.get('student_answer','No answer')}\nScore: {e.get('answer_score',0)}/10"
        for e in exchanges
    )

    if not AI_AVAILABLE:
        return _compute_report(exchanges, knowledge_map, student_name)

    try:
        prompt = REPORT_PROMPT.format(
            name=student_name,
            topics=", ".join(t.get("topic","") for t in knowledge_map.get("key_topics",[])),
            tech=", ".join(knowledge_map.get("tech_stack",[])),
            transcript=transcript[:7000]
        )
        return _parse_json(_call_gemini(prompt, 0.3))
    except Exception:
        return _compute_report(exchanges, knowledge_map, student_name)


# ── FALLBACKS (work without any API key) ─────────────────────────────────────

def _fallback_knowledge_map(content: str) -> dict:
    """Extract basic info from content without AI."""
    tech_keywords = ["python","fastapi","flask","django","react","node","express",
                     "mongodb","postgresql","sqlite","mysql","redis","docker",
                     "jwt","rest","graphql","typescript","javascript","java","spring"]
    found_tech = [t for t in tech_keywords if t.lower() in content.lower()]
    return {
        "project_title": "Student Project",
        "tech_stack": found_tech[:6] if found_tech else ["Python", "Web Framework"],
        "key_topics": [
            {"topic": "System Architecture", "importance": "high", "subtopics": ["Design", "Components"]},
            {"topic": "Technology Choices", "importance": "high", "subtopics": found_tech[:3]},
            {"topic": "Implementation", "importance": "medium", "subtopics": ["Backend", "Frontend"]},
            {"topic": "Testing & Deployment", "importance": "medium", "subtopics": ["Testing", "CI/CD"]},
        ],
        "design_decisions": ["Technology stack selection", "Database design", "API design"],
        "potential_weak_areas": ["Scalability", "Security", "Error handling"],
        "suggested_question_topics": ["Architecture", "Tech choices", "Challenges", "Testing"]
    }


def _smart_fallback_questions(knowledge_map: dict, count: int, difficulty: str) -> list[dict]:
    """Generate context-aware questions from knowledge map without AI."""
    tech = knowledge_map.get("tech_stack", ["the framework"])
    topics = [t.get("topic","") for t in knowledge_map.get("key_topics", [])]
    decisions = knowledge_map.get("design_decisions", [])
    title = knowledge_map.get("project_title", "your project")

    question_pool = [
        {"question": f"Explain the overall architecture of {title}.", "type": "conceptual", "topic": "Architecture", "difficulty": "medium", "expected_keywords": ["architecture", "components", "design"]},
        {"question": f"Why did you choose {tech[0] if tech else 'this technology'} for this project? What alternatives did you consider?", "type": "decision", "topic": "Tech Stack", "difficulty": "medium", "expected_keywords": ["performance", "ease of use", "alternatives"]},
        {"question": "How does data flow through your application from request to response?", "type": "conceptual", "topic": "Data Flow", "difficulty": "medium", "expected_keywords": ["request", "response", "database", "processing"]},
        {"question": "How did you handle authentication and authorization in your project?", "type": "conceptual", "topic": "Security", "difficulty": "medium", "expected_keywords": ["authentication", "authorization", "security"]},
        {"question": "What database did you choose and why? How did you design your schema?", "type": "decision", "topic": "Database", "difficulty": "medium", "expected_keywords": ["schema", "relationships", "normalization"]},
        {"question": "If your application suddenly gets 10x more users, what would break first and how would you fix it?", "type": "scenario", "topic": "Scalability", "difficulty": "hard", "expected_keywords": ["bottleneck", "scaling", "performance", "optimization"]},
        {"question": "How did you handle errors and exceptions throughout your application?", "type": "conceptual", "topic": "Error Handling", "difficulty": "medium", "expected_keywords": ["exception", "error handling", "logging", "user feedback"]},
        {"question": "Walk me through how you would test this application. What types of tests did you write?", "type": "conceptual", "topic": "Testing", "difficulty": "medium", "expected_keywords": ["unit test", "integration test", "testing strategy"]},
        {"question": "What was the most challenging technical problem you faced and how did you solve it?", "type": "conceptual", "topic": "Problem Solving", "difficulty": "medium", "expected_keywords": ["problem", "solution", "approach", "debugging"]},
        {"question": f"Explain how {tech[1] if len(tech) > 1 else 'your key library'} works and why it was important to your project.", "type": "conceptual", "topic": "Technology Deep Dive", "difficulty": "hard", "expected_keywords": []},
        {"question": "How did you ensure your API is secure against common vulnerabilities like SQL injection or XSS?", "type": "conceptual", "topic": "Security", "difficulty": "hard", "expected_keywords": ["sql injection", "validation", "sanitization", "security"]},
        {"question": "How would you add a caching layer to improve performance? What would you cache?", "type": "scenario", "topic": "Performance", "difficulty": "hard", "expected_keywords": ["cache", "redis", "performance", "ttl"]},
        {"question": "What improvements would you make if you had 2 more weeks to work on this project?", "type": "conceptual", "topic": "Reflection", "difficulty": "easy", "expected_keywords": ["improvement", "feature", "refactor"]},
        {"question": "How did you version and document your API?", "type": "conceptual", "topic": "API Design", "difficulty": "medium", "expected_keywords": ["versioning", "documentation", "swagger", "readme"]},
        {"question": "Describe the deployment process for your application.", "type": "conceptual", "topic": "Deployment", "difficulty": "medium", "expected_keywords": ["deploy", "server", "environment", "configuration"]},
    ]

    # Filter by difficulty
    if difficulty == "easy":
        pool = [q for q in question_pool if q["difficulty"] in ("easy", "medium")]
    elif difficulty == "hard":
        pool = [q for q in question_pool if q["difficulty"] in ("medium", "hard")]
    else:
        pool = question_pool

    random.shuffle(pool)
    result = pool[:count]
    # Pad if needed
    while len(result) < count:
        result.extend(pool)
    return result[:count]


def _heuristic_evaluate(answer: str, keywords: list[str]) -> dict:
    """Score answer without AI based on length and keyword presence."""
    word_count = len(answer.split())
    matched = sum(1 for kw in keywords if kw.lower() in answer.lower()) if keywords else 0
    keyword_ratio = matched / len(keywords) if keywords else 0.5

    # Base score from length + keywords
    length_score = min(word_count / 30, 1.0)  # 30 words = full length score
    score = round((length_score * 4 + keyword_ratio * 4 + min(word_count / 50, 1.0) * 2), 1)
    score = min(score, 10.0)
    is_weak = score < 5.0

    return {
        "score": score,
        "is_weak": is_weak,
        "feedback": (
            "Good detailed answer." if score >= 7
            else "Answer covers the basics but could be more detailed." if score >= 5
            else "Answer is too brief or missing key concepts."
        ),
        "missing_points": [kw for kw in keywords if kw.lower() not in answer.lower()],
        "positive_points": [kw for kw in keywords if kw.lower() in answer.lower()],
    }


def _compute_report(exchanges: list[dict], knowledge_map: dict, student_name: str) -> dict:
    """Compute report without AI from raw scores."""
    scores = [e.get("answer_score") or 0 for e in exchanges if e.get("student_answer")]
    avg = sum(scores) / len(scores) if scores else 0
    overall = round(avg * 10, 1)

    grade = "A" if overall >= 85 else "B" if overall >= 70 else "C" if overall >= 55 else "D" if overall >= 40 else "F"

    topic_scores = {}
    for e in exchanges:
        t = e.get("topic") or "General"
        if e.get("answer_score") is not None:
            topic_scores.setdefault(t, []).append(e["answer_score"])
    topic_avg = {t: round(sum(v)/len(v)*10, 1) for t, v in topic_scores.items()}

    weak = [e for e in exchanges if e.get("is_weak_answer")]
    strong = [e for e in exchanges if (e.get("answer_score") or 0) >= 7]

    return {
        "overall_grade": grade,
        "overall_score": overall,
        "summary": f"{student_name} completed the viva with an overall score of {overall}%. "
                   f"Answered {len(scores)} questions with {len(strong)} strong responses.",
        "strengths": list({e.get("topic","General") for e in strong})[:3],
        "weaknesses": list({e.get("topic","General") for e in weak})[:3],
        "topic_scores": topic_avg,
        "recommendations": [
            "Review topics where follow-up questions were triggered.",
            "Practice explaining technical decisions more clearly.",
            "Focus on depth over brevity in viva answers.",
        ],
        "detailed_feedback": (
            f"The student demonstrated {'strong' if overall >= 70 else 'moderate' if overall >= 50 else 'developing'} "
            f"understanding of the project. "
            f"{'Areas of strength include: ' + ', '.join(list({e.get('topic','') for e in strong})[:3]) + '.' if strong else ''} "
            f"{'Topics needing more attention: ' + ', '.join(list({e.get('topic','') for e in weak})[:3]) + '.' if weak else ''}"
        )
    }
