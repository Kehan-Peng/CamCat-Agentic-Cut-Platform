# Real provider contract

This document is the only CamCat provider protocol. Base URL settings contain only the origin or
gateway prefix; clients append the `/v1/...` paths below. A deployment whose upstream API differs
must use an adapter gateway that implements this contract. CamCat does not contain provider-specific
fallbacks.

Every provider implements `GET /health`, accepts bearer authentication, and returns a JSON object.
Calls have explicit timeouts. Only transport failures, HTTP 429, and HTTP 5xx are retried with bounded
exponential backoff; other 4xx responses and invalid payloads fail immediately.

## Qwen3-VL-Embedding-8B

`POST {CAMCAT_EMBEDDING_BASE_URL}/v1/embeddings` uses `multipart/form-data`:

- `model`: exactly `Qwen/Qwen3-VL-Embedding-8B`.
- `dimensions`: exactly `2048`.
- `instruction`: optional retrieval instruction.
- `text`: optional text input.
- `image`: optional original image file part.
- `video`: optional original video clip file part.
- `fps` and `max_frames`: sampling controls sent with video input.

Exactly one of text, image, video, or a supported joint combination is represented as one official
Qwen multimodal input object. The gateway invokes `Qwen3VLEmbedder` once and returns exactly one
embedding:

```json
{"data":[{"embedding":[0.0]}],"model":"Qwen/Qwen3-VL-Embedding-8B"}
```

The vector must contain exactly 2048 non-zero floats. CamCat neither averages multiple vectors nor
renormalizes the provider output. Video ingestion uploads the clip itself; extracted-frame JSON and
caption-only substitutes are non-conformant.

## Qwen3-VL-Reranker-8B

`POST {CAMCAT_RERANKER_BASE_URL}/v1/rerank` accepts JSON with the official multimodal objects intact:

```json
{
  "model": "Qwen/Qwen3-VL-Reranker-8B",
  "query": {"text": "...", "image_base64": "data:image/jpeg;base64,..."},
  "documents": [{"text": "...", "metadata": {"tags": [], "license_name": "..."}}],
  "top_n": 20,
  "instruction": "Rank source clips for the user's requested video edit."
}
```

Text is not discarded when an image is present, and document metadata is not flattened into text.
The response contains one uniquely indexed score per input document:

```json
{"results":[{"index":0,"relevance_score":0.91}]}
```

## Structured chat and direct-video analysis

- `POST {CAMCAT_LLM_BASE_URL}/v1/chat/completions` follows the OpenAI-compatible JSON-object response
  contract used by planning nodes.
- `POST {CAMCAT_LLM_BASE_URL}/v1/analyze` accepts multipart fields `model`, `prompt`, `transcript`,
  `response_schema`, and the original `video` file. The gateway must perform real visual
  understanding and return `{"analysis": ...}` conforming to the supplied JSON Schema. Required
  facts include description, scene, actions, people, composition, tags, event type, risk score, and
  risk labels. ASR text is context, never a visual substitute.

## ASR

`POST {CAMCAT_ASR_BASE_URL}/v1/audio/transcriptions` is OpenAI-compatible multipart transcription.
In addition to `text`, the provider should return timestamped `segments` or `words`; CamCat uses those
timestamps directly for source-aligned subtitles and only asks the planning model for subtitles when
timestamped speech is unavailable.

The official Qwen repository documents the shared text/image/video space, direct video input, and
2048-dimensional MRL output: <https://github.com/QwenLM/Qwen3-VL-Embedding>.
