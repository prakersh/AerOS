VALID_INTENTS = {
    "draft_rfx",
    "modify_rfx",
    "dispatch_rfx",
    "cancel_rfx",
    "evaluate_offer",
    "compare_offers",
    "award_vendor",
    "reply_to_vendor",
    "upload_document",
    "extract_offer",
    "search_inventory",
    "search_vendors",
    "update_defaults",
    "general_query",
    "greeting",
    "clarification",
}

DANGEROUS_INTENTS = {
    "delete_data",
    "export_all_data",
    "modify_other_user",
    "access_admin",
    "bypass_auth",
    "execute_code",
}


class IntentValidator:
    def validate(self, intent: str, user_role: str) -> tuple[bool, str]:
        """Check if the detected intent is valid for the user's role."""
        intent_lower = intent.lower().strip()

        if intent_lower in DANGEROUS_INTENTS:
            return False, f"Blocked dangerous intent: {intent}"

        if intent_lower not in VALID_INTENTS:
            return False, f"Unknown intent: {intent}"

        role_restrictions: dict[str, set[str]] = {
            "vendor": {
                "draft_rfx",
                "dispatch_rfx",
                "cancel_rfx",
                "award_vendor",
                "compare_offers",
            },
            "buyer": set(),
            "admin": set(),
        }

        blocked = role_restrictions.get(user_role, set())
        if intent_lower in blocked:
            return False, f"Intent '{intent_lower}' not allowed for role '{user_role}'"

        return True, ""
