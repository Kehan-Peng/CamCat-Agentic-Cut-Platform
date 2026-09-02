# Real provider contract

This document is the only CamCat provider protocol. Base URL settings contain only the origin or
gateway prefix; clients append the `/v1/...` paths below. A deployment whose upstream API differs
must use an adapter gateway that implements this contract. CamCat does not contain provider-specific
fallbacks.

Every provider implements `GET /health`, accepts bearer authentication, and returns a JSON object.
Calls have explicit timeouts. Only transport failures, HTTP 429, and HTTP 5xx are retried with bounded
exponential backoff; other 4xx responses and invalid payloads fail immediately.

The default open-source deployment starts `provider-gateway` on the private Compose network. It
adapts this contract to a Bailian workspace host and its hosted models; it does not host model
weights and does not require a local GPU. The mapping is:

- canonical embedding model `Qwen/Qwen3-VL-Embedding-8B` -> Bailian
  `qwen3-vl-embedding`, with `dimension=2048` and `enable_fusion=true`;
- canonical reranker `Qwen/Qwen3-VL-Reranker-8B` -> Bailian `qwen3-vl-rerank`;
- `/v1/chat/completions`, `/v1/analyze`, and `/v1/audio/transcriptions` -> the workspace
  OpenAI-compatible chat-completions endpoint with Qwen VL/ASR payloads.

Because Bailian's hosted embedding and VL APIs accept video URLs, the adapter writes the exact
uploaded video bytes to `temporary/provider-staging/...`, issues a short-lived signed URL, makes
one upstream request, and deletes that staging object in `finally`. Consequently,
`CAMCAT_OBJECT_STORE_PUBLIC_ENDPOINT` must be reachable by Bailian over the Internet. The original
upload remains multipart at the CamCat boundary; no frame extraction or vector averaging occurs.

## Qwen3-VL-Embedding-8B

`POST {CAMCAT_EMBEDDING_BASE_URL}/v1/embeddings` uses `multipart/form-data`:

- `model`: exactly `Qwen/Qwen3-VL-Embedding-8B`.
- `dimensions`: exactly `2048`.
- `instruction`: optional retrieval instruction.
- `text`: optional text input.
- `image`: optional original image file part.
- `video`: optional original video clip file part.
- `fps`: optional Bailian-supported video sampling control in the range 0–1.

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

Bailian accepts exactly one query modality and one modality per document object. The default
adapter expands a canonical mixed request into the Cartesian product of available query modalities
(text/image) and common document modalities (caption/video), verifies that every real call returns
each document index exactly once, and averages all scores by index. It never silently chooses the
image over the text or replaces video with captions. Bailian limits video rerank calls to four
documents, so CamCat batches the bounded candidate set in groups of four. Candidate metadata remains
an application-side sidecar: it is retained for deterministic scoring, evidence, and license display
rather than concatenated into model prose.

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
2048-dimensional MRL output: <https://github.com/QwenLM/Qwen3-VL-Embedding>. The hosted adapter
parameters and input limits follow Alibaba Cloud's official
[multimodal embedding](https://help.aliyun.com/en/model-studio/multimodal-embedding-api-reference)
and [reranking](https://help.aliyun.com/en/model-studio/text-rerank-api) references.
