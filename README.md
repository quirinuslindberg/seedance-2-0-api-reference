# Seedance 2.0 API Reference — from $0.053/s (480p): endpoints, fields, errors, OpenAPI

**ByteDance Seedance 2.0 is live on [ArgoLink](https://argolink.io/gh-seedance-2-0-api-reference)**: $0.053, $0.11, $0.28 and $0.58 per second at 480p, 720p, 1080p and 4K, 25% below the official price; Fast from $0.042/s and Mini from $0.026/s. This repo is the reference for its job API: every endpoint, request field and response field, the errors and failure codes, output pixel sizes, and machine-readable files you can test against.

[Model page →](https://argolink.io/en/models/seedance-2.0) · [Endpoints](#endpoints) · [Request](#post-v1videosgenerations) · [Job object](#get-v1videosrequest_id) · [Errors](#errors) · [Output sizes](#output-sizes) · [Pricing](#pricing-and-billing)

| File | What it is |
|---|---|
| [`openapi.yaml`](./openapi.yaml) | OpenAPI 3.1 description of the five endpoints |
| [`schema/seedance-2.0-request.schema.json`](./schema/seedance-2.0-request.schema.json) | JSON Schema (2020-12) of the request body, with the per-model and cross-field rules |
| [`examples/`](./examples) | request bodies for each mode, and sample responses |
| [`validate_request.py`](./validate_request.py) | checks a body against the schema before you spend money |

<sub>Last checked: 2026-10-07 against the [Seedance 2.0 model page](https://argolink.io/en/models/seedance-2.0), the [API docs](https://argolink.io/en/docs) and BytePlus's [video task API](https://docs.byteplus.com/en/docs/modelark/create-video-generation-task-api). Response samples show the documented shape; their IDs and messages are illustrative.</sub>

## Endpoints

Base URL `https://argolink.io`. Every call except the model list needs `Authorization: Bearer <key>`, and status and content calls only answer keys of the user who created the job (anyone else gets 404).

| Method | Path | Success | Purpose |
|---|---|---|---|
| `GET` | `/v1/models` | 200 | public model list (`seedance-2.0`, `seedance-2.0-fast`, `seedance-2.0-mini`, …); no key |
| `POST` | `/v1/videos/generations` | 202 | create a job, returns `request_id` |
| `GET` | `/v1/videos/{request_id}` | 200 | job object: status, progress, usage, error |
| `GET` | `/v1/videos/{request_id}/content` | 200 `video/mp4` | the MP4, Range requests supported |
| `POST` | `/v1/media/uploads` | 200 | signed upload URL for a local image, video or audio file |

## POST /v1/videos/generations

### Request fields

| Field | Type | Default | `seedance-2.0` | `-fast` | `-mini` | Notes |
|---|---|---|---|---|---|---|
| `model` | string | required | ✓ | ✓ | ✓ | |
| `prompt` | string | required | ✓ | ✓ | ✓ | every mode; ≤ 40,000 UTF-8 bytes |
| `duration` | integer | 5 | 4–15 | 4–15 | 4–15 | alias `seconds` |
| `resolution` | string | `720p` | 480p, 720p, 1080p, 4k | 480p, 720p | 480p, 720p | |
| `aspect_ratio` | string | `16:9` | 21:9 16:9 4:3 1:1 3:4 9:16 | same | same | `adaptive` with frames only; alias `ratio` |
| `size` | string | — | `WxH` | `WxH` | `WxH` | replaces resolution + ratio; e.g. `1280x720` |
| `generate_audio` | boolean | `true` | ✓ | ✓ | ✓ | `false`: silent MP4 |
| `start_image` | `{url}` | — | ✓ | ✓ | ✓ | first frame |
| `end_image` | `{url}` | — | ✓ | ✓ | ✓ | needs `start_image` |
| `reference_images` | `[{url}]` | — | ≤ 9 | ≤ 9 | ≤ 9 | |
| `reference_videos` | `[{url}]` | — | ≤ 3 | ≤ 3 | ≤ 3 | seconds are billed |
| `reference_audios` | `[{url}]` | — | ≤ 3 | ≤ 3 | ≤ 3 | needs an image or video too |
| `n` | integer | 1 | 1 | 1 | 1 | one video per request |
| `seed`, `watermark: true` | — | — | ✗ | ✗ | ✗ | 400 |
| `omni_reference_task_type` | — | — | ✗ | ✗ | ✗ | editing exists on `seedance-2.5` only |

Response: `202 Accepted`, `{"request_id": "…"}`. The JSON body must stay under 1 MiB.

### How the mode is chosen

| Fields present | Mode | Ratio rule |
|---|---|---|
| none of the media fields | text to video | fixed ratio; `adaptive` is rejected |
| `start_image` | first frame | `adaptive` (closest of the six ratios to the image) or a fixed ratio that crops it |
| `start_image` + `end_image` | first + last frame | as above; the last frame is fitted to the first |
| any of the three reference lists | reference | fixed ratio |

Frames and reference lists are mutually exclusive. Asset counts over the limit, unknown `@` numbers and out-of-range resolutions or durations are rejected at submission, before anything renders.

### Media

Every `url` is a public `https://` address that downloads without signing in and redirects only to HTTPS. Base64 data, multipart bodies and file IDs are refused.

| Asset | Formats | Size | Length | Other |
|---|---|---|---|---|
| image (`start_image`, `end_image`, `reference_images`) | JPEG, PNG | ≤ 20 MiB | — | |
| `reference_videos` | MP4, MOV | ≤ 50 MB | 2–15 s each, ≤ 15 s total | 200–2160 px per side |
| `reference_audios` | WAV, MP3 | ≤ 15 MB | 2–15 s each, ≤ 15 s total | |

Counts and types are checked on submit; lengths after download, before generation. An asset out of range fails the job with `invalid_input` and nothing is charged.

### Naming assets in the prompt

| Write | Means |
|---|---|
| `@Image 1` | first entry of `reference_images` |
| `@Video 2` | second entry of `reference_videos` |
| `@Audio 1` | first entry of `reference_audios` |

Also recognised: `image 1`, `<image 1>`, `@image1`, and the same words in other languages (`@图片1`, `@imagen 1`). Naming is optional; with `@` or `< >`, a number past the end of its list is a 400. In `input_references`, images, videos and audio are numbered separately in the order they appear.

### Aliases accepted from other APIs

| Canonical | fal name | OpenRouter name |
|---|---|---|
| `start_image` | `image_url` (string) | `frame_images[]` with `"frame_type": "first_frame"` |
| `end_image` | `end_image_url` | `frame_images[]` with `"frame_type": "last_frame"` |
| `reference_images` / `_videos` / `_audios` | `image_urls` / `video_urls` / `audio_urls` | `input_references[]` of type `image_url` / `video_url` / `audio_url` |
| `resolution` + `aspect_ratio` | — | `size` |
| `duration`, `aspect_ratio` | — | `seconds`, `ratio` |

One name per input: two names for the same input, or `frame_images` / `input_references` beside the fields they stand for, is a 400. See [examples/requests/openrouter_aliases.json](./examples/requests/openrouter_aliases.json) and [fal_aliases.json](./examples/requests/fal_aliases.json).

## GET /v1/videos/{request_id}

| Field | When | Meaning |
|---|---|---|
| `request_id`, `model`, `status` | always | `status` is `pending`, `done`, `failed` or `expired` |
| `created_at` | always | submission time, Unix seconds |
| `progress` | pending, done | 0–99 while pending (0 until a forecast exists, held at 99 past it); 100 when done |
| `estimated_seconds_remaining` | pending, once forecast | seconds left |
| `video.url`, `video.duration` | done | download address (needs the same key) and length |
| `usage.output_seconds`, `.reference_video_seconds`, `.billed_seconds` | done | what the job is billed for |
| `error.code`, `.message`, `.retryable`, `.field` | failed | why, and whether resending is safe |

Lifecycle rules: poll every 10–15 s. A job that finds no capacity within 10 minutes fails with `capacity_unavailable`; once rendering starts it waits for the result and gives up after 24 hours with `generation_timeout`. Billing happens once, when `done` is first observed. Samples: [pending](./examples/responses/job_pending.json), [done](./examples/responses/job_done.json), [failed](./examples/responses/job_failed.json).

## GET /v1/videos/{request_id}/content

Streams the MP4 (`video/mp4`, `Range` supported) once the job is `done`. Before that it answers `409 job_video_not_ready`; for a failed job `424 job_failed`. This is the same address as `video.url`.

## POST /v1/media/uploads

```json
{"model": "seedance-2.0", "type": "video", "content_type": "video/mp4", "size_bytes": 7340032}
```

| `type` | Ticket accepts | Seedance 2.0 uses | Ticket size limit |
|---|---|---|---|
| `image` | `image/jpeg`, `image/png`, `image/webp` | JPEG, PNG | 20 MiB |
| `video` | `video/mp4`, `video/quicktime`, `video/webm` | MP4, MOV | 500 MiB per ticket (reference limits still apply) |
| `audio` | `audio/mpeg`, `audio/wav`, `audio/mp4`, `audio/aac` | MP3, WAV | 20 MiB |

The answer holds `upload_url` (PUT the bytes within 15 minutes, with exactly the declared `Content-Type` and no API key), `media_url` (send this; readable for 7 days) and the `upload_expires_at` / `expires_at` timestamps. `size_bytes` must equal the file size. Tickets are free and create no job.

## Errors

HTTP errors share one body: `{"error": {"type", "code", "param", "message"}}`, where `code` is stable and `param` names the field at fault.

| HTTP | `type` | `code` | Charged | Retry? |
|---|---|---|---|---|
| 400 | `invalid_request_error` | `field_invalid`, `json_invalid` | no | after fixing the body |
| 400 | `invalid_request_error` | `request_unsupported` | no | after changing the value named in `message` |
| 401 | `authentication_error` | — | no | with a valid key |
| 402 / 403 | — | — | no | after topping up / with a key that has video access |
| 404 | `not_found_error` | `video_request_not_found` | — | with the right ID and key |
| 409 | `invalid_request_error` | `job_video_not_ready` | — | yes, after the job is done |
| 424 | `invalid_request_error` | `job_failed` | — | no: read the job's `error` |
| 429 | `rate_limit_error` | — | no | when running jobs finish |
| 503 | `overloaded_error` | `no_capacity` | no | after `Retry-After` |
| 503 | `api_error` | — | no | later |

Job failure codes (in the job object, `status: "failed"`, never billed):

| `error.code` | `retryable` | What to do |
|---|---|---|
| `invalid_input` | false | change the input named in `field` |
| `content_policy_violation` | false | change the prompt or the asset in `field` |
| `copyright_violation` | true or false | true: the output tripped it, resend or reword; false: replace the input |
| `generation_failed` | true or false | true: resend; false: outcome unconfirmed, check before resending |
| `generation_timeout` | false | no result after 24 hours |
| `capacity_unavailable` | true | resend later |
| `internal_error` | true | resend |
| `cancelled` | false | — |

## Output sizes

Pixel dimensions per resolution and ratio for the Seedance 2.0 series, from BytePlus's API reference (2026-09-28). ArgoLink's docs give the same 1280×720 and 960×960 at 720p. With `adaptive`, the output takes the ratio closest to the first frame.

| Ratio | 480p | 720p | 1080p (2.0 only) | 4K (2.0 only) |
|---|---|---|---|---|
| 16:9 | 864×496 | 1280×720 | 1920×1080 | 3840×2160 |
| 4:3 | 752×560 | 1112×834 | 1664×1248 | 3326×2494 |
| 1:1 | 640×640 | 960×960 | 1440×1440 | 2880×2880 |
| 3:4 | 560×752 | 834×1112 | 1248×1664 | 2494×3326 |
| 9:16 | 496×864 | 720×1280 | 1080×1920 | 2160×3840 |
| 21:9 | 992×432 | 1470×630 | 2206×946 | 4398×1886 |

BytePlus encodes its 4K output as 10-bit H.265/HEVC; check the codec of a 4K file before relying on browser playback.

## Pricing and billing

| Model | 480p | 720p | 1080p | 4K | Official (BytePlus list) |
|---|---:|---:|---:|---:|---|
| `seedance-2.0` | $0.053 | $0.11 | $0.28 | $0.58 | $0.0703 / $0.1512 / $0.3742 / $0.7776 |
| `seedance-2.0-fast` | $0.042 | $0.091 | — | — | $0.0562 / $0.121 |
| `seedance-2.0-mini` | $0.026 | $0.057 | — | — | $0.0352 / $0.0756 |

<sub>Per output second. ArgoLink rates from the [2.0](https://argolink.io/en/models/seedance-2.0), [Fast](https://argolink.io/en/models/seedance-2.0-fast) and [Mini](https://argolink.io/en/models/seedance-2.0-mini) pages; official figures computed from [BytePlus's token prices](https://docs.byteplus.com/en/docs/modelark/model-pricing) ($7.0/M tokens for 2.0 at 480p–720p, $7.7/M at 1080p, $4.0/M at 4K; $5.6/M Fast; $3.5/M Mini) for a 16:9 clip without video input. All read 2026-10-07.</sub>

```text
cost = rate(model, resolution) × billed_seconds
billed_seconds = output seconds + floor(total seconds of reference videos)
```

Reference images, reference audio and uploads are free; the input mode does not change the rate; a request without `duration` bills 5 s; failed and expired jobs are free. Example: `examples/requests/reference_mixed.json` with a 4.0 s reference video bills 9 + 4 = 13 s × $0.091 = $1.183.

## Validate a body locally

```bash
pip install jsonschema
python validate_request.py examples/requests/*.json
echo '{"model": "seedance-2.0-mini", "prompt": "x", "resolution": "1080p"}' | python validate_request.py -
#  resolution: '1080p' is not one of ['480p', '720p']  (Fast and Mini render 480p and 720p only.)
```

The schema encodes the rules a JSON validator can see; prompt bytes are checked by the script; media length, pixel size and whether a URL downloads are left to the server. Generate a client from [`openapi.yaml`](./openapi.yaml) with any OpenAPI 3.1 generator, or load it into Postman or Insomnia.

## FAQ

**Is `adaptive` allowed for text-to-video?**
No. `adaptive` needs a first frame to adapt to; text and reference requests take one of the six fixed ratios.

**Do Fast and Mini take the same references as 2.0?**
Yes: 9 images, 3 videos, 3 audio clips, 15 together, audio never alone. Only the resolutions (480p and 720p) and the rates differ.

**Which pixel size does `size` produce?**
The short side picks the tier and the shape picks the nearest ratio (within 3%); `1280x720` is 720p 16:9. The output follows the table above, not the exact pixels you sent.

**Is there an endpoint to cancel a job or list my jobs?**
None is documented. `cancelled` exists as a failure code, but no cancel call is published.

**Can I validate against the schema in another language?**
Yes. It is plain JSON Schema 2020-12, so Ajv (JavaScript), `jsonschema` (Python) and most other validators read it.

## Tests

```bash
pip install pytest jsonschema pyyaml openapi-spec-validator
pytest
```

The tests check the schema, every example, the OpenAPI document and the validator's exit codes. No network.

## License

MIT
