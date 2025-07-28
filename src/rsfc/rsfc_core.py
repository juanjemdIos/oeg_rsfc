from jinja2 import Environment, BaseLoader
from datetime import datetime, timezone
import os
import json
from rsfc.model import assessedSoftware as soft
from rsfc.rsfc_tests import rsfc_tests as rt
from importlib.resources import files
from rsfc.harvesters import somef_harvester as som



def render_template(sw, checks):
    
    print("Rendering assessment...")
    
    data = dict()
    
    data['name'] = sw.software_name
    data['url'] = sw.software_url
    data['version'] = sw.software_version
    data['doi'] = sw.software_id
    data['checks'] = checks
    

    with files("rsfc").joinpath("templates/assessment_schema.json.j2").open("r", encoding="utf-8") as f:
        template_source = f.read()

    env = Environment(loader=BaseLoader(), trim_blocks=True, lstrip_blocks=True)
    template = env.from_string(template_source)

    now = datetime.now(timezone.utc)
    data.setdefault("date", str(now.date()))
    data.setdefault("date_iso", now.replace(microsecond=0).isoformat().replace('+00:00', 'Z'))

    rendered = template.render(**data)
    
    return json.loads(rendered)


def build_assessment(repo_url):
    
    somef = som.SomefExtractor(repo_url)
    somef_data = somef.somef_assessment(repo_url, 0.8)
    sw = soft.AssessedSoftware(repo_url)
    
    print("Assessing repository...")

    checks = [
        rt.test_has_license(somef_data),
        rt.test_license_spdx_compliant(somef_data),
        rt.test_license_info_in_metadata_files(somef_data, repo_url, sw.repo_type, sw.repo_branch),
        rt.test_authors_contribs(somef_data),
        rt.test_authors_orcids(somef_data),
        rt.test_author_roles(repo_url, sw.repo_type, sw.repo_branch),
        rt.test_metadata_exists(somef_data, repo_url, sw.repo_type, sw.repo_branch),
        rt.test_codemeta_exists(repo_url, sw.repo_type, sw.repo_branch),
        rt.test_descriptive_metadata(somef_data),
        rt.test_title_description(somef_data),
        rt.test_has_citation(somef_data),
        rt.test_reference_publication(somef_data, repo_url, sw.repo_type, sw.repo_branch),
        rt.test_software_documentation(somef_data),
        rt.test_readme_exists(somef_data),
        rt.test_contact_support_documentation(somef_data),
        rt.test_installation_instructions(somef_data),
        rt.test_dependencies_declared(somef_data),
        rt.test_dependencies_in_machine_readable_file(somef_data),
        rt.test_dependencies_have_version(somef_data),
        rt.test_has_releases(somef_data),
        rt.test_release_id_and_version(somef_data),
        rt.test_latest_release_consistency(somef_data),
        rt.test_semantic_versioning_standard(somef_data),
        rt.test_version_scheme(somef_data),
        rt.test_metadata_record_in_zenodo_or_software_heritage(somef_data, repo_url, sw.repo_type, sw.repo_branch),
        rt.test_id_presence_and_resolves(somef_data),
        rt.test_id_associated_with_software(somef_data, repo_url, sw.repo_type, sw.repo_branch),
        rt.test_id_proper_schema(somef_data),
        rt.test_identifier_in_readme_citation(somef_data),
        rt.test_identifier_resolves_to_software(somef_data),
        rt.test_presence_of_tests(repo_url, sw.repo_type, sw.repo_branch),
        rt.test_github_action_tests(somef_data),
        rt.test_repository_workflows(somef_data),
        rt.test_is_github_repository(repo_url),
        rt.test_repo_enabled_and_commits(somef_data, repo_url, sw.repo_type, sw.repo_branch),
        rt.test_has_tickets(somef_data),
        rt.test_repo_status(somef_data)
    ]
    
    results = render_template(sw, checks)
    
    print("Saving assessment locally...")
    
    output_path = './outputs/rsfc_assessment.json'

    if os.path.exists(output_path):
        os.remove(output_path)

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=4)
