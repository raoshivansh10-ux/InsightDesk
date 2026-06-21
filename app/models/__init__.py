"""Models package — import all models so SQLAlchemy registers them."""

from .user import User          # noqa: F401
from .dataset import Dataset    # noqa: F401
from .sales import SalesRecord  # noqa: F401
from .customer import Customer  # noqa: F401
from .anomaly import Anomaly    # noqa: F401
from .root_cause import RootCauseReport # noqa: F401
from .forecast import Forecast  # noqa: F401
from .insight import Insight    # noqa: F401
