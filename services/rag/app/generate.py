from typing import Callable

# V5 prompt - cite source plate, honest no-record, no fabrication
PROMPT_TEMPLATE = """You are a fleet management assistant. Answer using ONLY the vehicle profiles provided.
Always cite the exact vehicle plate from the profile. Never invent plates or facts not in the profiles.
If no relevant profile is found, reply exactly: "No record found."

Profiles:
{context}

Question: {question}

Answer:"""


def answer(
    question: str,
    retrieved: list[dict],
    llm: Callable[[str], str],
) -> dict:
    if not retrieved:
        return {"answer": "No record found.", "citations": []}
    context = "\n---\n".join(r["document"] for r in retrieved)
    citations = [
        r["metadata"]["plate"]
        for r in retrieved
        if r.get("metadata", {}).get("plate")
    ]
    prompt = PROMPT_TEMPLATE.format(context=context, question=question)
    response = llm(prompt)
    return {"answer": response, "citations": citations}
