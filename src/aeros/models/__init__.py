"""All SQLModel tables — imported here so Alembic sees them."""

from aeros.models.audit import AuditLog  # noqa: F401
from aeros.models.award import Award, PurchaseOrder  # noqa: F401
from aeros.models.llm_cache import LLMCache  # noqa: F401
from aeros.models.notification import Notification  # noqa: F401
from aeros.models.observability import (  # noqa: F401
    AgentRunLog,
    ChannelEventLog,
    LLMCallLog,
    PipelineReport,
)
from aeros.models.offer import Offer  # noqa: F401
from aeros.models.organization import Organization  # noqa: F401
from aeros.models.rfx import (  # noqa: F401
    Attachment,
    Message,
    RFxLineItem,
    RFxRun,
    RFxVendor,
    Thread,
)
from aeros.models.sku import SKU, Category  # noqa: F401
from aeros.models.system_setting import SystemSetting  # noqa: F401
from aeros.models.user import User  # noqa: F401
from aeros.models.user_defaults import UserDefaults  # noqa: F401
from aeros.models.vendor import Vendor  # noqa: F401
