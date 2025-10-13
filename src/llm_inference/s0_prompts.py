def detect_misuse():
    return """
You are a security expert specializing in software cryptography. 
Given a complete Stack Overflow post (title, body, and answers), classify whether the post contains cryptographic misuse.

Definition of cryptographic misuse:
A cryptographic misuse occurs when a developer applies cryptography incorrectly, introducing or implying a real security weakness in implementation or design.
This includes:
- Using weak or deprecated algorithms,
- Using insecure modes or parameters,
- Hardcoding keys or secrets,
- Incorrect use of random number generators,
- Insecure padding or truncation in code,
- Omitting authentication or verification steps.

Do **NOT** classify as misuse:
- Posts that only discuss **protocol specifications** (e.g., TLS, RFCs) without showing incorrect implementation
- Posts that quote RFCs, explain correct behavior, or discuss **alignment, encoding, version negotiation**, or other non-security-logic details
- Theoretical, conceptual, or documentation-level questions
- Questions without code, configuration, or clear implementation context

If the post merely discusses how a protocol field *should* behave according to a specification (e.g., "legacy_session_id must be zero-length"), it is **not misuse**.

Task:
1. Choose a classification code:
   - 1 = "Misuse detected"
   - 2 = "No misuse detected"

2. Provide a short, factual justification ("rationale") with up to **3 concise bullet points** (each ≤ 25 words). 
   Focus on the reasoning, not speculation. Do **not** reveal internal reasoning.

3. Optionally include up to **2 short excerpts of evidence** (≤ 25 words each) taken verbatim from the post.

4. Assign a confidence rating:
   - low = uncertain or ambiguous
   - medium = somewhat clear but incomplete
   - high = clear and well-evidenced classification

Restrictions:
- Output MUST be **valid JSON only**, no explanations or extra text.
- All text fields ≤ 300 characters.

---

{post}

Output format (MUST be valid JSON only—no extra text):
{{
"id": ,
"site": ,
"classification": 1|2,
"rationale": ["concise bullet 1", "bullet 2"], // maximum of 3 bullets
"evidence": ["excerpt 1", "excerpt 2"], // optional, or []
"confidence": low|medium|high
"notes": "<optional short note, maximum 30 words>" // optional
}}
"""


def classify_misuse_categories():
    return """
You are a security expert specializing in software encryption.
Given a complete Stack Overflow post (title, body, and answers), your task is to identify and classify the **primary insecure cryptographic practice** contained within it.

---

### Classification Rules
1.  **Focus on the Core Issue:** The classification must target the **most explicit and severe cryptographic error** discussed in the post.
2.  **Avoid Inference:** Classify the issue strictly based on the primitives mentioned. **DO NOT infer the use of CBC mode, IV management, or AES/RSA** if those terms are not explicitly present in the text.
3.  **Select the Best Subtype:** Choose the **most specific Subtype** from the structure below that accurately describes the misuse.

### Classification Structure (Group, Category, Subtype)

### Code-level Misuses**
- **Weak Cryptography (WC)**
    - Risky or broken encryption
    - Proprietary cryptography
    - Deterministic symmetric encryption
    - Risky or broken hash/MAC
    - Custom implementation
    - Wrong configs for PBE
- **Coding and Implementation Bugs (CIB)**
    - Common coding errors
    - Buggy IV generation
    - No cryptography
    - Leakage of keys
- **Bad Randomness Handling (BRH)**
    - Use of statistical PRNGs
    - Predictable, low entropy seeds
    - Static, fixed seeds
    - Reused seeds

### Design flaws**
- **Program Design Flaws (PDF)**
    - Insecure behavior by default
    - Insecure key handling
    - Insecure use streamciphers
    - Insecure combo enc. w/ auth.
    - Insecure combo enc. w/ hash
    - Side-channel attacks
- **Improper Certificate Validation (ICV)**
    - Absent validation of certs
    - Insecure SSL/TLS channel
    - Incomplete cert. validation
    - Absent host/user validation
    - Wildcards, self-signed certs
- **Public-Key Cryptography (PKC)**
    - Deterministic encrypt. RSA
    - Insecure padding RSA enc.
    - Weak configs for RSA enc.
    - Insecure padding RSA sign.
    - Weak signatures w/ RSA
    - Weak signatures w/ ECDSA
    - Insecure DH or ECDH
    - Insecure elliptic curves

### Insecure architectures**
- **IV and Nonce Management (IVM)**
    - CBC with non-random IV
    - CTR with static counter
    - Hard-coded or constant IV
- **Poor Key Management (PKM)**
    - Short key, improper key size
    - Hard-coded or constant keys
    - Hard-coded PBE passwords
    - Key reuse in streamciphers
    - Reuse of expired keys
    - Issues in key distribution
- **Crypto Architecture and Infrastructure (CAI)**
    - Crypto Agility Issues
    - API Misunderstandings
    - Multiple Access Points
    - Randomness Reuse Issues
    - PKI and CA Issues

**Field Constraints:**
* **Rationale:** Maximum of 3 concise bullet points (each ≤ 25 words).
* **Evidence:** Up to 2 short verbatim excerpts (each ≤ 25 words) from the post, or `[]` if none.
* **Confidence:** Must be `low`, `medium`, or `high`.
* **All text fields:** Must be ≤ 300 characters total.

The complete Stack Overflow post
{post}

**Output:** **MUST** be valid JSON and nothing else.

```json
{{
"id": "Post ID",
"misuse_group": "Group Name Only",
"misuse_category": "Acronym Only",
"misuse_subtype": "Subtype Name Only",
"rationale": ["concise bullet 1", "bullet 2"], // maximum 3 bullets
"evidence": ["excerpt 1", "excerpt 2"], // optional, or []
"confidence": "low|medium|high",
"notes": "<optional short note, maximum 30 words>" // optional
}}
"""


def rq3():
    return """

"""
