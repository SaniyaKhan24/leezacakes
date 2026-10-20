from drf_spectacular.openapi import AutoSchema


class AppTagAutoSchema(AutoSchema):
    """Group operations by the application owning the versioned API path."""

    PATH_TAGS = {
        "accounts": "Accounts",
        "catalog": "Catalog",
        "customization": "Customization",
        "cart": "Cart",
        "orders": "Orders",
        "payments": "Payments",
        "notifications": "Notifications",
        "search": "Search",
    }

    def get_tags(self):
        parts = self.path.strip("/").split("/")
        app = parts[2] if len(parts) > 2 and parts[:2] == ["api", "v1"] else "common"
        return [self.PATH_TAGS.get(app, "Common")]
