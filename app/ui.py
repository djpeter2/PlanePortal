import math
import sys

import pygame


# Colors as RGB tuples (converted from CircuitPython 0xRRGGBB)
BACKGROUND  = (  7,  19,  31)
SKY_BAND    = ( 14,  34,  49)
CARD        = ( 16,  39,  57)
CARD_ALT    = ( 12,  30,  45)
ACCENT      = ( 45, 181, 163)
ACCENT_DIM  = ( 29, 109, 103)
TEXT        = (240, 247, 249)
TEXT_MUTED  = (149, 169, 181)
WARN        = (243, 190,  78)
ERROR       = (227, 101,  91)
ALT_LOW     = (243, 156,  90)
ALT_MID     = (45,  181, 163)
ALT_HIGH    = (183, 227, 245)

RADAR_WIDTH    = 98
RADAR_HEIGHT   = 70
RADAR_CENTER_X = 49
RADAR_CENTER_Y = 35
RADAR_RADIUS   = 31

BADGE_STATUS_X = 126
BADGE_TREND_X  = 160
BADGE_Y        = 46
BADGE_WIDTH    = 28
BADGE_HEIGHT   = 12
BADGE_TEXT_CY  = 52   # vertical center of badge


def _truncate(text, limit):
    text = text or ""
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "..."


def _wrap_text(text, width, max_lines):
    text = str(text or "")
    if not text:
        return ""

    words = text.split()
    if not words:
        return ""

    lines = []
    current = words[0]
    for word in words[1:]:
        proposal = current + " " + word
        if len(proposal) <= width:
            current = proposal
            continue
        lines.append(current)
        current = word
        if len(lines) >= max_lines - 1:
            break

    if len(lines) < max_lines:
        lines.append(current)

    if len(lines) > max_lines:
        lines = lines[:max_lines]

    if len(lines) == max_lines and len(" ".join(words)) > len(" ".join(lines)):
        lines[-1] = _truncate(lines[-1], max(4, width - 1))

    return "\n".join(lines)


def _distance_label(distance_miles):
    return "{:.1f}MI".format(distance_miles)


def _altitude_label(altitude_ft):
    if altitude_ft is None:
        return "--KFT"
    return "{}KFT".format(max(0, int(round(altitude_ft / 1000.0))))


def _speed_label(speed_kts):
    if speed_kts is None:
        return "--KT"
    return "{}KT".format(speed_kts)


def _heading_label(heading):
    return "HDG{:03d}".format(int(heading) % 360)


def _vertical_label(vertical_rate_fpm):
    if vertical_rate_fpm is None:
        return "VS --"
    return "VS {:+d}".format(int(vertical_rate_fpm))


def _trend_label(vertical_rate_fpm):
    if vertical_rate_fpm is None:
        return "LVL"
    if vertical_rate_fpm > 250:
        return "CLB"
    if vertical_rate_fpm < -250:
        return "DSC"
    return "LVL"


def _altitude_color(altitude_ft):
    if altitude_ft is None:
        return TEXT_MUTED
    if altitude_ft < 12000:
        return ALT_LOW
    if altitude_ft < 28000:
        return ALT_MID
    return ALT_HIGH


def _bearing_to_xy(bearing_degrees, distance_miles, radius_miles):
    if radius_miles <= 0:
        radius_fraction = 0
    else:
        radius_fraction = min(1.0, max(0.0, distance_miles / radius_miles))

    angle = bearing_degrees * math.pi / 180.0
    x_offset = int(round(math.sin(angle) * RADAR_RADIUS * radius_fraction))
    y_offset = int(round(math.cos(angle) * RADAR_RADIUS * radius_fraction))
    return RADAR_CENTER_X + x_offset, RADAR_CENTER_Y - y_offset


def _heading_endpoint(x_pos, y_pos, heading_degrees, length=8):
    angle = heading_degrees * math.pi / 180.0
    x_offset = int(round(math.sin(angle) * length))
    y_offset = int(round(math.cos(angle) * length))
    return x_pos + x_offset, y_pos - y_offset


def _radar_color(altitude_ft):
    if altitude_ft is None:
        return TEXT_MUTED
    if altitude_ft < 12000:
        return ALT_LOW
    if altitude_ft < 28000:
        return ALT_MID
    return ALT_HIGH


def _draw_radar_pixel(surf, x, y, color):
    if 0 <= x < RADAR_WIDTH and 0 <= y < RADAR_HEIGHT:
        surf.set_at((x, y), color)


def _draw_radar_square(surf, cx, cy, radius, color):
    for x in range(cx - radius, cx + radius + 1):
        for y in range(cy - radius, cy + radius + 1):
            _draw_radar_pixel(surf, x, y, color)


def _draw_radar_line(surf, x0, y0, x1, y1, color):
    dx = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0)
    sy = 1 if y0 < y1 else -1
    err = dx + dy

    while True:
        _draw_radar_pixel(surf, x0, y0, color)
        if x0 == x1 and y0 == y1:
            return
        e2 = err * 2
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def _build_radar_surface(snapshot, radius_miles):
    surf = pygame.Surface((RADAR_WIDTH, RADAR_HEIGHT))
    surf.fill(SKY_BAND)

    # Range rings
    for ring_r in (10, 20, 30):
        lo_sq = (ring_r - 1) ** 2
        hi_sq = (ring_r + 1) ** 2
        for x in range(RADAR_WIDTH):
            for y in range(RADAR_HEIGHT):
                d_sq = (x - RADAR_CENTER_X) ** 2 + (y - RADAR_CENTER_Y) ** 2
                if lo_sq <= d_sq <= hi_sq:
                    surf.set_at((x, y), ACCENT_DIM)

    # Crosshairs
    _draw_radar_line(surf, RADAR_CENTER_X - RADAR_RADIUS, RADAR_CENTER_Y,
                     RADAR_CENTER_X + RADAR_RADIUS, RADAR_CENTER_Y, ACCENT_DIM)
    _draw_radar_line(surf, RADAR_CENTER_X, RADAR_CENTER_Y - RADAR_RADIUS,
                     RADAR_CENTER_X, RADAR_CENTER_Y + RADAR_RADIUS, ACCENT_DIM)
    _draw_radar_square(surf, RADAR_CENTER_X, RADAR_CENTER_Y, 1, TEXT_MUTED)

    # North indicator
    _draw_radar_line(surf, RADAR_CENTER_X, 2, RADAR_CENTER_X, 6, TEXT)
    _draw_radar_line(surf, RADAR_CENTER_X - 2, 4, RADAR_CENTER_X + 2, 4, TEXT)

    records = snapshot.get("records") or []
    for record in records[1:]:
        x, y = _bearing_to_xy(record["bearing"], record["distance_miles"], radius_miles)
        color = TEXT_MUTED if not record.get("is_live") else _radar_color(record.get("altitude_ft"))
        _draw_radar_square(surf, x, y, 1, color)

    featured = snapshot.get("featured")
    if featured:
        x, y = _bearing_to_xy(featured["bearing"], featured["distance_miles"], radius_miles)
        ex, ey = _heading_endpoint(x, y, featured["heading"])
        _draw_radar_line(surf, x, y, ex, ey, TEXT)
        _draw_radar_square(surf, x, y, 2, TEXT)
        _draw_radar_square(surf, x, y, 1, _radar_color(featured.get("altitude_ft")))

    return surf


def _build_plane_glyph_surface():
    surf = pygame.Surface((RADAR_WIDTH, RADAR_HEIGHT))
    surf.fill(SKY_BAND)
    # Wings
    pygame.draw.rect(surf, WARN, pygame.Rect(32, 34, 34, 4))
    # Fuselage
    pygame.draw.rect(surf, WARN, pygame.Rect(45, 21, 8, 28))
    # Horizontal stabilizers
    pygame.draw.rect(surf, WARN, pygame.Rect(39, 17, 20, 4))
    pygame.draw.rect(surf, WARN, pygame.Rect(39, 49, 20, 4))
    # Vertical stabilizer base
    pygame.draw.rect(surf, WARN, pygame.Rect(44, 57, 10, 4))
    return surf


class PlanePortalUI:
    FONT_SIZE = 11

    def __init__(self, config):
        self._config = config
        pygame.init()

        flags = pygame.FULLSCREEN if config.fullscreen else 0
        self._screen = pygame.display.set_mode((320, 240), flags)
        pygame.display.set_caption("Plane Portal")
        pygame.mouse.set_visible(False)

        # Try monospace system font; fall back to pygame default
        self._font = pygame.font.SysFont("monospace", self.FONT_SIZE)
        self._font_large = pygame.font.SysFont("monospace", self.FONT_SIZE * 2)
        self._fh = self._font.get_height()
        self._fh_large = self._font_large.get_height()

        self.show_message(
            "Plane Portal",
            "Booting display",
            "Edit settings.toml, then restart",
        )

    # -------------------------------------------------------------------------
    # Internal drawing helpers
    # -------------------------------------------------------------------------

    def _pump(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_q, pygame.K_ESCAPE):
                pygame.quit()
                sys.exit(0)

    def _fill_rect(self, x, y, w, h, color):
        pygame.draw.rect(self._screen, color, pygame.Rect(x, y, w, h))

    def _txt(self, text, color, x, cy, large=False):
        """Render text with x=left, cy=vertical-center (matching CircuitPython label anchor)."""
        font = self._font_large if large else self._font
        fh = self._fh_large if large else self._fh
        surf = font.render(str(text), True, color)
        self._screen.blit(surf, (x, cy - fh // 2))

    def _txt_multiline(self, text, color, x, cy, line_spacing=1.1):
        """Render multi-line text; cy is the center of the first line."""
        if not text:
            return
        lines = text.split("\n")
        step = int(self._fh * line_spacing)
        y = cy
        for line in lines:
            self._txt(line, color, x, y)
            y += step

    def _draw_base(self):
        self._fill_rect(0, 0, 320, 240, BACKGROUND)
        self._fill_rect(0, 0, 320, 80, SKY_BAND)
        self._fill_rect(0, 0, 320, 28, CARD_ALT)
        self._fill_rect(10, 38, 192, 154, CARD)
        self._fill_rect(212, 38, 98, 154, CARD_ALT)
        self._fill_rect(10, 198, 300, 32, CARD_ALT)
        self._fill_rect(18, 52, 98, 70, SKY_BAND)
        self._fill_rect(18, 120, 98, 2, ACCENT)
        self._fill_rect(10, 194, 300, 2, ACCENT_DIM)

    def _draw_badge(self, x, color, text):
        pygame.draw.rect(self._screen, color, pygame.Rect(x, BADGE_Y, BADGE_WIDTH, BADGE_HEIGHT))
        label = _truncate(str(text), 4)
        surf = self._font.render(label, True, CARD_ALT)
        fw = surf.get_width()
        bx = x + max(1, (BADGE_WIDTH - fw) // 2)
        self._screen.blit(surf, (bx, BADGE_TEXT_CY - self._fh // 2))

    def _blit_image(self, surf):
        self._screen.blit(surf, (18, 52))

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def show_message(self, title, body, footer, side_text=None, use_radar=False):
        self._pump()
        self._draw_base()

        if use_radar:
            self._blit_image(_build_radar_surface({"records": [], "featured": None},
                                                  self._config.radius_miles))
        else:
            self._blit_image(_build_plane_glyph_surface())

        self._txt(_truncate(title.upper(), 22), TEXT, 12, 17)
        self._txt(_truncate(body, 24), TEXT_MUTED, 158, 17)
        self._txt("STANDBY", WARN, 18, 48)
        self._draw_badge(BADGE_STATUS_X, WARN, "WAIT")
        self._draw_badge(BADGE_TREND_X, CARD_ALT, "IDLE")

        self._txt(_wrap_text(body, 22, 2), TEXT, 126, 74)
        self._txt(_wrap_text(footer, 22, 2), TEXT_MUTED, 126, 96)

        self._txt(_wrap_text(body, 22, 2), TEXT, 18, 146)
        self._txt_multiline(_wrap_text(footer, 22, 2), TEXT_MUTED, 18, 166)

        self._txt("STATUS", TEXT, 222, 56)
        side = side_text or "Waiting for first\nnearby aircraft"
        self._txt_multiline(_wrap_text(side, 13, 5), TEXT_MUTED, 222, 76)

        self._txt(_truncate(footer, 46), TEXT_MUTED, 18, 216)

        pygame.display.flip()

    def show_refreshing(self, detail, source_label):
        self._pump()
        self._draw_base()
        self._blit_image(_build_plane_glyph_surface())
        self._txt("PLANE PORTAL", TEXT, 12, 17)
        self._txt(_truncate(source_label, 24), TEXT_MUTED, 158, 17)
        self._txt("REFRESH", WARN, 18, 48)
        self._draw_badge(BADGE_STATUS_X, WARN, "SCAN")
        self._draw_badge(BADGE_TREND_X, ACCENT_DIM, "LIVE")
        self._txt("STATUS", TEXT, 222, 56)
        self._txt_multiline(_wrap_text(detail, 13, 5), TEXT_MUTED, 222, 76)
        self._txt(_truncate(detail, 46), WARN, 18, 216)
        pygame.display.flip()

    def render_snapshot(self, snapshot, ip_address, source_label, stale=False, detail=None):
        self._pump()
        featured = snapshot["featured"]

        if featured is None:
            if snapshot.get("has_seen_aircraft"):
                self.show_message(
                    "Quiet Sky",
                    "No aircraft now",
                    "Watching {} miles around watch point".format(self._config.radius_miles),
                    side_text="No aircraft in recent window",
                    use_radar=True,
                )
            else:
                self.show_message(
                    "Quiet Sky",
                    "No planes logged",
                    "Watching {} miles around watch point".format(self._config.radius_miles),
                    side_text="Waiting for first nearby aircraft",
                    use_radar=False,
                )
            return

        self._draw_base()

        # Header
        self._txt("PLANE PORTAL", TEXT, 12, 17)
        self._txt(_truncate("{}  {}".format(source_label, ip_address), 24), TEXT_MUTED, 158, 17)

        # Radar
        self._blit_image(_build_radar_surface(snapshot, self._config.radius_miles))

        # Status line above radar
        status_color = WARN if stale else ACCENT
        self._txt(featured["status_text"], status_color, 18, 48)

        # Badges
        trend = _trend_label(featured["vertical_rate_fpm"])
        self._draw_badge(BADGE_STATUS_X, status_color, featured["status_text"])
        self._draw_badge(BADGE_TREND_X, self._trend_color(featured["vertical_rate_fpm"]), trend)

        # Featured aircraft details (right of radar)
        self._txt(_truncate(featured["callsign"], 6), TEXT, 126, 74, large=True)
        self._txt(_truncate(self._aircraft_line(featured), 14),
                  _altitude_color(featured.get("altitude_ft")), 126, 96)
        self._txt(_truncate(self._route_badge(featured), 16), TEXT, 126, 114)

        # Image badge (ICAO/registration in radar area)
        self._txt(_truncate(self._image_badge_text(featured), 12), TEXT_MUTED, 18, 132)

        # Metrics below radar
        self._txt(_truncate(self._metric_line(featured), 26), TEXT, 18, 146)
        self._txt(_truncate(self._metric_line_secondary(featured), 26), TEXT_MUTED, 18, 166)
        self._txt(_truncate(self._owner_badge(featured), 26), TEXT_MUTED, 18, 184)

        # Side panel
        self._txt("RECENT SKY", TEXT, 222, 56)
        self._txt_multiline(self._side_list_text(snapshot["others"]), TEXT_MUTED, 222, 76)

        # Footer
        footer_text = detail or "{} live, {} recent inside {} mi".format(
            snapshot["live_count"],
            snapshot["recent_count"],
            int(self._config.radius_miles),
        )
        self._txt(_truncate(footer_text, 46), WARN if stale else TEXT_MUTED, 18, 216)

        pygame.display.flip()

    # -------------------------------------------------------------------------
    # Data formatting helpers
    # -------------------------------------------------------------------------

    def _aircraft_line(self, record):
        enrichment = record.get("enrichment") or {}
        aircraft = enrichment.get("aircraft") or {}
        registration = aircraft.get("registration")
        aircraft_type = aircraft.get("type") or aircraft.get("icao_type")
        if registration and aircraft_type:
            return "{}  {}".format(registration, aircraft_type)
        if registration:
            return registration
        if aircraft_type:
            return aircraft_type
        return record["category_name"]

    def _route_line(self, record):
        enrichment = record.get("enrichment") or {}
        flightroute = enrichment.get("flightroute") or {}
        origin = flightroute.get("origin") or {}
        destination = flightroute.get("destination") or {}
        origin_code = origin.get("iata_code") or origin.get("icao_code")
        destination_code = destination.get("iata_code") or destination.get("icao_code")
        if origin_code and destination_code:
            return "{} -> {}".format(origin_code, destination_code)
        return None

    def _metric_line(self, record):
        return "{}  {}  {}".format(
            _distance_label(record["distance_miles"]),
            _altitude_label(record["altitude_ft"]),
            _speed_label(record["speed_kts"]),
        )

    def _metric_line_secondary(self, record):
        return "BRG{:03d}  {}  {}".format(
            record["bearing"],
            _heading_label(record["heading"]),
            _vertical_label(record["vertical_rate_fpm"]),
        )

    def _route_badge(self, record):
        route = self._route_line(record)
        if not route:
            return "NO ROUTE"
        return route.replace(" -> ", ">")

    def _owner_badge(self, record):
        owner = self._owner_line(record)
        if not owner:
            return record.get("category_name") or "Aircraft"
        return _truncate(owner, 20)

    def _trend_color(self, vertical_rate_fpm):
        if vertical_rate_fpm is None:
            return CARD_ALT
        if vertical_rate_fpm > 250:
            return ALT_HIGH
        if vertical_rate_fpm < -250:
            return ALT_LOW
        return TEXT_MUTED

    def _owner_line(self, record):
        enrichment = record.get("enrichment") or {}
        aircraft = enrichment.get("aircraft") or {}
        flightroute = enrichment.get("flightroute") or {}
        airline = flightroute.get("airline") or {}
        if airline.get("name"):
            return airline.get("name")
        if aircraft.get("registered_owner"):
            return aircraft.get("registered_owner")
        if aircraft.get("manufacturer"):
            return aircraft.get("manufacturer")
        return None

    def _image_badge_text(self, record):
        enrichment = record.get("enrichment") or {}
        aircraft = enrichment.get("aircraft") or {}
        if aircraft.get("registration"):
            return aircraft.get("registration")
        return record["icao24"].upper()

    def _side_list_text(self, records):
        if not records:
            return "No other nearby\naircraft in the\nrecent window"

        lines = []
        for record in records:
            route = self._route_badge(record)
            lines.append(
                "{} {}\n{} {}\n{}".format(
                    record["status_text"][0],
                    _distance_label(record["distance_miles"]),
                    _truncate(record["callsign"], 6),
                    _altitude_label(record["altitude_ft"]),
                    _truncate(route, 12),
                )
            )
        return "\n".join(lines)
