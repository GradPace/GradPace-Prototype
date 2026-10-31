import re
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

START = '<!-- schema:start -->'
END = '<!-- schema:end -->'
PROJECT_APPS = ('accounts', 'intelligence', 'benchmarks')
ON_DELETE = {
    'CASCADE': 'row deleted',
    'SET_NULL': 'FK set to NULL',
    'PROTECT': 'deletion blocked',
    'SET_DEFAULT': 'FK set to default',
    'DO_NOTHING': 'nothing (DB decides)',
    'RESTRICT': 'deletion blocked',
}


def project_models():
    return [m for app in PROJECT_APPS for m in apps.get_app_config(app).get_models()]


def edge(field):
    """Mermaid cardinality line: target side on the left, FK holder on the right."""
    optional = '|o' if field.null else '||'
    if field.one_to_one:
        return f'{optional}--o|'
    return f'{optional}--o{{'


def build():
    mods = project_models()
    mod_set = set(mods)
    rels, rows, entities = [], [], []

    for m in mods:
        attrs = []
        for f in m._meta.concrete_fields:
            keys = []
            if f.primary_key:
                keys.append('PK')
            if f.is_relation:
                keys.append('FK')
            if f.unique and not f.primary_key:
                keys.append('UK')
            col = f.target_field if f.is_relation else f
            col_type = col.get_internal_type()
            attrs.append(f'        {col_type} {f.attname} {", ".join(keys)}'.rstrip())
        entities.append(f'    {m.__name__} {{\n' + '\n'.join(attrs) + '\n    }')

        for f in m._meta.local_fields + m._meta.local_many_to_many:
            if not f.is_relation or f.related_model not in mod_set:
                continue
            target = f.related_model.__name__
            label = f'{m.__name__}.{f.name}'
            if f.many_to_many:
                rels.append(f'    {m.__name__} }}o--o{{ {target} : "{label}"')
                rows.append((m.__name__, f.name, target, 'many-to-many', 'link row removed'))
                continue
            rels.append(f'    {target} {edge(f)} {m.__name__} : "{label}"')
            kind = 'one-to-one' if f.one_to_one else f'many {m.__name__} to one {target}'
            if f.null:
                kind += ' (optional)'
            rows.append(
                (m.__name__, f.name, target, kind, ON_DELETE[f.remote_field.on_delete.__name__])
            )

    table = [
        '| From (holds the FK column) | Field | Points at | Type | If the target is deleted |',
        '|---|---|---|---|---|',
        *(f'| `{a}` | `{b}` | `{c}` | {d} | {e} |' for a, b, c, d, e in sorted(rows)),
    ]
    diagram = ['```mermaid', 'erDiagram', *sorted(rels), '', *entities, '```']
    return '\n'.join(table), '\n'.join(diagram)


class Command(BaseCommand):
    help = 'Regenerate the FK table and Mermaid ER diagram in docs/schema.md from the models.'

    def add_arguments(self, parser):
        parser.add_argument('--check', action='store_true', help='Fail if schema.md is stale.')

    def handle(self, *args, check=False, **opts):
        path = Path(settings.BASE_DIR) / 'docs' / 'schema.md'
        text = path.read_text()
        if START not in text or END not in text:
            raise CommandError(f'{path} is missing the schema markers.')
        table, diagram = build()
        block = f'{START}\n\n### Foreign keys\n\n{table}\n\n### Diagram\n\n{diagram}\n\n{END}'
        new = re.sub(re.escape(START) + '.*?' + re.escape(END), lambda _: block, text, flags=re.S)
        if check:
            if new != text:
                raise CommandError('docs/schema.md is stale; run `make schema-docs`.')
            return
        path.write_text(new)
        self.stdout.write(f'Updated {path}')
