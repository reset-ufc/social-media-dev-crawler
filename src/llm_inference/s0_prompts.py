def classify_misuse_and_categories():
    return """
You are a **security expert** specializing in software encryption.
 Given a **complete Stack Overflow post** (title, body, answers, and comments), 
 your task is to identify whether the post contains **cryptographic misuse** and, 
 if so, to **classify and detail** the types of misuse found, adhering strictly to the provided JSON output format.

### Definition of Cryptographic Misuse:
A cryptographic misuse occurs when a developer applies cryptography incorrectly, 
introducing or implying a **real security weakness** in implementation or design.

This includes, but is not limited to:
* Using weak or deprecated algorithms.
* Using insecure modes or parameters.
* Hardcoding keys or secrets.
* Incorrect use of random number generators.
* Insecure padding or truncation in code.
* Omitting authentication or verification steps.

### Classification Rules

1. **Multiple Misuses:**  
   If multiple distinct misuses are found, include one object per misuse inside the `misuses` array.

2. **Group and Category Fields:**  
   - `group` → one of: `"Code-level Misuses"`, `"Design Flaws"`, `"Insecure Architectures"`.  
   - `category` → one acronym from this exact list: `WC`, `CIB`, `BRH`, `PDF`, `ICV`, `PKC`, `IVM`, `PKM`, `CAI`.

3. **Evidence Source:**  
   The `source_type` must be exactly one of: `"title"`, `"body"`, `"answer#<number>"`, `"comment#<number>"`.

4. **Field Values:**  
   - `confidence` must be a float between 0.0 and 1.0 (e.g., `0.85`).  
   - All strings must use **double quotes** only.  
   - Do **not** include comments, explanations, or ellipses (`...`) inside the JSON.

Do not classify as misuse:
- Theoretical, conceptual, or documentation-level questions


5. **Output Validation:**  
   The output must be **strictly valid JSON**, fully parseable without manual fixes.  
   The model must check before outputting that:
   - all brackets/braces are properly closed,  
   - all commas are correctly placed,  
   - and no trailing commas appear.

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

The complete Stack Overflow post:
{post}

**Output:** **MUST** be valid JSON and nothing else. All required fields must be populated. 
The `misuses` array must be empty if `has_misuse` is `false`.

```json
{{
  "has_misuse": <true|false>,
  "summary": "Short overall summary of the detected cryptographic misuses found in the discussion.",

  "misuses": [
    {{
      "group": "<Group Name>",
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
