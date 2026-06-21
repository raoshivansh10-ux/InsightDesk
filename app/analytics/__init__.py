"""Analytics blueprint — dashboard and API routes."""

from flask import Blueprint

analytics_bp = Blueprint('analytics', __name__, url_prefix='/dashboard',
                         template_folder='../templates/dashboard')

from . import routes  # noqa: E402, F401
