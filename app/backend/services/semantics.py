"""Qwen semantics client.

Calls the Modal function directly (no deployed endpoint needed).
Falls back to {} if Modal is unavailable or errors.
Set QWEN_ENDPOINT env var to use a deployed HTTP endpoint instead.
"""
import base64
import os
from dotenv import load_dotenv
load_dotenv()


def analyze_semantics(image_path: str) -> dict:
    endpoint = os.environ.get("QWEN_ENDPOINT")
    print(f"[semantics] QWEN_ENDPOINT={'set: '+endpoint[:30]+'...' if endpoint else 'NOT SET'}")
    if endpoint:
        return _call_endpoint(endpoint, image_path)
    return _call_modal(image_path)


def _call_modal(image_path: str) -> dict:
    try:
        from infra.qwen_endpoint import Model
        img_b64 = base64.b64encode(open(image_path, "rb").read()).decode()
        model = Model()
        result = model.analyze.remote({"image": img_b64})
        if isinstance(result, dict) and "error" not in result:
            return result
        return {}
    except Exception:
        return {}


def _call_endpoint(endpoint: str, image_path: str) -> dict:
    try:
        import httpx
        payload = {"image": base64.b64encode(open(image_path, "rb").read()).decode()}
        resp = httpx.post(endpoint, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}
