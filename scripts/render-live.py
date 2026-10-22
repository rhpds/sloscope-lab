#!/usr/bin/env python3
"""Render the same scoped live contract used by the Ansible role."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parents[1]/'automation/ansible/roles/sloscope_lab/files/render.py'),run_name='__main__')
