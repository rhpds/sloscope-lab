# Compatibility role

The original Publishing House example entry point now delegates to `sloscope_lab`. New callers should use `playbooks/lab.yml` and the documented deploy/validate/teardown inputs. No empty or debug-only deployment is reported as success.
