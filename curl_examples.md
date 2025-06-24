# CogView4 API - cURL Examples

## Prompt Optimization API

### Basic Prompt Optimization

```bash
curl -X POST "http://localhost:8000/v1/prompt/optimize" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a cat sitting on a chair",
    "retry_times": 5
  }'
```

### Chinese Prompt Optimization

```bash
curl -X POST "http://localhost:8000/v1/prompt/optimize" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "一只可爱的小猫坐在椅子上",
    "retry_times": 3
  }'
```

### Complex Prompt Optimization

```bash
curl -X POST "http://localhost:8000/v1/prompt/optimize" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "An anime girl with blue hair in a magical forest with glowing butterflies",
    "retry_times": 5
  }'
```

### Expected Response Format

```json
{
  "original_prompt": "a cat sitting on a chair",
  "optimized_prompt": "In this charming scene, a sleek, black cat perches gracefully on a classic wooden armchair...",
  "success": true,
  "message": "Prompt optimized successfully"
}
```

## Image Generation with Optimized Prompt

### Step 1: Optimize the prompt
```bash
OPTIMIZED_PROMPT=$(curl -s -X POST "http://localhost:8000/v1/prompt/optimize" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "a cat sitting on a chair", "retry_times": 5}' | \
  jq -r '.optimized_prompt')
```

### Step 2: Generate image with optimized prompt
```bash
curl -X POST "http://localhost:8000/v1/images/generations" \
  -H "Content-Type: application/json" \
  -d "{
    \"prompt\": \"$OPTIMIZED_PROMPT\",
    \"n\": 1,
    \"size\": \"1024x1024\",
    \"guidance_scale\": 5.0,
    \"num_inference_steps\": 50
  }"
```

## Health Check

```bash
curl -X GET "http://localhost:8000/health"
```

## List Models

```bash
curl -X GET "http://localhost:8000/v1/models"
```

## Status Information

```bash
curl -X GET "http://localhost:8000/status"
``` 