# app/extractors/llm_parser.py
import os
import json
from app.config import settings

# New OpenAI python client (>=1.0.0)
from openai import OpenAI

# Create a client (it reads API key from environment or from settings)
_client = OpenAI(api_key=settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY"))

EXTRACTION_PROMPT = """
You are a precise parser. Given the payslip text delimited by triple backticks, extract these fields as JSON:
employee_name, employee_code, pan, pay_date (YYYY-MM-DD if possible), month (YYYY-MM), gross_salary, basic, hra, special_allowance, tds, pf_employee, pf_employer, net_pay, components (object of other components).
If a field isn't present use null. ONLY return valid JSON (no commentary).

Here is the payslip text:
```{text}```
"""

def _call_openai_chat(text: str, model: str = "gpt-3.5-turbo", max_tokens: int = 1500):
    """
    Uses the new OpenAI client API to create a chat completion.
    """
    prompt = EXTRACTION_PROMPT.replace("{text}", text)
    resp = _client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=max_tokens,
    )
    # response content lives in resp.choices[0].message.content
    return resp.choices[0].message.content

def parse_with_llm(text: str) -> dict:
    raw = _call_openai_chat(text)
    # Try strict JSON
    try:
        return json.loads(raw)
    except Exception:
        # fallback: find first JSON object substring
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(raw[start:end+1])
        # If still fails, raise so caller can log + continue
        raise ValueError("Failed to parse JSON from LLM output; raw output (truncated):\n" + raw[:1000])
