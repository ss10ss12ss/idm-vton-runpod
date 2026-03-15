# runpod_idm_worker

Runpod Serverless worker for IDM-VTON request handling.

## Files
- `Dockerfile`
- `requirements.txt`
- `handler.py`

## Input JSON (`/run`)

```json
{
  "input": {
    "person_image_base64": "data:image/png;base64,...",
    "cloth_image_base64": "data:image/png;base64,...",
    "garment_description": "white long-sleeve shirt",
    "auto_mask": true,
    "auto_crop": false,
    "steps": 30,
    "seed": -1
  }
}
```

## Output JSON

```json
{
  "ok": true,
  "result_image_base64": "data:image/png;base64,...",
  "masked_image_base64": "data:image/png;base64,...",
  "engine": "idm-vton-hf-space"
}
```

## Env Vars
- `HF_TOKEN` (optional)
- `HF_SSL_VERIFY` (`true` or `false`, default `false`)
- `IDM_HF_SPACE_ID` (default `yisol/IDM-VTON`)
