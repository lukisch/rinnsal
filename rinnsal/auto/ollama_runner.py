# -*- coding: utf-8 -*-
"""
OllamaRunner -- Ollama API Wrapper
====================================

Lokaler LLM-Runner fuer Ollama (qwen3, mistral, etc.).
Kommuniziert direkt mit der Ollama REST API.
Zero external dependencies (nur stdlib).

Author: Lukas Geiger
License: MIT
"""
import json
import re
import urllib.request
import urllib.error
from datetime import datetime


class OllamaRunner:
    """Wrapper um die Ollama REST API fuer automatisierte Aufrufe."""

    def __init__(self, model="qwen3:4b", base_url="http://localhost:11434",
                 timeout=300, temperature=0.7, system_prompt=None):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.temperature = temperature
        self.system_prompt = system_prompt

    def run(self, prompt, **overrides):
        """
        Fuehrt einen Ollama-Aufruf aus.

        Returns:
            dict mit keys: success, output, model, duration_s, eval_count
        """
        model = overrides.get("model", self.model)
        system = overrides.get("system_prompt", self.system_prompt)
        temperature = overrides.get("temperature", self.temperature)
        timeout = overrides.get("timeout", self.timeout)

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }
        if system:
            payload["system"] = system

        start = datetime.now()
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/api/generate",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            duration = (datetime.now() - start).total_seconds()
            response_text = result.get("response", "")

            # Thinking-Tags entfernen falls vorhanden
            if "<think>" in response_text:
                response_text = re.sub(
                    r"<think>.*?</think>\s*", "", response_text, flags=re.DOTALL
                ).strip()

            return {
                "success": True,
                "output": response_text,
                "thinking": result.get("thinking", ""),
                "model": model,
                "duration_s": round(duration, 1),
                "eval_count": result.get("eval_count", 0),
                "prompt_eval_count": result.get("prompt_eval_count", 0),
                "done_reason": result.get("done_reason", ""),
            }
        except urllib.error.URLError as e:
            return {
                "success": False,
                "output": "",
                "error": f"Verbindungsfehler: {e}",
                "model": model,
                "duration_s": round((datetime.now() - start).total_seconds(), 1),
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "model": model,
                "duration_s": round((datetime.now() - start).total_seconds(), 1),
            }

    def chat(self, messages, **overrides):
        """
        Chat-Completion mit Nachrichtenverlauf.

        Args:
            messages: Liste von {"role": "user/assistant/system", "content": "..."}

        Returns:
            dict wie run()
        """
        model = overrides.get("model", self.model)
        temperature = overrides.get("temperature", self.temperature)
        timeout = overrides.get("timeout", self.timeout)

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }

        start = datetime.now()
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/api/chat",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            duration = (datetime.now() - start).total_seconds()
            msg = result.get("message", {})

            return {
                "success": True,
                "output": msg.get("content", ""),
                "role": msg.get("role", "assistant"),
                "model": model,
                "duration_s": round(duration, 1),
                "eval_count": result.get("eval_count", 0),
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "model": model,
                "duration_s": round((datetime.now() - start).total_seconds(), 1),
            }

    def available_models(self):
        """Listet verfuegbare Modelle."""
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            return [m["name"] for m in result.get("models", [])]
        except Exception:
            return []

    def health(self):
        """Prueft ob Ollama erreichbar ist."""
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False
