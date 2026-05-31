"""Groq (Llama 3.1) recommendation generation with a deterministic stub fallback."""
import json
import logging

from app.config import settings
from app.models import Verdict

logger = logging.getLogger(__name__)

VALID_VERDICTS = {
    Verdict.URGENT_SERVICE,
    Verdict.SCHEDULE_SERVICE,
    Verdict.MONITOR,
    Verdict.SAFE,
}

SYSTEM_PROMPT = """You are a senior predictive-maintenance engineer for industrial \
equipment (hydraulic pumps, motors, valves, fluid conveyance systems).

You are given: (1) a summary of detected sensor anomalies, (2) relevant excerpts from \
the equipment maintenance manual, and (3) an engineer's question.

Respond ONLY with a JSON object of this exact shape:
{
  "verdict": one of "URGENT_SERVICE" | "SCHEDULE_SERVICE" | "MONITOR" | "SAFE",
  "explanation": "clear plain-English reasoning, 2-5 sentences, citing the manual where relevant",
  "citations": [{"source": "manual filename or section", "snippet": "short quote", "page": number-or-null}]
}

Rules:
- Ground your reasoning in the provided manual excerpts. If you cite a fact, it must \
come from the excerpts; never invent manual content.
- If no manual excerpts are provided, set citations to an empty list and reason from \
the anomaly data only.
- URGENT_SERVICE = HIGH-severity anomalies or dangerous trends; SAFE = no meaningful anomalies."""


def _build_user_prompt(question: str, anomaly_summary: str, manual_context: str) -> str:
    parts = ["## Detected anomalies\n" + (anomaly_summary or "No anomalies detected.")]
    if manual_context:
        parts.append("## Manual excerpts\n" + manual_context)
    else:
        parts.append("## Manual excerpts\n(none provided)")
    parts.append("## Engineer question\n" + question)
    return "\n\n".join(parts)


def _stub_recommendation(anomaly_summary: str) -> dict:
    """Deterministic fallback used when no Groq key is set or the call fails."""
    text = (anomaly_summary or "").upper()
    if "HIGH" in text:
        verdict = Verdict.URGENT_SERVICE
        reason = "HIGH-severity anomalies were detected, indicating a likely imminent fault."
    elif "MEDIUM" in text:
        verdict = Verdict.SCHEDULE_SERVICE
        reason = "MEDIUM-severity anomalies suggest degradation; schedule service soon."
    elif "MONITOR" in text:
        verdict = Verdict.MONITOR
        reason = "Low-severity deviations detected; keep monitoring the affected parameters."
    else:
        verdict = Verdict.SAFE
        reason = "No meaningful anomalies were detected in the current data."
    return {
        "verdict": verdict,
        "explanation": f"[stub] {reason} (Set GROQ_API_KEY and LLM_STUB_MODE=false for AI-generated reasoning.)",
        "citations": [],
    }


def _coerce(payload: dict) -> dict:
    verdict = str(payload.get("verdict", "")).upper().strip()
    if verdict not in VALID_VERDICTS:
        verdict = Verdict.MONITOR
    citations = payload.get("citations") or []
    if not isinstance(citations, list):
        citations = []
    return {
        "verdict": verdict,
        "explanation": str(payload.get("explanation", "")).strip() or "No explanation provided.",
        "citations": citations,
    }


def generate_recommendation(
    question: str,
    anomaly_summary: str,
    manual_context: str = "",
    history: list[dict] | None = None,
) -> dict:
    """Return {verdict, explanation, citations}."""
    if settings.llm_stub_mode or not settings.groq_api_key:
        return _stub_recommendation(anomaly_summary)

    try:
        from groq import Groq

        client = Groq(api_key=settings.groq_api_key)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for h in (history or [])[-6:]:
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append(
            {"role": "user", "content": _build_user_prompt(question, anomaly_summary, manual_context)}
        )

        resp = client.chat.completions.create(
            model=settings.groq_model,
            messages=messages,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        payload = json.loads(resp.choices[0].message.content)
        return _coerce(payload)
    except Exception as exc:
        logger.warning("Groq call failed (%s); falling back to stub.", exc)
        result = _stub_recommendation(anomaly_summary)
        result["explanation"] = "[fallback] " + result["explanation"]
        return result
