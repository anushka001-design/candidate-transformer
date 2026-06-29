# Multi-Source Candidate Data Transformer
A configurable ETL pipeline that transforms candidate information from multiple structured and unstructured sources into a single, canonical candidate profile with normalization, deduplication, provenance tracking, confidence scoring, and runtime-configurable output schemas.

---

## Overview
Recruitment platforms receive candidate information from multiple sources such as Applicant Tracking Systems (ATS), recruiter spreadsheets, resumes, GitHub profiles, and recruiter notes. These sources often contain inconsistent, incomplete, or conflicting information.

This project solves that problem by building a deterministic and explainable data transformation pipeline that:

- Extracts information from multiple sources.
- Normalizes data into a common format.
- Merges conflicting values using predefined rules.
- Tracks where every value originated.
- Assigns confidence scores.
- Produces a single canonical candidate profile.
- Supports configurable output schemas without changing the source code.
The system is designed to be robust, scalable, and transparent, ensuring that incorrect data is never silently propagated.

---

# Features

- Supports both structured and unstructured data sources
- CSV and JSON parsing
- Resume parsing (PDF/DOCX)
- Recruiter notes processing (TXT)
- Candidate profile normalization
- Phone number normalization (E.164)
- Date normalization (YYYY-MM)
- ISO-3166 country normalization
- Canonical skill mapping
- Entity deduplication
- Conflict resolution
- Provenance tracking
- Confidence scoring
- Runtime configurable output schema
- JSON schema validation
- Graceful error handling
- Command Line Interface (CLI)

---

# Pipeline Architecture

```
                 INPUT SOURCES
 ┌─────────────────────────────────────────────┐
 │ Recruiter CSV                               │
 │ ATS JSON                                    │
 │ Resume (PDF / DOCX)                         │
 │ Recruiter Notes (.txt)                      │
 └─────────────────────────────────────────────┘
                     │
                     ▼
              Source Parsers
                     │
                     ▼
            Information Extraction
                     │
                     ▼
          Data Normalization Layer
                     │
                     ▼
        Candidate Merge & Deduplication
                     │
                     ▼
     Provenance + Confidence Assignment
                     │
                     ▼
        Canonical Candidate Profile
                     │
                     ▼
       Configurable Projection Layer
                     │
                     ▼
          Schema Validation Layer
                     │
                     ▼
               Final JSON Output
```

---

# Project Structure

```
candidate-data-transformer/

│
├── config/
│   ├── default_config.json
│   └── custom_config.json
│
├── data/
│   ├── recruiter.csv
│   ├── ats.json
│   ├── resume.pdf
│   └── recruiter_notes.txt
│
├── parsers/
│   ├── csv_parser.py
│   ├── ats_parser.py
│   ├── resume_parser.py
│   └── notes_parser.py
│
├── normalizer/
│
├── merger/
│
├── projector/
│
├── validator/
│
├── output/
│
├── tests/
│
├── main.py
├── requirements.txt
└── README.md
```

---

# Supported Input Sources
SourceTypeStatusRecruiter CSVStructuredSupportedATS JSONStructuredSupportedResume (PDF)UnstructuredSupportedResume (DOCX)UnstructuredSupportedRecruiter Notes (.txt)UnstructuredSupported
---

# Canonical Output Schema
The pipeline generates a unified candidate profile containing:

- candidate_id
- full_name
- emails
- phones
- location
- links
- headline
- years_experience
- skills
- experience
- education
- provenance
- overall_confidence

---

# Normalization Rules
The following fields are normalized before merging:

FieldNormalizationPhone NumbersE.164DatesYYYY-MMCountryISO-3166 Alpha-2SkillsCanonical Skill DictionaryEmailsLowercaseURLsStandardized Format
---

# Merge Strategy
When multiple sources provide conflicting values, the system follows deterministic merge rules.

Priority order:

1. ATS JSON
2. Recruiter CSV
3. Resume
4. Recruiter Notes
The selected value is based on:

- Source reliability
- Data completeness
- Validation success
- Consistency across sources
No values are guessed.

Missing information is returned as:

- `null`
- omitted
- error
depending on the runtime configuration.

---

# Provenance Tracking
Every field stores information about:

- Source
- Extraction method
- Confidence score
Example:

```
{
  "field": "skills",
  "source": "resume.pdf",
  "method": "Resume Parser"
}
```

---

# Runtime Configuration
The output schema is fully configurable without modifying the pipeline.

Users can:

- Include selected fields
- Rename fields
- Map fields
- Enable or disable confidence scores
- Enable or disable provenance
- Choose missing value behavior
- Apply field-level normalization
Example:

```
{
  "fields": [
    {
      "path": "full_name"
    },
    {
      "path": "primary_email",
      "from": "emails[0]"
    }
  ],
  "include_confidence": true,
  "on_missing": "null"
}
```

---

# Installation
Clone the repository

```
git clone https://github.com/<your-username>/candidate-data-transformer.git
```
Move into the project directory

```
cd candidate-data-transformer
```
Install dependencies

```
pip install -r requirements.txt
```

---

# Running the Project
Default output

```
python main.py \
--csv data/recruiter.csv \
--ats data/ats.json \
--resume data/resume.pdf \
--notes data/recruiter_notes.txt \
--config config/default_config.json
```
Custom output

```
python main.py \
--csv data/recruiter.csv \
--ats data/ats.json \
--resume data/resume.pdf \
--notes data/recruiter_notes.txt \
--config config/custom_config.json
```

---

# Example Output

```
{
    "full_name": "John Doe",
    "emails": [
        "john@example.com"
    ],
    "phones": [
        "+14155552671"
    ],
    "skills": [
        {
            "name": "Python",
            "confidence": 0.97
        },
        {
            "name": "SQL",
            "confidence": 0.94
        }
    ],
    "overall_confidence": 0.95
}
```

---

# Error Handling
The pipeline gracefully handles:

- Missing files
- Empty files
- Corrupted PDF files
- Invalid JSON
- Missing fields
- Invalid phone numbers
- Duplicate candidate information
- Conflicting source values
- Unknown countries
- Unsupported resume formats
The pipeline never crashes because of malformed input.

---

# Testing
Run all tests

```
pytest
```
Tests cover:

- Data extraction
- Phone normalization
- Date normalization
- Skill normalization
- Merge policy
- Schema validation
- Missing source handling

---

# Technologies Used

- Python
- Pandas
- Pydantic
- pdfplumber
- python-docx
- phonenumbers
- pycountry
- dateparser
- JSON
- CSV
- argparse
- pytest
- Git

---

# Future Improvements

- GitHub REST API integration
- LinkedIn API integration
- OCR support for scanned resumes
- LLM-assisted resume parsing
- FastAPI REST API
- Docker containerization
- Batch candidate processing
- Web Dashboard
- Cloud deployment
- CI/CD using GitHub Actions

---

# Author
**Anushka Ghosh**

Engineering Internship Assignment

2026

---

# License
This project is developed for educational and internship evaluation purposes.

