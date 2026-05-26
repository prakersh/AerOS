"""All SQLModel tables — imported here so Alembic sees them."""

from aeros.models.organization import Organization  # noqa: F401
from aeros.models.user import User  # noqa: F401
from aeros.models.user_defaults import UserDefaults  # noqa: F401
from aeros.models.audit import AuditLog  # noqa: F401
from aeros.models.sku import Category, SKU  # noqa: F401
from aeros.models.vendor import Vendor  # noqa: F401
from aeros.models.rfx import (  # noqa: F401
    RFxRun,
    RFxLineItem,
    RFxVendor,
    Thread,
    Message,
    Attachment,
)
from aeros.models.offer import Offer  # noqa: F401
from aeros.models.award import Award, PurchaseOrder  # noqa: F401
from aeros.models.notification import Notification  # noqa: F401
from aeros.models.llm_cache import LLMCache  # noqa: F401
