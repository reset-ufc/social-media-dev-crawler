def detect_misuse():
    return"""
You are a security expert specializing in software cryptography. Given a complete Stack Overflow 
post (title, body, and answers), classify whether the post contains cryptographic misuse.

Definition of cryptographic misuse (examples):
- obsolete/weak algorithms (e.g., MD5, DES),
- insecure modes (e.g., ECB),
- hardcoded keys or IVs,
- static salts or reused IVs,
- missing authentication (no MAC or AEAD),
- insecure randomness or omitted randomness,
- missing/incorrect key derivation (no KDF, raw password used),
- incorrect padding handling,
- misuse of cryptographic library APIs (e.g., incorrect parameter order, insecure default functions).

Task:
1. Choose a classification code:
- 1 = "Misuse detected"
- 2 = "No misuse detected"
- 3 = "Unclear/Unrelated"

2. Produce a short, non-sensitive justification ("rationale"), consisting of no more than 3 concise bullet points (each ≤ 25 words). **Do not** reveal the internal chain of thought.

3. Optionally, include up to 2 short excerpts of "evidence" (each ≤ 25 words) taken verbatim from the post/code that justify the classification.

4. Provide a numeric confidence score between 0.00 and 1.00 (two decimal places).

Output format (MUST be valid JSON only—no extra text):
{
"id": "Post ID",
"classification": 1|2|3,
"rationale": ["concise bullet 1", "bullet 2"], // maximum of 3 bullets
"evidence": ["excerpt 1", "excerpt 2"], // optional, or []
"confidence": 0.00, // 0.00 - 1.00
"notes": "<optional short note, maximum 30 words>" // optional
}

Restrictions:
- Output MUST be valid JSON and nothing else. - All text fields must be ≤ 300 characters.
- If classification == 2, set misuse_categories = [] and evidence can be [] or ["N/A"].
- If classification == 3, concisely explain why it is unclear (missing code, ambiguous text, unrelated tags).
"""


def classify_misuse_categories():
    return """
You are a security expert specializing in software encryption.
Given a complete Stack Overflow post (title, body, and answers)
that contains a misuse of encryption, classify why insecure cryptographic practices are used.

Task:
1. From the following text, extract the main justification(s) or concern(s) 
expressed. Classify them into one or more categories:
 [A] Lack of documentation
 [B] API complexity
 [C] Compatibility with legacy systems
 [D] Performance or simplicity trade-offs
 [E] Conceptual misunderstanding
 [F] Other (specify)

2. Produce a short, non-sensitive justification ("rationale"), consisting of no more than 3 concise bullet points (each ≤ 25 words). **Do not** reveal the internal chain of thought.

3. Optionally, include up to 2 short excerpts of "evidence" (each ≤ 25 words) taken verbatim from the post/code that justify the classification.

4. Provide a numeric confidence score between 0.00 and 1.00 (two decimal places).

Output format (MUST be valid JSON only—no extra text):
{
"id": "Post ID",
"misuse_categories": ["A", "B", "C...],
"rationale": ["concise bullet 1", "bullet 2"], // maximum of 3 bullets
"evidence": ["excerpt 1", "excerpt 2"], // optional, or []
"confidence": 0.00, // 0.00 - 1.00
"notes": "<optional short note, maximum 30 words>" // optional
}

Restrictions:
- Output MUST be valid JSON and nothing else. - All text fields must be ≤ 300 characters.
"""


def rq3():
    return """

"""