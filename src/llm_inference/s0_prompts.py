def classify_misuse_and_categories():
    return """
You are a **security expert** specializing in software encryption.
 Given a **complete Stack Overflow post** (title, body, answers, and comments), 
 your task is to identify whether the post contains **cryptographic misuse** and, 
 if so, to **classify and detail** the types of misuse found, adhering strictly to the provided JSON output format.
"""


def anderson():
    return """
You are a senior cryptography auditor. Analyze ONLY the Stack Overflow discussion below and identify ALL cryptographic misuses present.

<<<STACK_OVERFLOW_DISCUSSION>>>
{post}
<<<END_DISCUSSION>>>

Analyze strictly the content within these markers.

----------------------------
TASK
----------------------------
Detect and classify cryptographic misuses using the taxonomy and definition below. A single thread may contain multiple independent misuses — report ALL of them.
Each misuse MUST include: group (category), subtype (specific misuse), confidence (0–1), evidence (source_type + exact quote), and a short rationale explaining why it is insecure.

----------------------------
Definition of Cryptographic Misuse
----------------------------
A cryptographic misuse occurs when a developer applies cryptography incorrectly, 
introducing or implying a **real security weakness** in implementation or design.

This includes, but is not limited to:
* Using weak or deprecated algorithms.
* Using insecure modes or parameters.
* Hardcoding keys or secrets.
* Incorrect use of random number generators.
* Insecure padding or truncation in code.
* Omitting authentication or verification steps.

----------------------------
MISUSE TYPES TAXONOMY
----------------------------
Code-level Misuses
- WC (Weak Cryptography): risky/broken encryption; proprietary crypto; deterministic symmetric encryption; risky/broken hash or MAC; custom implementation; wrong PBE configs.
- CIB (Coding & Implementation Bugs): common coding errors; buggy IV generation; missing cryptography; key leakage.
- BRH (Bad Randomness Handling): statistical PRNGs; predictable/low-entropy seeds; static/fixed seeds; reused seeds.

Design Flaws
- PDF (Program Design Flaws): insecure by default; insecure key handling; insecure use of stream ciphers; insecure enc–auth combos; insecure enc–hash combos; side-channel vulnerabilities.
- ICV (Improper Certificate Validation): absent cert validation; insecure SSL/TLS channel; incomplete validation; missing host/user validation; wildcard/self-signed certificates.
- PKC (Public-Key Cryptography): deterministic RSA encryption; insecure RSA padding (enc/sign); weak RSA configs; weak RSA/ECDSA signatures; insecure DH/ECDH; insecure elliptic curves.

Insecure Architectures
- IVM (IV & Nonce Management): CBC with non-random IV; CTR with static counter; hardcoded/constant IV.
- PKM (Poor Key Management): short/improper key sizes; hardcoded/constant keys; hardcoded PBE passwords; key reuse in stream ciphers; reuse of expired keys; issues in key distribution.
- CAI (Crypto Architecture & Infrastructure): crypto agility issues; API misunderstandings; multiple access points; randomness reuse; PKI/CA misconfigurations.

----------------------------
DECISION RULES
----------------------------
1) has_misuse
- Set "has_misuse": true if any code, configuration, or recommendation demonstrates or promotes an insecure cryptographic practice.
- Set "has_misuse": false ONLY if the accepted answer fully fixes all issues AND no insecure approach remains endorsed.

2) Label assignment
- Assign one label per independent misuse (follow the taxonomy).
- Merge duplicates when multiple findings share the same root cause.

3) Evidence requirements
- Provide one short quote (≤120 chars) and precise source_type: "title", "body", "answer#", or "comment#" (e.g., "answer1", "comment3").
- Use explicit code/config lines or clear recommendations as evidence.
- Misuses in comments count if proposed or endorsed as fixes.

4) Confidence calibration (0-1)
- 0.95-1.00: explicit insecure API/mode/parameter AND endorsed in accepted or top-voted answer.
- 0.80-0.94: clear misuse in code/text; guidance consistent.
- 0.60-0.79: probable misuse but limited context/unclear endorsement.
- <0.60: insufficient evidence → do not report.

5) Do not classify as misuse:
- Theoretical, conceptual, or documentation-level questions

----------------------------
OUTPUT (STRICT JSON)
----------------------------
Rules:
- If "has_misuse" == true → "misuses" MUST be non-empty and "meta.num_misuses" MUST equal its length.
- If "has_misuse" == false → "misuses" MUST be an empty list and "summary" MUST state no misuse found.

{{
  "has_misuse": <true|false>,
  "summary": "Short overall summary of the detected cryptographic misuses found in the discussion.",

  "misuses": [
    {{
      "category": "<WC|PKC|ICV|PKM|PDF|CIB|BRH|IVM|CAI>",
      "subtype": "<Subtype Name>",
      "confidence": 0.xx,
      "evidence": {{
        "source_type": "<title|body|answer#|comment#>",
        "quote": "<exact snippet>"
      }},
      "rationale": "Brief explanation of why this usage represents an insecure or incorrect cryptographic practice."
    }}
    // Add more misuse objects if found
  ],

  "meta": {{
    "post_id": "<unique id>",
    "num_misuses": "<number of objects in the 'misuses' array>",
  }}
}}
"""


def judge():
    return """
You are an **independent security expert** acting as a **judge**
to evaluate the reasoning quality and correctness of an AI model's **cryptographic misuse classification**.

You are given:
1. The **complete Stack Overflow post** (question and answers).
2. **One model output** (in JSON format) containing its cryptographic misuse classification for the post.

Your goal is to **evaluate how well the model output aligns with the rules, logic, and evidence** presented in the post—not to produce a new classification yourself. You must infer the rules and logic the model was trying to follow from the model's output itself and your experience as a security expert.

### Step 1. Evaluation Criteria

Evaluate the model answer according to the following five dimensions, based on the content of the Stack Overflow post:

1.  **Misuse Detection Validity (0-1):**
    * 1 → the `is_misuse` value **correctly reflects** whether the post shows cryptographic misuse.
    * 0.5 → uncertain or weak justification for the decision.
    * 0 → clearly **incorrect misuse judgment**.

2.  **Classification Accuracy Validity (0-1):**
    * 1 → the chosen group, category, and subtype **correctly describe** the misuse (if any).
    * 0.5 → partially correct or overly broad.
    * 0 → incorrect or irrelevant classification.

Post:
{post}

model response
{response}

**Output:** **MUST** be valid JSON and nothing else.

```json
{{
"id": "The post_id from the 'meta' section of the model response",
"misuse_validity":,
"classification_validity":,
"rationale": ["concise bullet 1", "bullet 2"], // maximum 3 
"confidence": "0-1",  // numeric interval
}}
"""
