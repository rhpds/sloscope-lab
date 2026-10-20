#!/usr/bin/env python3
"""Real optional stdio protocol check using the learner's synthetic artifacts."""
import asyncio
import copy
import json
import os
from pathlib import Path
import sys
import subprocess

if sys.flags.optimize:
    raise RuntimeError("Optimized Python is not supported for learner verification")

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path(os.environ.get('SLOSCOPE_MCP_SOURCE',ROOT/'.lab/mcp-engine')).resolve()

async def main():
    lock=json.loads((ROOT/'mcp.lock.json').read_text())
    actual=subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD'],text=True).strip()
    if actual!=lock['commit']:
        raise RuntimeError('Adapter source differs from mcp.lock.json')
    if subprocess.check_output(['git','-C',str(SOURCE),'status','--porcelain'],text=True).strip():
        raise RuntimeError('Adapter source is modified; use the clean pinned source')
    signal=json.loads((ROOT/'.lab/learner/drift-signal.json').read_text())
    environment=dict(os.environ)
    environment.pop('LLM_BASE_URL',None)
    environment.pop('LLM_API_KEY',None)
    params=StdioServerParameters(command=sys.executable,args=[str(SOURCE/'integrations/mcp_server.py')],env=environment)
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write,read_timeout_seconds=10) as session:
            initialized=await session.initialize()
            assert initialized.server_info.name=='sloscope-evidence-review'
            tools=(await session.list_tools()).tools
            assert {t.name for t in tools}=={'compute_baseline','measure_drift','review_classification','review_proposal'}
            for tool in tools:
                assert tool.annotations.read_only_hint is True
                assert tool.annotations.destructive_hint is False
                assert tool.annotations.open_world_hint is False
                assert tool.annotations.idempotent_hint is True
                assert not set(tool.input_schema['properties']) & {'path','filename','command','token','url'}
            review=await session.call_tool('review_classification',{'signal':signal})
            assert not review.is_error
            assert review.structured_content['status']=='admissible',review.structured_content
            insufficient=copy.deepcopy(signal)
            insufficient['provenance']['coverage_ratio']=.79
            review=await session.call_tool('review_classification',{'signal':insufficient})
            assert not review.is_error
            assert review.structured_content['status']=='abstained',review.structured_content
    print('PASS: discovered 4 bounded tools; real stdio review admitted measured evidence and abstained on low coverage')

if __name__=='__main__':
    asyncio.run(main())
