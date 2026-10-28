# Structured Extraction using LLM

Async FastAPI service that converts unstructured job postings into validated Pydantic schemas using an LLM. I built an evaluation harness over hand-labelled postings, with retry and validation handling baked in. It is containerised and designed to run in AWS ECS.

## Project overview

This project is a simple but practical extraction pipeline: take a raw job description, pass it through a model, validate the result, and return structured data in a predictable schema.

The main API endpoint is `/structure`. It accepts a job description and returns a JSON object containing structured fields such as title, company, salary, location, remote policy, and required/desirable skills.

## API Design

The `/structure` endpoint is intentionally a minimal POST API. It accepts a single `job_description` value because the extraction is driven by one source of truth: the raw job posting text. That keeps the request contract simple, easy to call from a browser form, a CLI, or another service, and avoids exposing fields that are redundant or already present in the job description.

The response is deliberately returned as a plain JSON object matching the extraction schema, rather than a wrapper or raw model object. That makes it easy to serialize, inspect, and pass into other parts of the app or a frontend. I kept the route itself thin and simple: it sits on top of the extraction logic rather than trying to do extra orchestration or response shaping.

The design also includes validation at two layers. The request is constrained with a Pydantic model so malformed payloads fail early, and the model output is validated against the same schema plus grounding checks to stop hallucinated values from being accepted. That gives a clean API contract while still adding a safety layer for quality.

## LLM Lessons

I used Claude Haiku 5.5 because it is the cheapest model that still works for this task. The work is not especially reasoning-heavy; it is mostly structured extraction and validation, so speed and cost mattered more than a large reasoning model.

The main challenge was reliability. I had to make sure the response came back as valid JSON and could be parsed into a dict cleanly. It worked for short job descriptions, but not always consistently for longer or noisier ones. My original system prompt outlined the JSON structure and instructions, and the docs recommended either strict tools or a Pydantic output format.

I wanted to add a validation loop so hallucinations would not slip through. There are two parts to that:

### Pydantic validation

A Pydantic model validates the shape and types of the output. It is used both when the LLM response is parsed and again when validating the final object. This prevents invalid structures and allows null values where they are appropriate, which is important for fields like salary and company when the data is not explicitly present.

### Grounding checks

Grounding checks ensure values in the output actually appear in the input and were not invented. This is especially important for salary figures and company names, where a model can confidently hallucinate details. To keep those checks effective, the error is fed back into the recursive retry loop so the function can retry with the same prompt and a clearer failure signal.

I also had to tighten the prompt to stop the model inferring required skills that were not explicitly listed. Manual testing showed the pattern was working, but I wanted a structured way to evaluate it.

## Testing and Evaluation

I am aware of the evaluation frameworks that already exist, but I built this one from scratch to fit the problem. The tests are split into challenge tests and evaluation tests.

Since the app makes a lot of model calls, I used async to keep the runner efficient.

### Challenge testing

I used the same structure as the golden dataset but adjusted inputs to target specific failure modes I considered important. Examples include:
- “Competitive” salary with no numeric figure, so salary fields should be null
- prompt injection attempts, where the output should ignore embedded instructions
- German text with values like `60.000`, which should still parse correctly

#### What I learned from challenge testing

- I only wanted to test specific things, so I omitted certain fields from some challenge cases rather than making them full job-level assertions.
- ExtractionError was raised when full stops were used as thousands separators and the grounding check stripped the punctuation incorrectly. That required a change to the grounding logic.
- I wanted the challenge cases to be strong must-pass checks, so I ran each case 5 times instead of just once.

### Evaluation testing

Challenge testing is meant to catch known traps. Evaluation testing is meant to give a score over a broader set of real job descriptions.

The basic flow is:
- build a golden dataset of job inputs and expected outputs
- run each input through the structure function
- compare the actual output against the expected output with a deterministic judge
- measure overall accuracy and field-level performance

I used a deterministic judge because the task is very specific: the model is asked not to infer skills, so an exact comparison and structured validation make sense. It is also cheap and fast.

The golden dataset is built from real job listings rather than synthetic examples. The goal is to measure how the extractor performs on realistic text, not just toy examples.

The evaluation harness returns an overall percentage accuracy plus F1 scores for skill fields. F1 is a combination of precision and recall. An F1 score of 1 means both precision and recall are perfect, so all predicted values were correct and all expected values were captured.

#### Learnings / how I improved the function

- Pass/fail is not always the right metric. Skill fields are lists, so a strict match can be too harsh. A better metric is F1, which balances precision and recall.
- Some skills were being inferred from the description rather than extracted exactly from the text. I tightened the prompt to prevent that.
- An unexpected failure case showed up when the model returned “basic SQL” instead of “SQL”. I considered “basic” to be a descriptor rather than part of the actual skill, so I updated the prompt and added a new test case.

## Next steps

This works well. I would like to extend the project to estimate my fit for each job and highlight any gaps, so I can triage applications more effectively and avoid wasting time on roles that are a poor match.