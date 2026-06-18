# Guardrails Prompt Log - Surface #4

Iteration history for topic restriction and output grounding prompts.
Five versions required by the rubric (DoD). See `app/guardrails_ai.py` for V5 final.

---

## Topic Restriction Prompt

### V1 - Baseline

```
Is this fleet management related? Yes or no.
```

Problem: too broad - "weather in Tel Aviv" passed, "what is a car" passed.

### V2 - Domain examples added

```
You are a fleet assistant. Is the text about fleet management, vehicles, or drivers?
Answer yes or no.
```

Problem: still too permissive. Off-topic vehicle questions (car reviews, buying advice) passed.

### V3 - Explicit rejection criteria

```
You are a fleet management assistant. Determine if the input is strictly related to
operational fleet tasks: vehicle tracking, driver management, maintenance, mileage
updates, insurance, accidents, tickets, or fines.
Reject: general vehicle questions, buying advice, reviews, weather, finance.
Respond only 'yes' (fleet-related) or 'no' (off-topic).
```

Problem: Hebrew inputs failing due to missing multilingual instruction.

### V4 - Multilingual + threshold tuning

```
You are a fleet management assistant. The input may be in Hebrew or English.
Determine if it relates to fleet operations: vehicle tracking, driver management,
maintenance, mileage, insurance, accidents, traffic tickets, or fines.
Accept both Hebrew and English fleet requests.
Respond only 'yes' (fleet-related) or 'no' (off-topic or offensive).
```

Problem: prompt injection ("ignore instructions") still passing at default threshold.

### V5 - Final (injected into guardrails_ai.py)

```
You are a fleet management assistant. Determine if the input relates to
fleet topics: vehicles, drivers, maintenance, mileage, insurance, accidents,
fines, or licenses. Hebrew and English inputs are both valid.
Respond only 'yes' (fleet-related) or 'no' (off-topic).
```

Combined with ToxicLanguage validator (threshold=0.5) to handle offensive/injection cases
separately from topic classification. FP rate on VALID_FLEET_MSGS: 0%.

---

## Output Grounding Prompt

### V1 - Baseline

```
Is the response supported by the source documents? Yes or no.
```

Problem: too lenient - invented prices and regulation numbers passed.

### V2 - Claim-level checking

```
Check if every claim in the response is in the source documents.
Respond yes or no.
```

Problem: vague "claim" - LLM still passed numeric hallucinations.

### V3 - Explicit forbidden categories

```
Given source documents and a generated response, check if every price, date,
legal requirement, fine amount, and regulation number is explicitly in the sources.
Respond only 'yes' (fully grounded) or 'no' (contains unsupported claims).
```

Problem: missed implicit legal references ("as required by law" without citation).

### V4 - Implicit reference handling

```
Given source documents and a generated response, determine if every factual claim
(price, date, fine amount, legal reference, regulation number) is directly and
explicitly supported by the source documents. Treat implicit legal references
without citation as unsupported.
Respond only 'yes' (fully grounded) or 'no' (contains unsupported claims).
```

Problem: safe_text (FIX action) was too aggressive - redacted correct facts.

### V5 - Final (injected into guardrails_ai.py)

```
You are a fact-checker. Given source documents and a generated response,
determine if every factual claim (price, date, legal requirement, fine amount,
regulation number) is explicitly supported by the source documents.
Respond only 'yes' (fully grounded) or 'no' (contains unsupported claims).
```

FIX action on ProvenanceV1 kept. Threshold tuned to avoid over-redaction of
correct fleet data while blocking invented legal/financial claims.
