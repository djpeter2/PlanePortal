import os


def _load_settings_toml(path="settings.toml"):
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                if (value.startswith('"') and value.endswith('"')) or (
                    value.startswith("'") and value.endswith("'")
                ):
                    value = value[1:-1]
                os.environ.setdefault(key, value)
    except FileNotFoundError:
        pass


_load_settings_toml()


def _get_string(name, default=None):
    value = os.getenv(name)
    if value is None:
        return default

    if isinstance(value, str):
        value = value.strip()
    else:
        value = str(value).strip()

    if not value:
        return default
    return value


def _get_int(name, default):
    value = _get_string(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_float(name, default):
    value = _get_string(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _get_bool(name, default=False):
    value = _get_string(name)
    if value is None:
        return default
    return value.lower() in ("1", "true", "yes", "on")


class AppConfig:
    def __init__(self):
        self.opensky_client_id = _get_string("OPENSKY_CLIENT_ID")
        self.opensky_client_secret = _get_string("OPENSKY_CLIENT_SECRET")
        self.home_latitude = _get_float("PLANEPORTAL_HOME_LATITUDE", 0.0)
        self.home_longitude = _get_float("PLANEPORTAL_HOME_LONGITUDE", 0.0)
        self.radius_miles = max(0.5, _get_float("PLANEPORTAL_RADIUS_MILES", 3.0))
        self.refresh_seconds = max(30, _get_int("PLANEPORTAL_REFRESH_SECONDS", 120))
        self.recent_window_minutes = max(
            2, _get_int("PLANEPORTAL_RECENT_WINDOW_MINUTES", 10)
        )
        self.adsb_cache_seconds = max(300, _get_int("PLANEPORTAL_ADSB_CACHE_SECONDS", 1800))
        self.enrichment_limit = max(1, _get_int("PLANEPORTAL_ENRICHMENT_LIMIT", 4))
        self.debug = _get_bool("PLANEPORTAL_DEBUG", False)
        self.fullscreen = _get_bool("PLANEPORTAL_FULLSCREEN", False)

    @property
    def recent_window_seconds(self):
        return self.recent_window_minutes * 60

    @property
    def has_opensky_auth(self):
        return bool(self.opensky_client_id and self.opensky_client_secret)

    def validate(self):
        if self.home_latitude == 0.0 and self.home_longitude == 0.0:
            return "Add watch point coordinates in settings.toml using PLANEPORTAL_HOME_LATITUDE and PLANEPORTAL_HOME_LONGITUDE"
        return None

    def source_label(self):
        if self.has_opensky_auth:
            return "OpenSky authenticated"
        return "OpenSky anonymous"
