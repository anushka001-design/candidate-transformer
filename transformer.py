import csv
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import phonenumbers
from dateutil import parser as date_parser


KNOWN_SKILLS = {
    "python": "Python",
    "java": "Java",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "sql": "SQL",
    "data science": "Data Science",
    "machine learning": "Machine Learning",
    "ml": "Machine Learning",
    "devops": "DevOps",
    "recruiting": "Recruiting",
    "ai": "AI",
    "c++": "C++",
}

COUNTRY_MAP = {
    "usa": "US",
    "us": "US",
    "united states": "US",
    "united states of america": "US",
    "canada": "CA",
    "uk": "GB",
    "united kingdom": "GB",
}


def _normalize_text(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    text = value.strip()
    return text if text else None


def _safe_lower(value: Optional[str]) -> Optional[str]:
    return value.lower().strip() if value else None


def normalize_email(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = value.strip()
    match = re.search(r"[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}", value)
    return match.group(0).lower() if match else None


def normalize_phone(value: Optional[str], default_region: str = "US") -> Optional[str]:
    if not value:
        return None
    try:
        parsed = phonenumbers.parse(value, default_region)
        if not phonenumbers.is_valid_number(parsed):
            return None
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        return None


def normalize_date(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        parsed = date_parser.parse(value, default=datetime(1900, 1, 1))
        if parsed.day == 1 and parsed.month == 1 and re.fullmatch(r"\d{4}", value.strip()):
            return parsed.strftime("%Y")
        return parsed.strftime("%Y-%m")
    except (ValueError, TypeError, OverflowError):
        return None


def normalize_country(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    key = value.strip().lower().replace("the ", "")
    return COUNTRY_MAP.get(key, key.upper() if len(key) == 2 else None)


def canonical_skill(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = re.sub(r"[^0-9a-zA-Z+]+", " ", value).strip().lower()
    if not normalized:
        return None
    if normalized in KNOWN_SKILLS:
        return KNOWN_SKILLS[normalized]
    if normalized.title() in KNOWN_SKILLS.values():
        return normalized.title()
    return normalized.title()


def deterministic_id(inputs: List[str]) -> str:
    digest = hashlib.sha1("|".join(inputs).encode("utf-8")).hexdigest()
    return digest[:16]


def _add_scalar(record: Dict[str, Any], key: str, value: Any, confidence: float, source: str, method: str):
    if value is None:
        return
    current = record.get(key)
    if current is None or confidence > current["confidence"]:
        record[key] = {"value": value, "confidence": confidence, "sources": [source], "methods": [method]}
    elif value != current["value"]:
        current["sources"].append(source)
        if method not in current["methods"]:
            current["methods"].append(method)


def _add_list_item(record: Dict[str, Any], key: str, item: Dict[str, Any]):
    if item["value"] is None:
        return
    record.setdefault(key, [])
    existing = next((element for element in record[key] if element["value"] == item["value"]), None)
    if existing:
        existing["confidence"] = max(existing["confidence"], item["confidence"])
        existing["sources"] = list(set(existing["sources"] + item["sources"]))
        existing["methods"] = list(set(existing["methods"] + item["methods"]))
    else:
        record[key].append(item)


def _add_provenance(record: Dict[str, Any], field: str, source: str, method: str, value: Any):
    record.setdefault("provenance", [])
    record["provenance"].append({"field": field, "source": source, "method": method, "value": value})


def _parse_recruiter_row(row: Dict[str, str], source: str) -> Dict[str, Any]:
    partial = {}
    if name := _normalize_text(row.get("name")):
        _add_scalar(partial, "full_name", name, 0.8, source, "csv")
        _add_provenance(partial, "full_name", source, "csv", name)
    if email := normalize_email(row.get("email")):
        _add_list_item(partial, "emails", {"value": email, "confidence": 0.8, "sources": [source], "methods": ["csv"]})
        _add_provenance(partial, "emails", source, "csv", email)
    if phone := normalize_phone(row.get("phone")):
        _add_list_item(partial, "phones", {"value": phone, "confidence": 0.7, "sources": [source], "methods": ["csv"]})
        _add_provenance(partial, "phones", source, "csv", phone)
    if company := _normalize_text(row.get("current_company")):
        _add_scalar(partial, "current_company", company, 0.6, source, "csv")
        _add_provenance(partial, "current_company", source, "csv", company)
    if title := _normalize_text(row.get("title")):
        _add_scalar(partial, "headline", title, 0.6, source, "csv")
        _add_provenance(partial, "headline", source, "csv", title)
    return partial


def parse_recruiter_csv(path: str) -> Dict[str, Any]:
    source = f"recruiter_csv:{Path(path).name}"
    record: Dict[str, Any] = {}
    try:
        with open(path, newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                row_record = _parse_recruiter_row(row, source)
                _merge_partial(record, row_record)
    except FileNotFoundError:
        return {"source_error": f"missing_csv:{path}"}
    except Exception:
        return {"source_error": f"malformed_csv:{path}"}
    return record


def parse_ats_json(path: str) -> Dict[str, Any]:
    source = f"ats_json:{Path(path).name}"
    record: Dict[str, Any] = {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return {"source_error": f"missing_ats:{path}"}
    except Exception:
        return {"source_error": f"malformed_ats:{path}"}

    name = data.get("applicantName") or data.get("name")
    if name := _normalize_text(name):
        _add_scalar(record, "full_name", name, 0.85, source, "json")
        _add_provenance(record, "full_name", source, "json", name)
    emails = data.get("contact", {}).get("emails") if isinstance(data.get("contact"), dict) else None
    if isinstance(emails, list):
        for item in emails:
            if email := normalize_email(item):
                _add_list_item(record, "emails", {"value": email, "confidence": 0.9, "sources": [source], "methods": ["json"]})
                _add_provenance(record, "emails", source, "json", email)
    phones = data.get("contact", {}).get("phones") if isinstance(data.get("contact"), dict) else None
    if isinstance(phones, list):
        for item in phones:
            if phone := normalize_phone(item):
                _add_list_item(record, "phones", {"value": phone, "confidence": 0.85, "sources": [source], "methods": ["json"]})
                _add_provenance(record, "phones", source, "json", phone)
    location = data.get("location")
    if location:
        city, region, country = _parse_location_text(location)
        if city:
            _add_scalar(record, "city", city, 0.7, source, "json")
            _add_provenance(record, "location.city", source, "json", city)
        if region:
            _add_scalar(record, "region", region, 0.7, source, "json")
            _add_provenance(record, "location.region", source, "json", region)
        if country := normalize_country(country or location):
            _add_scalar(record, "country", country, 0.7, source, "json")
            _add_provenance(record, "location.country", source, "json", country)
    if summary := _normalize_text(data.get("summary")):
        _add_scalar(record, "headline", summary, 0.65, source, "json")
        _add_provenance(record, "headline", source, "json", summary)
    for raw_skill in data.get("skills", []) if isinstance(data.get("skills"), list) else []:
        if name := canonical_skill(raw_skill):
            _add_list_item(record, "skills", {"value": name, "confidence": 0.8, "sources": [source], "methods": ["json"]})
            _add_provenance(record, "skills", source, "json", name)
    if education := data.get("education"):
        for item in education if isinstance(education, list) else [education]:
            institution = _normalize_text(item.get("school") or item.get("institution"))
            degree = _normalize_text(item.get("degree"))
            field = _normalize_text(item.get("field"))
            end_year = _normalize_text(str(item.get("endYear") or item.get("end_year") or ""))
            if institution:
                _add_list_item(record, "education", {
                    "institution": institution,
                    "degree": degree,
                    "field": field,
                    "end_year": end_year,
                    "confidence": 0.7,
                    "sources": [source],
                    "methods": ["json"],
                    "value": institution,
                })
                _add_provenance(record, "education", source, "json", institution)
    return record


def _parse_location_text(value: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    piece = value.strip()
    parts = [p.strip() for p in re.split(r"[,;/\\]", piece) if p.strip()]
    city = region = country = None
    if len(parts) >= 1:
        city = _normalize_text(parts[0])
    if len(parts) >= 2:
        region = _normalize_text(parts[1])
    if len(parts) >= 3:
        country = _normalize_text(parts[2])
    return city, region, country


def parse_recruiter_notes(path: str) -> Dict[str, Any]:
    source = f"notes_txt:{Path(path).name}"
    record: Dict[str, Any] = {}
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return {"source_error": f"missing_notes:{path}"}
    except Exception:
        return {"source_error": f"malformed_notes:{path}"}

    emails = set(re.findall(r"[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}", text))
    phones = set(re.findall(r"(?:\+\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})", text))
    raw_location = None
    if m := re.search(r"location[:\s]+([A-Za-z0-9 ,./-]+)", text, re.I):
        raw_location = m.group(1).strip()
    experience_years = None
    if m := re.search(r"(\d+)\+? years? of experience", text, re.I):
        experience_years = float(m.group(1))
    skills = set(re.findall(r"\b(Python|JavaScript|Java|SQL|Machine Learning|DevOps|AI|Data Science|Recruiting)\b", text, re.I))
    title_match = re.search(r"(Senior|Lead|Engineer|Analyst|Manager|Intern|Recruiter)[A-Za-z0-9 /-]*", text)
    if title_match:
        headline = title_match.group(0).strip()
        _add_scalar(record, "headline", headline, 0.7, source, "nlp")
        _add_provenance(record, "headline", source, "nlp", headline)
    for email in emails:
        if normalized := normalize_email(email):
            _add_list_item(record, "emails", {"value": normalized, "confidence": 0.85, "sources": [source], "methods": ["nlp"]})
            _add_provenance(record, "emails", source, "nlp", normalized)
    for phone in phones:
        if normalized := normalize_phone(phone):
            _add_list_item(record, "phones", {"value": normalized, "confidence": 0.75, "sources": [source], "methods": ["nlp"]})
            _add_provenance(record, "phones", source, "nlp", normalized)
    if raw_location:
        city, region, country = _parse_location_text(raw_location)
        if city:
            _add_scalar(record, "city", city, 0.7, source, "nlp")
            _add_provenance(record, "location.city", source, "nlp", city)
        if region:
            _add_scalar(record, "region", region, 0.7, source, "nlp")
            _add_provenance(record, "location.region", source, "nlp", region)
        if country := normalize_country(country or raw_location):
            _add_scalar(record, "country", country, 0.7, source, "nlp")
            _add_provenance(record, "location.country", source, "nlp", country)
    if experience_years is not None:
        _add_scalar(record, "years_experience", experience_years, 0.75, source, "nlp")
        _add_provenance(record, "years_experience", source, "nlp", experience_years)
    for raw_skill in skills:
        if name := canonical_skill(raw_skill):
            _add_list_item(record, "skills", {"value": name, "confidence": 0.8, "sources": [source], "methods": ["nlp"]})
            _add_provenance(record, "skills", source, "nlp", name)
    return record


def _merge_partial(base: Dict[str, Any], incoming: Dict[str, Any]):
    if "source_error" in incoming:
        base.setdefault("source_errors", []).append(incoming["source_error"])
        return
    for key, value in incoming.items():
        if key == "provenance":
            base.setdefault("provenance", []).extend(value)
            continue
        if isinstance(value, dict) and "value" in value:
            _add_scalar(base, key, value["value"], value["confidence"], value["sources"][0], value["methods"][0])
        elif isinstance(value, list):
            for item in value:
                if item.get("value") is not None:
                    _add_list_item(base, key, item)
                else:
                    base.setdefault(key, []).append(item)
        else:
            base[key] = value


def merge_partials(partials: List[Dict[str, Any]]) -> Dict[str, Any]:
    merged: Dict[str, Any] = {}
    for part in partials:
        _merge_partial(merged, part)
    if "candidate_id" not in merged:
        candidate_key = []
        if merged.get("emails"):
            candidate_key.append(merged["emails"][0]["value"])
        if merged.get("full_name"):
            candidate_key.append(merged["full_name"]["value"])
        merged["candidate_id"] = deterministic_id(candidate_key or ["unknown"])
    merged["overall_confidence"] = _compute_overall_confidence(merged)
    return merged


def _compute_overall_confidence(record: Dict[str, Any]) -> float:
    values = []
    for key in ["full_name", "headline", "city", "region", "country", "years_experience"]:
        if field := record.get(key):
            values.append(field["confidence"])
    for key in ["emails", "phones", "skills", "experience", "education"]:
        for item in record.get(key, []):
            values.append(item.get("confidence", 0.0))
    if not values:
        return 0.0
    return round(sum(values) / len(values), 3)


def _resolve_path(data: Any, path: str) -> Any:
    if path == "" or path is None:
        return data
    parts = re.split(r"\.(?![^\[]*\])", path)
    current = data
    for idx, part in enumerate(parts):
        if current is None:
            return None
        if part.endswith("[]"):
            key = part[:-2]
            container = current.get(key) if isinstance(current, dict) else None
            if container is None:
                return None
            results = []
            subpath = ".".join(parts[idx + 1:])
            for item in container:
                if subpath:
                    value = _resolve_path(item, subpath)
                    if isinstance(value, list):
                        results.extend(value)
                    elif value is not None:
                        results.append(value)
                else:
                    results.append(item)
            return results
        match = re.fullmatch(r"([a-zA-Z0-9_]+)\[(\d+)\]", part)
        if match:
            key, item_idx = match.group(1), int(match.group(2))
            container = current.get(key) if isinstance(current, dict) else None
            if isinstance(container, list) and 0 <= item_idx < len(container):
                current = container[item_idx]
            else:
                return None
        else:
            if isinstance(current, dict):
                if part in current:
                    current = current.get(part)
                elif part == "name" and "value" in current:
                    current = current["value"]
                else:
                    return None
            else:
                return None
    return current


def _unwrap_value(value: Any) -> Any:
    if isinstance(value, dict) and "value" in value:
        return value["value"]
    if isinstance(value, list):
        return [_unwrap_value(item) for item in value]
    return value


def _normalize_projection_value(value: Any, normalize: Optional[str]) -> Any:
    if normalize is None or value is None:
        return value
    if normalize == "E164":
        if isinstance(value, list):
            return [normalize_phone(v) for v in value if normalize_phone(v)]
        return normalize_phone(value)
    if normalize == "canonical":
        if isinstance(value, list):
            return [canonical_skill(v) for v in value if canonical_skill(v)]
        return canonical_skill(value)
    return value


def _ensure_type(value: Any, expected_type: str) -> Any:
    if value is None:
        return None
    if expected_type == "string":
        return str(value)
    if expected_type == "string[]" and isinstance(value, list):
        return [str(v) for v in value]
    if expected_type == "number":
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    if expected_type == "number[]" and isinstance(value, list):
        result = []
        for v in value:
            try:
                result.append(float(v))
            except (TypeError, ValueError):
                continue
        return result
    return value


def project_profile(record: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    output: Dict[str, Any] = {}
    fields = config.get("fields")
    include_confidence = config.get("include_confidence", True)
    include_provenance = config.get("include_provenance", True)
    on_missing = config.get("on_missing", "null")

    if not fields:
        output = profile_to_default_output(record)
    else:
        for field in fields:
            path = field["path"]
            source_path = field.get("from", path)
            raw = _resolve_path(record, source_path)
            if raw is None:
                if field.get("required"):
                    raise ValueError(f"Missing required value for {path}")
                if on_missing == "null":
                    output[path] = None
                elif on_missing == "omit":
                    continue
                elif on_missing == "error":
                    raise ValueError(f"Missing required value for {path}")
                continue
            normalized = _normalize_projection_value(_unwrap_value(raw), field.get("normalize"))
            typed = _ensure_type(normalized, field.get("type", "string"))
            if typed is None:
                if field.get("required") or on_missing == "error":
                    raise ValueError(f"Cannot project field {path} as {field.get('type')}")
                if on_missing == "null":
                    output[path] = None
                    continue
                if on_missing == "omit":
                    continue
            output[path] = typed

    if include_confidence is False:
        output = _strip_confidence(output)
    if include_provenance is False and "provenance" in output:
        output.pop("provenance")
    return output


def _strip_confidence(node: Any) -> Any:
    if isinstance(node, list):
        return [_strip_confidence(item) for item in node]
    if isinstance(node, dict):
        return {k: _strip_confidence(v) for k, v in node.items() if k != "confidence"}
    return node


def profile_to_default_output(record: Dict[str, Any]) -> Dict[str, Any]:
    output = {
        "candidate_id": record.get("candidate_id"),
        "full_name": record.get("full_name", {}).get("value"),
        "emails": [email["value"] for email in record.get("emails", [])],
        "phones": [phone["value"] for phone in record.get("phones", [])],
        "location": {
            "city": record.get("city", {}).get("value"),
            "region": record.get("region", {}).get("value"),
            "country": record.get("country", {}).get("value"),
        },
        "links": {
            "linkedin": record.get("linkedin", {}).get("value"),
            "github": record.get("github", {}).get("value"),
            "portfolio": record.get("portfolio", {}).get("value"),
            "other": [link for link in record.get("other_links", []) if link],
        },
        "headline": record.get("headline", {}).get("value"),
        "years_experience": record.get("years_experience", {}).get("value"),
        "skills": [
            {
                "name": skill["value"],
                "confidence": skill["confidence"],
                "sources": skill["sources"],
            }
            for skill in record.get("skills", [])
        ],
        "experience": [
            {
                "company": exp.get("company"),
                "title": exp.get("title"),
                "start": exp.get("start"),
                "end": exp.get("end"),
                "summary": exp.get("summary"),
                "confidence": exp.get("confidence"),
            }
            for exp in record.get("experience", [])
        ],
        "education": [
            {
                "institution": edu.get("institution"),
                "degree": edu.get("degree"),
                "field": edu.get("field"),
                "end_year": edu.get("end_year"),
            }
            for edu in record.get("education", [])
        ],
        "provenance": record.get("provenance", []),
        "overall_confidence": record.get("overall_confidence", 0.0),
    }
    return output
