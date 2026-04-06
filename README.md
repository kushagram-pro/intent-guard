# Phase 1: Gemini Intent Parser

This project is complete through Phase 1: converting messy financial instructions into structured intent before any action is considered.

## What Phase 1 includes

- Gemini-powered intent parsing
- Multi-intent extraction from a single user instruction
- Confidence scoring per intent
- Ambiguity detection
- Risk level output
- Safe handling for vague or malformed model responses
- CLI output formatted as readable JSON

## Output schema

```json
{
  "intents": [
    {
      "type": "monitor",
      "stock": "XYZ",
      "condition": "",
      "confidence": 0.93
    }
  ],
  "ambiguous": false,
  "risk_level": "low"
}
```

## Setup

1. Create a `.env` file:

```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the CLI:

```bash
python app.py
```

## Example

Input:

```text
Watch this stock XYZ and buy it whenever the situation is good
```

Expected behavior:

- Extract `monitor` and `buy` as separate intents
- Mark the request as ambiguous
- Preserve the vague buy condition for downstream enforcement

## Notes

- The parser uses Gemini with model fallback logic so hardcoded model-name failures are less likely.
- If Gemini returns malformed JSON, the app falls back to a safe ambiguous response.
- Trading is not assumed unless clearly implied in the prompt.
