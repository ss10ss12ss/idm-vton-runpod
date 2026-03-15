from __future__ import annotations

import base64
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

import requests
import runpod
from gradio_client import Client, handle_file

HF_SPACE_ID = os.environ.get("IDM_HF_SPACE_ID", "yisol/IDM-VTON")
HF_TOKEN = os.environ.get("HF_TOKEN")
HF_SSL_VERIFY = os.environ.get("HF_SSL_VERIFY", "false").lower() in {"1", "true", "yes"}

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = Client(HF_SPACE_ID, token=HF_TOKEN, ssl_verify=HF_SSL_VERIFY)
    return _client


def decode_b64_to_png(data: str, out_path: Path) -> None:
    payload = data
    if data.startswith("data:"):
        parts = data.split(",", 1)
        if len(parts) == 2:
            payload = parts[1]
    out_path.write_bytes(base64.b64decode(payload))


def extract_path_or_url(item: Any) -> str | None:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        if isinstance(item.get("path"), str):
            return item["path"]
        if isinstance(item.get("url"), str):
            return item["url"]
    return None


def read_bytes_from_src(src: str) -> bytes:
    if src.startswith("http://") or src.startswith("https://"):
        resp = requests.get(src, timeout=120)
        resp.raise_for_status()
        return resp.content
    return Path(src).read_bytes()


def to_b64_data_url(raw: bytes, mime: str = "image/png") -> str:
    return f"data:{mime};base64," + base64.b64encode(raw).decode("utf-8")


def handler(job: dict[str, Any]) -> dict[str, Any]:
    try:
        payload = job.get("input", {})
        person_b64 = payload.get("person_image_base64")
        cloth_b64 = payload.get("cloth_image_base64")

        if not isinstance(person_b64, str) or not person_b64.strip():
            return {"error": "input.person_image_base64 is required"}
        if not isinstance(cloth_b64, str) or not cloth_b64.strip():
            return {"error": "input.cloth_image_base64 is required"}

        garment_description = str(payload.get("garment_description", "sportswear set, long sleeve top and pants"))
        auto_mask = bool(payload.get("auto_mask", True))
        auto_crop = bool(payload.get("auto_crop", False))
        steps = int(payload.get("steps", 30))
        seed = int(payload.get("seed", -1))

        with tempfile.TemporaryDirectory(prefix="idm-runpod-") as td:
            tmp_dir = Path(td)
            person_path = tmp_dir / "person.png"
            cloth_path = tmp_dir / "cloth.png"

            decode_b64_to_png(person_b64, person_path)
            decode_b64_to_png(cloth_b64, cloth_path)

            person_editor = {
                "background": handle_file(str(person_path)),
                "layers": [],
                "composite": None,
            }

            output = get_client().predict(
                person_editor,
                handle_file(str(cloth_path)),
                garment_description,
                auto_mask,
                auto_crop,
                steps,
                seed,
                api_name="/tryon",
            )

            if not isinstance(output, (list, tuple)) or len(output) < 1:
                return {"error": "IDM-VTON output format was unexpected"}

            result_src = extract_path_or_url(output[0])
            masked_src = extract_path_or_url(output[1]) if len(output) > 1 else None

            if not result_src:
                return {"error": "IDM-VTON did not return result image"}

            result_raw = read_bytes_from_src(result_src)
            masked_raw = read_bytes_from_src(masked_src) if masked_src else b""

            return {
                "ok": True,
                "result_image_base64": to_b64_data_url(result_raw),
                "masked_image_base64": to_b64_data_url(masked_raw) if masked_raw else "",
                "engine": "idm-vton-hf-space",
            }
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
