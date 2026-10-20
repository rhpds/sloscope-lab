#!/usr/bin/env python3
"""Check Showroom navigation, AsciiDoc structure, links, and executable-block syntax."""
from pathlib import Path
import re
import subprocess

root=Path(__file__).resolve().parents[1]
pages=root/'content/modules/ROOT/pages'
nav=(root/'content/modules/ROOT/nav.adoc').read_text()
references=set()
def resolve_xref(target):
    if target.startswith('attachment$'):
        return root/'content/modules/ROOT/attachments'/target.removeprefix('attachment$')
    return pages/target
for path in pages.glob('*.adoc'):
    text=path.read_text()
    if not text.startswith('= '):
        raise SystemExit(f'{path.name}: missing page title')
    if 'include::partial$_attributes.adoc[]' not in text:
        raise SystemExit(f'{path.name}: missing shared attributes')
    if '== Learning objectives' not in text or '== Learning outcomes' not in text:
        raise SystemExit(f'{path.name}: missing objectives/outcomes')
    if path.name not in nav:
        raise SystemExit(f'{path.name}: absent from navigation')
    if text.count('\n----\n') % 2:
        raise SystemExit(f'{path.name}: unbalanced listing blocks')
    if re.search(r'\[source,(?:bash|shell|sh)\]',text):
        raise SystemExit(f'{path.name}: executable blocks need role="execute"')
    if '== References' in text and path.name!='99-conclusion.adoc':
        raise SystemExit(f'{path.name}: consolidate references in conclusion')
    for target in re.findall(r'xref:([^\[#]+)',text):
        if not resolve_xref(target).is_file():
            raise SystemExit(f'{path.name}: broken xref {target}')
    for image,options in re.findall(r'image::([^\[]+)\[([^\]]+)\]',text):
        if not (root/'content/modules/ROOT/assets/images'/image).is_file():
            raise SystemExit(f'{path.name}: missing image {image}')
        if 'link=self' not in options or 'window=blank' not in options:
            raise SystemExit(f'{path.name}: image needs a full-size link {image}')
    for link,label in re.findall(r'link:([^\[]+)\[([^\]]+)\]',text):
        if not label.endswith('^'):
            raise SystemExit(f'{path.name}: external link lacks caret: {link}')
    for block in re.findall(r'\[source,role="execute"\]\n----\n(.*?)\n----',text,re.S):
        result=subprocess.run(['bash','-n'],input=block,text=True,capture_output=True)
        if result.returncode:
            raise SystemExit(f'{path.name}: invalid shell block: {result.stderr}')
    if 'openshift_version' in text:
        references.add('openshift_version')
for target in re.findall(r'xref:([^\[#]+)',nav):
    if not resolve_xref(target).is_file():
        raise SystemExit(f'nav.adoc: broken xref {target}')
ui=(root/'ui-config.yml').read_text()
if 'default_mode: split' not in ui or 'path: /wetty' not in ui or '${DOMAIN}' not in ui:
    raise SystemExit('ui-config.yml: missing terminal/console split-view contract')
print(f'PASS: {len(list(pages.glob("*.adoc")))} pages, navigation/xrefs, shared attributes, objective/outcome sections, external links, and shell syntax')
