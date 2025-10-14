def classify_misuse_and_categories():
    return """
You are a security expert specializing in software encryption. 
Given a complete Stack Overflow post (title, body, answers and coments), 
your task is to identify whether the post contains cryptographic misuse and, if so, 
and classify what types of misuse it contains.

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

Only if any misuse is detected should you classify which types were found.

### Classification Rules
1.  **Focus on the Core Issue:** The classification must target the **most explicit and severe cryptographic error** discussed in the post.
2.  **Select the Best Subtype:** Choose the **most specific Subtype** from the structure below that accurately describes the misuse.

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
* is_misuse: yes or no
* Rationale: Maximum of 3 concise bullet points (each ≤ 25 words).
* Evidence: Up to 2 short verbatim excerpts (each ≤ 25 words) from the post, or `[]` if none.
* Confidence: reliability of inference
* All text fields: Must be ≤ 300 characters total.

The complete Stack Overflow post:
{post}

**Output:** **MUST** be valid JSON and nothing else.

```json
{{
"id": "Post ID",
"is_misuse":,
"misuse_groups": "Group Name Only",
"misuse_categories": "Acronym Only",
"misuse_subtypes": "Subtype Name Only",
"rationale": ["concise bullet 1", "bullet 2"], // maximum 3 
"evidence": ["excerpt 1", ...], // optional
"confidence": "0%-100%",
"notes": "<optional short note, maximum 30 words>" // optional
}}
"""


def judge():
    return """
YYou are an **independent security expert** acting as a **judge** between model predictions.  
You are given:
1. The **complete Stack Overflow post**.  
2. The **official inference prompt** used to classify cryptographic misuse.  
3. Two **model outputs** (Model A and Model B) generated using that same inference prompt.

Your goal is to **evaluate the agreement and quality** of both model outputs in relation to each other, without introducing new classifications or reinterpreting the post.

---

### Step 1. Evaluation Criteria

You must assess the following dimensions:

1. **Misuse Detection Agreement (0-1):**  
   - 1 → both models agree (same `is_misuse` value)  
   - 0 → one says “yes” and the other says “no”  

2. **Classification Match (0-1):**  
   - 1 → identical `misuse_groups`, `misuse_categories`, and `misuse_subtypes`  
   - 0.5 → partial match (same group or category but different subtype)  
   - 0 → completely different classifications  

3. **Rationale Alignment (0-1):**  
   - 1 → rationales express the same reasoning or highlight the same issue  
   - 0.5 → partially similar reasoning  
   - 0 → reasoning differs significantly  

4. **Evidence Overlap (0-1):**  
   - 1 → both cite similar or overlapping excerpts  
   - 0.5 → partial overlap  
   - 0 → unrelated or missing excerpts  

5. **Confidence Agreement (0-1):**  
   - 1 → identical or very close (≤10% difference)  
   - 0.5 → moderately different (10-30% difference)  
   - 0 → large difference (>30%)  

Then compute:  
**disagreement_score = 1 - average(five scores above)**  

Finally, indicate which model produced the **most coherent and rule-consistent** classification.

---

### Step 2. Output Format

Your output **must** be valid JSON and nothing else.

```json
{{
  "id": "Post ID",
  "misuse_detection_agreement": 0|1,
  "classification_match": 0|0.5|1,
  "rationale_alignment": 0|0.5|1,
  "evidence_overlap": 0|0.5|1,
  "confidence_agreement": 0|0.5|1,
  "disagreement_score": "float between 0 and 1",
  "preferred_model": "A | B | tie",
  "justification": "Short explanation (max 50 words)."
}}
"""
