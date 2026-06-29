# Candidate Transformer

A small CLI-based data transformer for multi-source candidate profiles.

## What it does

- Ingests structured and unstructured candidate sources
- Normalizes emails, phones, dates, skills, and countries
- Merges conflicting values with confidence and provenance
- Produces a canonical profile and custom projected output via runtime config

## Install

1. Create a Python environment.
2. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Run the pipeline

Generate default canonical output:

```bash
python main.py --csv samples/recruiter.csv --notes samples/notes.txt --ats samples/ats.json --output results/default_output.json
```

Generate a custom projection from config:

```bash
python main.py --csv samples/recruiter.csv --notes samples/notes.txt --ats samples/ats.json --config configs/custom_profile.json --output results/custom_output.json
```

## Sample files

- `samples/recruiter.csv` — recruiter export with name, email, phone, company, title
- `samples/notes.txt` — unstructured recruiter notes
- `samples/ats.json` — ATS JSON blob with candidate profile fields
- `configs/custom_profile.json` — custom output projection config

## Tests

Run:

```bash
pytest
```
