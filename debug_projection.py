from transformer import parse_recruiter_csv, parse_recruiter_notes, parse_ats_json, merge_partials, project_profile

record = merge_partials([
    parse_recruiter_csv('samples/recruiter.csv'),
    parse_recruiter_notes('samples/notes.txt'),
    parse_ats_json('samples/ats.json')
])
print('skills record:', record.get('skills'))
config = {
    'fields': [
        {'path': 'skills', 'from': 'skills[].name', 'type': 'string[]', 'normalize': 'canonical'}
    ],
    'include_confidence': True,
    'include_provenance': False,
    'on_missing': 'null'
}
print('projected', project_profile(record, config))
