"""The skill catalog: the list students pick their skills from.

It's every skill that appears in at least one job's benchmark, so anything
a student picks can count toward a readiness score. The `name` is the exact
O*NET name and is what gets saved on the student's Skill row - that way it
matches the benchmark exactly, with no guessing. `label` is just for display.
"""

from collections import defaultdict

from intelligence.models import Job

from .job_benchmark import build_job_benchmark

# O*NET's names are precise but clunky. Display-only - never saved.
DISPLAY_LABELS = {
    'Amazon Web Services AWS software': 'AWS',
    'Atlassian JIRA': 'Jira',
    'Border Gateway Protocol BGP': 'BGP',
    'Cascading style sheets CSS': 'CSS',
    'Enterprise application integration EAI software': 'Enterprise application integration (EAI)',
    'Extensible markup language XML': 'XML',
    'Google Angular': 'Angular',
    'Hypertext markup language HTML': 'HTML',
    'IBM Terraform': 'Terraform',
    'Jenkins CI': 'Jenkins',
    'Learning management system LMS': 'Learning management systems (LMS)',
    'MITRE ATT&CK software': 'MITRE ATT&CK',
    'Microsoft Azure software': 'Microsoft Azure',
    'Microsoft Office software': 'Microsoft Office',
    'Microsoft SQL Server Integration Services SSIS': 'SSIS',
    'Microsoft Visual Basic for Applications VBA': 'VBA',
    'Oracle Java': 'Java',
    'PCI Express PCIe': 'PCIe',
    'SAP software': 'SAP',
    'Salesforce software': 'Salesforce',
    'Simulation program with integrated circuit emphasis SPICE': 'SPICE',
    'StataCorp Stata': 'Stata',
    'Structured query language SQL': 'SQL',
    'The MathWorks MATLAB': 'MATLAB',
    'Tool command language Tcl': 'Tcl',
    'Very high speed integrated circuit VHSIC hardware description language VHDL simulation '
    'software': 'VHDL',
}


def label_for(name):
    return DISPLAY_LABELS.get(name, name)


def skill_catalog(jobs=None):
    """[{name, label, skill_type, job_count, demand}], most useful first.

    jobs: which jobs' benchmarks to draw from - default every national job.
    Pass one job to get just the skills that count toward that job's score.

    job_count is how many of those jobs' benchmarks include the skill, and
    demand is its highest weight in any of them (0-1). Sorted by job_count,
    then demand - so for a single job, the most in-demand skills come first,
    and across all jobs, broadly useful ones do."""
    if jobs is None:
        jobs = Job.objects.filter(area='National')

    jobs_needing = defaultdict(set)
    skill_types = {}
    demand = defaultdict(float)
    for job in jobs:
        for skill in build_job_benchmark(job).skills:
            jobs_needing[skill.name].add(job.pk)
            skill_types[skill.name] = skill.skill_type
            demand[skill.name] = max(demand[skill.name], skill.weight)

    catalog = [
        {
            'name': name,
            'label': label_for(name),
            'skill_type': skill_types[name],
            'job_count': len(job_ids),
            'demand': round(demand[name], 3),
        }
        for name, job_ids in jobs_needing.items()
    ]
    catalog.sort(key=lambda s: (-s['job_count'], -s['demand'], s['label'].lower()))
    return catalog
