"""Sphinx configuration.

https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

import os
import sys
from pathlib import Path

# backend/docs/conf.py -> backend/ (so `accounts`, `core`, `config` import)
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# dev.py, not the PIPELINE-dispatching config.settings package - building docs
# shouldn't depend on a real Postgres/prod secrets being available.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django  # noqa: E402

django.setup()


project = "GradPace Backend"
copyright = "2025-2026, Team Copper"
author = "Team Copper"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",  # Google/NumPy-style docstrings
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "furo"
html_static_path = ["_static"]

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}
autodoc_member_order = "bysource"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "django": (
        "https://docs.djangoproject.com/en/stable/",
        "https://docs.djangoproject.com/en/stable/_objects/",
    ),
}
