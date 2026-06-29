import json
from transformer import merge_partials, parse_recruiter_csv, parse_recruiter_notes, parse_ats_json, project_profile, profile_to_default_output


def test_merge_and_default_output(tmp_path):
    csv_path = tmp_path / "recruiter.csv"
    csv_path.write_text("name,email,phone,current_company,title\nAlex Johnson,alex.johnson@example.com,415-555-0100,Acme Corp,Senior Data Scientist\n", encoding="utf-8")
    notes_path = tmp_path / "notes.txt"
    notes_path.write_text("Candidate: Alex Johnson\nEmail: alex.johnson@example.com\nPhone: +1 (415) 555-0100\nLocation: San Francisco, CA, USA\nSkills: Python, ML, SQL\n", encoding="utf-8")
    ats_path = tmp_path / "ats.json"
    ats_path.write_text(json.dumps({
        "applicantName": "Alex Johnson",
        "contact": {"emails": ["alex.j@example.com"], "phones": ["(415)555-0100"]},
        "location": "San Francisco, CA, United States",
        "skills": ["Python", "SQL", "Machine Learning"],
    }), encoding="utf-8")

    record = merge_partials([
        parse_recruiter_csv(str(csv_path)),
        parse_recruiter_notes(str(notes_path)),
        parse_ats_json(str(ats_path)),
    ])

    output = profile_to_default_output(record)
    assert output["full_name"] == "Alex Johnson"
    assert "alex.johnson@example.com" in output["emails"]
    assert output["phones"] == ["+14155550100"]
    assert output["location"]["city"] == "San Francisco"
    assert any(skill["name"] == "Python" for skill in output["skills"])
    assert output["overall_confidence"] > 0


def test_custom_projection(tmp_path):
    record = merge_partials([
        parse_recruiter_csv(str(tmp_path / "recruiter.csv")) if (tmp_path / "recruiter.csv").exists() else {
            "full_name": {"value": "Alex Johnson", "confidence": 0.8, "sources": ["test"], "methods": ["csv"]},
            "emails": [{"value": "alex.johnson@example.com", "confidence": 0.8, "sources": ["test"], "methods": ["csv"]}],
            "phones": [{"value": "+14155550100", "confidence": 0.7, "sources": ["test"], "methods": ["csv"]}],
        }
    ])
    config = {
        "fields": [
            {"path": "full_name", "type": "string"},
            {"path": "primary_email", "from": "emails[0]", "type": "string"},
            {"path": "phone", "from": "phones[0]", "type": "string", "normalize": "E164"}
        ],
        "include_confidence": False,
        "include_provenance": False,
        "on_missing": "null"
    }
    projected = project_profile(record, config)
    assert projected["full_name"] == "Alex Johnson"
    assert projected["primary_email"] == "alex.johnson@example.com"
    assert projected["phone"] == "+14155550100"
