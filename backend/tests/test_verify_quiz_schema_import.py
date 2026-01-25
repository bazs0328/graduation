import os
import runpy


def test_verify_quiz_schema_script_importable():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    script_path = os.path.join(root_dir, "scripts", "verify_quiz_schema.py")
    module_globals = runpy.run_path(script_path)
    assert "SessionLocal" in module_globals
