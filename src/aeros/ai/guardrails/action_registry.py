from dataclasses import dataclass, field


@dataclass
class AllowedAction:
    name: str
    description: str
    requires_confirmation: bool = False
    allowed_roles: set[str] = field(default_factory=lambda: {"buyer", "vendor", "admin"})


ALLOWED_ACTIONS: dict[str, AllowedAction] = {
    "create_rfx": AllowedAction(
        "create_rfx",
        "Create a new RFx/RFQ",
        requires_confirmation=True,
        allowed_roles={"buyer", "admin"},
    ),
    "dispatch_rfx": AllowedAction(
        "dispatch_rfx",
        "Send RFx to vendors",
        requires_confirmation=True,
        allowed_roles={"buyer", "admin"},
    ),
    "cancel_rfx": AllowedAction(
        "cancel_rfx",
        "Cancel an active RFx",
        requires_confirmation=True,
        allowed_roles={"buyer", "admin"},
    ),
    "award_vendor": AllowedAction(
        "award_vendor",
        "Award PO to vendor(s)",
        requires_confirmation=True,
        allowed_roles={"buyer", "admin"},
    ),
    "send_message": AllowedAction("send_message", "Send chat message"),
    "upload_file": AllowedAction("upload_file", "Upload a document"),
    "extract_offer": AllowedAction("extract_offer", "Extract offer from document"),
    "search_inventory": AllowedAction("search_inventory", "Search inventory catalog"),
    "search_vendors": AllowedAction("search_vendors", "Search vendor directory"),
    "update_defaults": AllowedAction(
        "update_defaults",
        "Update user default terms",
        allowed_roles={"buyer", "admin"},
    ),
    "decline_rfx": AllowedAction(
        "decline_rfx",
        "Decline an RFx invitation",
        allowed_roles={"vendor"},
    ),
    "reply_to_rfx": AllowedAction(
        "reply_to_rfx",
        "Reply to an RFx thread",
        allowed_roles={"vendor"},
    ),
}


class ActionRegistry:
    def __init__(self, actions: dict[str, AllowedAction] | None = None) -> None:
        self.actions = actions or ALLOWED_ACTIONS

    def is_allowed(self, action_name: str, user_role: str) -> tuple[bool, str]:
        action = self.actions.get(action_name)
        if not action:
            return False, f"Unknown action: {action_name}"
        if user_role not in action.allowed_roles:
            return False, f"Action '{action_name}' not allowed for role '{user_role}'"
        return True, ""

    def requires_confirmation(self, action_name: str) -> bool:
        action = self.actions.get(action_name)
        return action.requires_confirmation if action else True
