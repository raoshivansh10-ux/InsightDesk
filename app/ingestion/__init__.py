"""Ingestion blueprint — CSV/XLSX upload and data cleaning."""

from flask import Blueprint

ingestion_bp = Blueprint('ingestion', __name__, url_prefix='/datasets',
                         template_folder='../templates/ingestion')

from . import routes  # noqa: E402, F401
