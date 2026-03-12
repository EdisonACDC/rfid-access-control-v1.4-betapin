"""Data models for RFID Access Control."""
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any
from datetime import datetime


KEYPAD_ACTIONS = [
    "any",
    "arm_all_zones",
    "arm_day_zones",
    "arm_night_zones",
    "disarm",
]

DEFAULT_ADMIN_PIN = "11061988"


@dataclass
class AccessAction:
    """Represents an action to perform on access."""

    entity_id: str
    service: str
    service_data: Dict[str, Any] = field(default_factory=dict)
    action_name: str = ""
    keypad_action: str = "any"
    delay_before_seconds: int = 0
    delay_after_seconds: int = 0

    def matches_keypad_action(self, keypad_action: str) -> bool:
        """Check if this action should run for the given keypad action."""
        if not self.keypad_action or self.keypad_action == "any":
            return True
        return self.keypad_action.lower() == keypad_action.lower()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AccessAction":
        """Create from dictionary — backward compatible with old delay_seconds."""
        old_delay = int(data.get("delay_seconds", 0))
        return cls(
            entity_id=data.get("entity_id", ""),
            service=data.get("service", ""),
            service_data=data.get("service_data", {}),
            action_name=data.get("action_name", ""),
            keypad_action=data.get("keypad_action", "any"),
            delay_before_seconds=int(data.get("delay_before_seconds", old_delay)),
            delay_after_seconds=int(data.get("delay_after_seconds", 0)),
        )


@dataclass
class AccessUser:
    """Represents an access control user."""

    user_id: str
    user_name: str
    pin: str
    rfid: str
    actions: List[AccessAction] = field(default_factory=list)
    enabled: bool = True
    created_at: str = ""
    last_access: str = ""
    access_count: int = 0

    def __post_init__(self):
        """Post initialization."""
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["actions"] = [a.to_dict() for a in self.actions]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AccessUser":
        """Create from dictionary."""
        actions = [
            AccessAction.from_dict(a) for a in data.get("actions", [])
        ]
        return cls(
            user_id=data.get("user_id", ""),
            user_name=data.get("user_name", ""),
            pin=data.get("pin", ""),
            rfid=data.get("rfid", ""),
            actions=actions,
            enabled=data.get("enabled", True),
            created_at=data.get("created_at", ""),
            last_access=data.get("last_access", ""),
            access_count=data.get("access_count", 0),
        )

    def validate_credentials(self, pin: str = "", rfid: str = "") -> bool:
        """Validate user credentials."""
        if not self.enabled:
            return False

        if pin and rfid:
            return self.pin == pin and self.rfid == rfid

        if pin and not rfid:
            return self.pin == pin

        if rfid and not pin:
            return self.rfid.upper().strip() == rfid.upper().strip()

        return False

    def record_access(self):
        """Record successful access."""
        self.last_access = datetime.now().isoformat()
        self.access_count += 1


class AccessDatabase:
    """Manages user database and system settings."""

    def __init__(self):
        """Initialize database."""
        self.users: Dict[str, AccessUser] = {}
        self.admin_pin: str = DEFAULT_ADMIN_PIN

    def add_user(self, user: AccessUser) -> bool:
        """Add a new user."""
        if user.user_id in self.users:
            return False
        self.users[user.user_id] = user
        return True

    def remove_user(self, user_id: str) -> bool:
        """Remove a user."""
        if user_id not in self.users:
            return False
        del self.users[user_id]
        return True

    def get_user(self, user_id: str) -> AccessUser | None:
        """Get user by ID."""
        return self.users.get(user_id)

    def update_user(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        """Update user."""
        if user_id not in self.users:
            return False
        user = self.users[user_id]
        if "user_name" in user_data:
            user.user_name = user_data["user_name"]
        if "pin" in user_data:
            user.pin = user_data["pin"]
        if "rfid" in user_data:
            user.rfid = user_data["rfid"]
        if "enabled" in user_data:
            user.enabled = user_data["enabled"]
        return True

    def find_user_by_rfid(self, rfid: str) -> AccessUser | None:
        """Find user by RFID (case insensitive)."""
        rfid_upper = rfid.upper().strip()
        for user in self.users.values():
            if user.rfid.upper().strip() == rfid_upper and user.enabled:
                return user
        return None

    def find_user_by_pin(self, pin: str) -> AccessUser | None:
        """Find user by PIN."""
        for user in self.users.values():
            if user.pin == pin and user.enabled:
                return user
        return None

    def find_user_by_credentials(self, pin: str = "", rfid: str = "") -> AccessUser | None:
        """Find user by PIN + RFID."""
        for user in self.users.values():
            if user.validate_credentials(pin=pin, rfid=rfid):
                return user
        return None

    def get_all_users(self) -> List[AccessUser]:
        """Get all users."""
        return list(self.users.values())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary including admin_pin."""
        return {
            "_admin_pin": self.admin_pin,
            "users": {
                user_id: user.to_dict()
                for user_id, user in self.users.items()
            },
        }

    def from_dict(self, data: Dict[str, Any]):
        """Load from dictionary — backward compatible with old flat format."""
        if "users" in data and isinstance(data["users"], dict):
            self.admin_pin = data.get("_admin_pin", DEFAULT_ADMIN_PIN)
            self.users = {
                user_id: AccessUser.from_dict(user_data)
                for user_id, user_data in data["users"].items()
            }
        else:
            self.admin_pin = data.get("_admin_pin", DEFAULT_ADMIN_PIN)
            flat_users = {k: v for k, v in data.items() if not k.startswith("_")}
            self.users = {
                user_id: AccessUser.from_dict(user_data)
                for user_id, user_data in flat_users.items()
            }
