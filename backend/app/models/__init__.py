# Import all models here so that:
#  1. Alembic's env.py can import Base.metadata and detect every table.
#  2. SQLAlchemy's relationship() resolver can find all mapped classes.
#
# Order matters: referenced models must be imported before referencing ones
# when using string-based forward references in relationship().

from app.models.developer import Developer, McaFilingStatus  # noqa: F401
from app.models.user import User, RiskAppetite, SubscriptionTier  # noqa: F401
from app.models.project import Project, ProjectType, OcStatus, ReraStatus  # noqa: F401
from app.models.risk_score import RiskScore, RiskBand, ConfidenceLevel  # noqa: F401
from app.models.transaction import Transaction  # noqa: F401
from app.models.complaint import Complaint, ComplaintStatus  # noqa: F401
from app.models.news_item import NewsItem, SentimentLabel, NewsCategory  # noqa: F401
from app.models.alert import ProjectAlert, AlertType, AlertSeverity     # noqa: F401
from app.models.payment import Payment, PaymentStatus, BillingCycle      # noqa: F401

__all__ = [
    # Models
    "Developer",
    "User",
    "Project",
    "RiskScore",
    "Transaction",
    "Complaint",
    "NewsItem",
    "ProjectAlert",
    "Payment",
    # Enums
    "McaFilingStatus",
    "RiskAppetite",
    "SubscriptionTier",
    "ProjectType",
    "OcStatus",
    "ReraStatus",
    "RiskBand",
    "ConfidenceLevel",
    "ComplaintStatus",
    "SentimentLabel",
    "NewsCategory",
    "AlertType",
    "AlertSeverity",
    "PaymentStatus",
    "BillingCycle",
]
