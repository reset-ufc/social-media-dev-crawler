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
"id": "Post ID",
"classification": 1|2|3,
"rationale": ["concise bullet 1", "bullet 2"], // maximum of 3 bullets
"evidence": ["excerpt 1", "excerpt 2"], // optional, or []
"confidence": low|medium|high
"notes": "<optional short note, maximum 30 words>" // optional
}}
"""


def classify_misuse_categories():
    return """
You are a security expert specializing in software encryption.
Given a complete Stack Overflow post (title, body, and answers)
that contains a misuse of encryption, classify the type of insecure cryptographic practices.

Classify them into a group, category and subtype:
### **Group 1: Code-level Misuses — Bad practices at the code level**
Errors committed directly in code implementation, usually related to weak algorithms, incorrect use of libraries, or insecure practices.

- **Weak Cryptography (WC)** — Use of obsolete or weak cryptographic algorithms, functions, or practices.
    - *Risky or broken encryption* — Use of compromised or broken encryption schemes.
    - *Proprietary cryptography* — Creation of proprietary algorithms without public review.
    - *Deterministic symmetric encryption* — Symmetric encryption without the use of randomness, vulnerable to attacks.
    - *Risky or broken hash/MAC* — Use of hash or MAC functions known to be insecure.
    - *Custom implementation* — Homemade cryptographic implementations, prone to failure.
    - *Wrong configs for PBE* — Incorrect configuration of password-based encryption functions.

- **Coding and Implementation Bugs (CIB)** — Programming errors that compromise cryptographic security.
    - *Common coding errors* — Common flaws in code logic or syntax.
    - *Buggy IV generation* — Incorrect generation of initialization vectors (IV).
    - *No cryptography* — Lack of cryptographic protection where needed.
    - *Leakage of keys* — Accidental exposure of cryptographic keys.

- **Bad Randomness Handling (BRH)** — Problems related to the generation and use of random values.
    - *Use of statistical PRNGs* — Use of statistical pseudorandom generators that are inadequate for security.
    - *Predictable, low entropy seeds* — Predictable or low entropy seeds.
    - *Static, fixed seeds* — Reuse of fixed seeds.
    - *Reused seeds* — Reuse of random values, compromising security.

### **Group 2: Design flaws**
Deficiencies in protocol design or system architecture that make cryptographic use insecure.

- **Program Design Flaws (PDF)** — Conceptual problems in the design of cryptographic protocols.
    - *Insecure behavior by default* — Insecure default settings.
    - *Insecure key handling* — Improper key management.
    - *Insecure use streamciphers* — Incorrect use of stream ciphers.
    - *Insecure combo enc. w/ auth.* — Incorrect combination of encryption and authentication.
    - *Insecure combo enc. w/ hash* — Insecure combination of encryption and hashing.
    - *Side-channel attacks* — Flaws susceptible to side-channel attacks.

- **Improper Certificate Validation (ICV)** — Failures in the verification and use of digital certificates.
    - *Absent validation of certs* — Lack of certificate validation.
    - *Insecure SSL/TLS channel* — Insecure TLS/SSL channel configured.
    - *Incomplete cert. validation* — Partial or incorrect certificate validation.
    - *Absent host/user validation* — Lack of host or user name validation.
    - *Wildcards, self-signed certs* — Incautious use of wildcards or self-signed certificates.

- **Public-Key Cryptography (PKC) Issues** — Incorrect use of asymmetric algorithms.
    - *Deterministic encrypt. RSA* — Deterministic use of RSA without randomness.
    - *Insecure padding RSA enc.* — Insecure padding in RSA.
    - *Weak configs for RSA enc.* — Weak configurations for RSA encryption.
    - *Insecure padding RSA sign.* — Insecure padding in RSA signatures.
    - *Weak signatures w/ RSA* — RSA signatures with weak parameters.
    - *Weak signatures w/ ECDSA* — Insecure parameters in ECDSA signatures.
    - *Insecure DH or ECDH* — Insecure Diffie–Hellman implementation.
    - *Insecure elliptic curves* — Vulnerable or non-standard elliptic curves.

---
### **Group 3: Insecure architectures — Insecure architectures**
Structural errors that affect how cryptographic components integrate into the system.

- **IV and Nonce Management (IVM)** — Incorrect management of initialization vectors and nonces.
    - *CBC with non-random IV* — Use of a fixed IV in CBC mode.
    - *CTR with static counter* — Fixed counter in CTR mode.
    - *Hard-coded or constant IV* — Hard-coded initialization vector.

- **Poor Key Management (PKM)** — Deficiencies in key generation, storage, and rotation.
    - *Short key, improper key size* — Short or inadequately sized keys.
    - *Hard-coded or constant keys* — Hard-coded keys.
    - *Hard-coded PBE passwords* — Hard-coded passwords in PBE schemes.
    - *Key reuse in streamciphers* — Key reuse in stream ciphers.
    - *Reuse of expired keys* — Reuse of expired keys.
    - *Issues in key distribution* — Problems in secure key distribution.

- Crypto Architecture and Infrastructure (CAI) Issues — Structural flaws in the overall cryptographic design.
    - Crypto Agility Issues — Difficulty updating or changing algorithms.
    - API Misunderstandings — Incorrect use of cryptographic APIs.
    - Multiple Access Points — Exposure of multiple vulnerabilities.
    - Randomness Reuse Issues — Incorrect reuse of random values.
    - PKI and CA Issues — Problems with public key infrastructure and certification authorities.

    
Produce a short, non-sensitive justification ("rationale"), consisting of no more than 3 concise bullet points (each ≤ 25 words). **Do not** reveal the internal chain of thought.

Optionally, include up to 2 short excerpts of "evidence" (each ≤ 25 words) taken verbatim from the post/code that justify the classification.

Provide a numeric confidence score between 0.00 and 1.00 (two decimal places).

Restrictions:
- Output MUST be valid JSON and nothing else. - All text fields must be ≤ 300 characters.

{post}

Output format (MUST be valid JSON only—no extra text):
{
"id": "Post ID",
"misuse_group": group,
"misuse_category": category,
"misuse_subtype": subtype,
"rationale": ["concise bullet 1", "bullet 2"], // maximum of 3 bullets
"evidence": ["excerpt 1", "excerpt 2"], // optional, or []
"confidence": low|medium|high
"notes": "<optional short note, maximum 30 words>" // optional
}
"""


def rq3():
    return """

"""
