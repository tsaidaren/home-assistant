"""Constants for the Tesla Powerwall integration."""

DOMAIN = "powerwall"

POWERWALL_SITE_NAME = "site_name"

POWERWALL_OBJECT = "powerwall"
POWERWALL_COORDINATOR = "coordinator"
POWERWALL_SITE_INFO = "site_info"

POWERWALL_METERS = [
    "solar",
    "site",
    "load",
    "battery",
    "busway",
    "frequency",
    "generator",
]
UPDATE_INTERVAL = 60

POWERWALL_SITE_NAME = "site_name"
POWERWALL_API_METERS = "meters"
POWERWALL_API_CHARGE = "charge"
POWERWALL_API_GRID_STATUS = "grid_status"
POWERWALL_API_SITEMASTER = "sitemaster"
POWERWALL_IP_ADDRESS = "ip"

POWERWALL_GRID_ONLINE = "SystemGridConnected"
POWERWALL_RUNNING_KEY = "running"
