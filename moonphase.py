#!/usr/bin/env python3
"""Moon phase menu bar app — chart + sky info side by side."""

import io
import math
import threading
from datetime import datetime, timezone

import ephem
import objc
import AppKit
import CoreLocation

# ── Constants ─────────────────────────────────────────────────────────────────

SIGNS = [
    (0,   "♈", "Aries"),       (30,  "♉", "Taurus"),
    (60,  "♊", "Gemini"),      (90,  "♋", "Cancer"),
    (120, "♌", "Leo"),         (150, "♍", "Virgo"),
    (180, "♎", "Libra"),       (210, "♏", "Scorpio"),
    (240, "♐", "Sagittarius"), (270, "♑", "Capricorn"),
    (300, "♒", "Aquarius"),    (330, "♓", "Pisces"),
]

SIGN_COLORS = [
    "#c0392b", "#6d4c41", "#1565c0", "#6a1b9a",
    "#c0392b", "#6d4c41", "#1565c0", "#6a1b9a",
    "#c0392b", "#6d4c41", "#1565c0", "#6a1b9a",
]

PLANETS = [
    ("☉", "Sun",     ephem.Sun),
    ("☽", "Moon",    ephem.Moon),
    ("☿", "Mercury", ephem.Mercury),
    ("♀", "Venus",   ephem.Venus),
    ("♂", "Mars",    ephem.Mars),
    ("♃", "Jupiter", ephem.Jupiter),
    ("♄", "Saturn",  ephem.Saturn),
    ("♅", "Uranus",  ephem.Uranus),
    ("♆", "Neptune", ephem.Neptune),
]

PHASE_MAP = [
    (0,   "🌑", "New Moon"),
    (22,  "🌒", "Waxing Crescent"),
    (68,  "🌓", "First Quarter"),
    (112, "🌔", "Waxing Gibbous"),
    (158, "🌕", "Full Moon"),
    (202, "🌖", "Waning Gibbous"),
    (248, "🌗", "Last Quarter"),
    (292, "🌘", "Waning Crescent"),
    (338, "🌑", "New Moon"),
]

ASPECT_DEFS = [
    (0,   8, "#e74c3c", "☌"),
    (60,  6, "#2ecc71", "⚹"),
    (90,  7, "#e74c3c", "□"),
    (120, 8, "#2ecc71", "△"),
    (150, 3, "#95a5a6", "⚻"),
    (180, 8, "#e74c3c", "☍"),
]

PLANET_COLORS = {
    "Sun":     "#f39c12",
    "Moon":    "#bdc3c7",
    "Mercury": "#95a5a6",
    "Venus":   "#e91e63",
    "Mars":    "#e74c3c",
    "Jupiter": "#3498db",
    "Saturn":  "#c0a060",
    "Uranus":  "#1abc9c",
    "Neptune": "#9b59b6",
}

BG_COLOR = (13/255, 13/255, 26/255)


# ── Location manager ──────────────────────────────────────────────────────────

class LocationManager(CoreLocation.NSObject):
    on_update = None

    def init(self):
        self = objc.super(LocationManager, self).init()
        self._mgr = CoreLocation.CLLocationManager.alloc().init()
        self._mgr.setDelegate_(self)
        self._mgr.setDesiredAccuracy_(CoreLocation.kCLLocationAccuracyThreeKilometers)
        self.lat = None
        self.lon = None
        return self

    def request(self):
        status = CoreLocation.CLLocationManager.authorizationStatus()
        if status in (3, 4):
            self._mgr.startUpdatingLocation()
        elif status == 0:
            self._mgr.requestWhenInUseAuthorization()

    def locationManagerDidChangeAuthorization_(self, mgr):
        if mgr.authorizationStatus() in (3, 4):
            mgr.startUpdatingLocation()

    def locationManager_didUpdateLocations_(self, mgr, locations):
        coord = locations.lastObject().coordinate()
        self.lat, self.lon = coord.latitude, coord.longitude
        mgr.stopUpdatingLocation()
        if callable(self.on_update):
            self.on_update(self.lat, self.lon)

    def locationManager_didFailWithError_(self, mgr, error):
        pass


# ── Astronomy ─────────────────────────────────────────────────────────────────

def zodiac(ecl_lon_rad):
    deg = math.degrees(ecl_lon_rad) % 360
    idx = int(deg // 30)
    return SIGNS[idx][1], SIGNS[idx][2], deg % 30


def to_local_hhmm(ephem_date):
    dt = ephem.Date(ephem_date).datetime().replace(tzinfo=timezone.utc)
    return dt.astimezone().strftime("%H:%M")


def moon_phase(when=None):
    now = when if when is not None else ephem.now()
    sun = ephem.Sun(); sun.compute(now)
    moon = ephem.Moon(); moon.compute(now)
    sun_lon  = math.degrees(ephem.Ecliptic(sun,  epoch=now).lon) % 360
    moon_lon = math.degrees(ephem.Ecliptic(moon, epoch=now).lon) % 360
    phase_angle = (moon_lon - sun_lon) % 360
    emoji, name = PHASE_MAP[0][1], PHASE_MAP[0][2]
    for thr, e, n in PHASE_MAP:
        if phase_angle >= thr:
            emoji, name = e, n
        else:
            break
    return emoji, name, moon.phase, float(ephem.next_full_moon(now) - now)


def moon_riseset(lat, lon, when=None):
    obs = ephem.Observer()
    obs.lat, obs.lon = str(lat), str(lon)
    t = when if when is not None else ephem.now()
    obs.horizon, obs.date = "-0:34", t
    moon = ephem.Moon()
    try:
        return to_local_hhmm(obs.next_rising(moon)), to_local_hhmm(obs.next_setting(moon))
    except ephem.CircumpolarError:
        return "–", "–"


def sky_positions(when=None):
    now = when if when is not None else ephem.now()
    rows = []
    for glyph, name, Body in PLANETS:
        body = Body(); body.compute(now)
        sym, sign, deg = zodiac(ephem.Ecliptic(body, epoch=now).lon)
        rows.append((glyph, name, sym, sign, deg))
    return rows


def compute_angles(lat, lon, when=None):
    obs = ephem.Observer()
    t = when if when is not None else ephem.now()
    obs.lat, obs.lon, obs.date = str(lat), str(lon), t
    lst = float(obs.sidereal_time())
    lat_r = math.radians(lat)
    eps = math.radians(23.4392911)
    asc = math.degrees(math.atan2(
        math.cos(lst),
        -math.sin(lst) * math.cos(eps) - math.tan(lat_r) * math.sin(eps)
    )) % 360
    mc = math.degrees(math.atan2(math.tan(lst), math.cos(eps))) % 360
    return asc, mc


def planet_lons(when=None):
    now = when if when is not None else ephem.now()
    result = []
    for glyph, name, Body in PLANETS:
        body = Body(); body.compute(now)
        lon = math.degrees(ephem.Ecliptic(body, epoch=now).lon) % 360
        result.append((name, glyph, lon))
    return result


def when_from_offset_days(offset_days):
    return ephem.Date(ephem.now() + float(offset_days))


# d / w / m: slider in native units → offset in days
AVG_DAYS_PER_MONTH = 365.2422 / 12.0
TF_DAY = 0
TF_WEEK = 1
TF_MONTH = 2

# (min, max) slider units, tick count
TIME_SLIDER = {
    TF_DAY:  (-7.0, 7.0, 15),
    TF_WEEK: (-4.0, 4.0, 9),
    TF_MONTH: (-3.0, 3.0, 7),
}


def offset_days_from_timeframe_unit(tf, slider_value):
    v = float(slider_value)
    if tf == TF_WEEK:
        return v * 7.0
    if tf == TF_MONTH:
        return v * AVG_DAYS_PER_MONTH
    return v


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _slider_value_for_offset_days(tf, offset_days):
    o = float(offset_days)
    lo, hi, _ = TIME_SLIDER[tf]
    if tf == TF_WEEK:
        return _clamp(o / 7.0, lo, hi)
    if tf == TF_MONTH:
        return _clamp(o / AVG_DAYS_PER_MONTH, lo, hi)
    return _clamp(o, lo, hi)


def time_offset_caption(tf, slider_value):
    s = float(slider_value)
    if abs(s) < 0.02:
        return "Now"
    if tf == TF_WEEK:
        r = round(s * 2) / 2.0
        if abs(s - r) < 0.04:
            return f"{r:+.0f}w"
        return f"{s:+.1f}w"
    if tf == TF_MONTH:
        r = round(s, 1)
        return f"{r:+.1f}m"
    r = round(s)
    if abs(s - r) < 0.02:
        return f"{r:+d}d"
    return f"{s:+.1f}d"


# ── Chart ─────────────────────────────────────────────────────────────────────

def _ephem_local_str(when):
    dt = ephem.Date(when).datetime().replace(tzinfo=timezone.utc)
    return dt.astimezone().strftime("%Y-%m-%d  %H:%M  %Z")


def build_chart(lat, lon, when=None, figsize=7.0):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    t = when if when is not None else ephem.now()
    asc, mc = compute_angles(lat, lon, t)
    planets = planet_lons(t)

    BG, FG = "#0d0d1a", "#e8e8ff"
    GRID, ACCENT, FONT = "#2a2a4a", "#7c6fa0", "Apple Symbols"

    f_in = max(float(figsize), 0.1)
    sc = f_in / 7.0
    def fs(n):
        return n * sc
    def lwx(n):
        return n * sc

    fig = plt.figure(figsize=(f_in, f_in), facecolor=BG)
    ax  = fig.add_subplot(111, projection="polar", facecolor=BG)
    ax.set_theta_zero_location("W")
    ax.set_theta_direction(-1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    theta_full = np.linspace(0, 2 * math.pi, 720)

    def ct(lon_deg):
        return math.radians((lon_deg - asc) % 360)

    # Zodiac ring
    for i, (_, sym, _) in enumerate(SIGNS):
        start = math.radians((i * 30 - asc) % 360)
        thetas = np.linspace(start, start + math.radians(30), 90)
        ax.fill_between(thetas, 0.83, 1.0, color=SIGN_COLORS[i], alpha=0.35, linewidth=0)
        ax.plot([start, start], [0.83, 1.0], color=GRID, lw=lwx(0.7))
        mid = start + math.radians(15)
        ax.text(mid, 0.915, sym, ha="center", va="center",
                color=BG, fontsize=fs(13), fontweight="bold", fontfamily=FONT, zorder=3)
        ax.text(mid, 0.915, sym, ha="center", va="center",
                color=FG, fontsize=fs(11), fontweight="bold", fontfamily=FONT, zorder=4)

    for r, lwa in [(1.0, 1.8), (0.83, 1.8), (0.73, 0.8)]:
        ax.plot(theta_full, [r] * len(theta_full), color=ACCENT, lw=lwx(lwa))

    for h in range(12):
        angle = math.radians(h * 30)
        ax.plot([angle, angle], [0, 0.83],
                color=ACCENT if h % 3 == 0 else GRID,
                lw=lwx(1.3) if h % 3 == 0 else lwx(0.5))

    for angle, color, label in [
        (0,                            "#f39c12", "AC"),
        (ct((asc + 180) % 360),        "#f39c12", "DC"),
        (ct(mc),                       "#3498db", "MC"),
        (ct((mc  + 180) % 360),        "#3498db", "IC"),
    ]:
        ax.plot([angle, angle], [0, 0.83], color=color, lw=lwx(1.8), zorder=5)
        ax.text(angle, 0.78, label, ha="center", va="center",
                color=color, fontsize=fs(7), fontweight="bold", fontfamily=FONT, zorder=6)

    # Aspect lines (Cartesian overlay)
    ax2 = fig.add_axes(ax.get_position(), frameon=False)
    ax2.set_xlim(-1, 1); ax2.set_ylim(-1, 1)
    ax2.set_aspect("equal"); ax2.axis("off")

    def to_xy(r, theta):
        return -r * math.cos(theta), r * math.sin(theta)

    for i, (n1, _, l1) in enumerate(planets):
        for j, (n2, _, l2) in enumerate(planets):
            if j <= i:
                continue
            diff = abs(l1 - l2) % 360
            if diff > 180:
                diff = 360 - diff
            for ang, orb, color, _ in ASPECT_DEFS:
                if abs(diff - ang) <= orb:
                    ax2.plot(list(to_xy(0.40, ct(l1))), list(to_xy(0.40, ct(l2))),
                             color=color, lw=lwx(0.8), alpha=0.45)
                    break

    # Planet placement (5 bands)
    R_BANDS, MIN_SEP = [0.52, 0.59, 0.66, 0.73, 0.79], math.radians(8)
    lons_sorted = sorted((lon_deg, glyph, name) for name, glyph, lon_deg in planets)
    placed = []
    for lon_deg, glyph, pname in lons_sorted:
        th = ct(lon_deg)
        chosen_r = R_BANDS[-1]
        for band in R_BANDS:
            if not any(
                band == pr and min(abs(th - pt), 2*math.pi - abs(th - pt)) < MIN_SEP
                for pt, pr in placed
            ):
                chosen_r = band
                break
        placed.append((th, chosen_r))
        col = PLANET_COLORS.get(pname, FG)
        sym, _, deg_in_sign = zodiac(math.radians(lon_deg))
        ax.plot([th], [0.826], "o",
                markersize=max(2.0, min(6.0, 3.0 * sc)), color=col, zorder=7)
        ax.plot([th, th], [0.816, chosen_r + 0.034], color=col, lw=lwx(0.6), alpha=0.5)
        ax.text(th, chosen_r, f"{glyph}\n{sym}{deg_in_sign:.0f}°",
                ha="center", va="center", color=col,
                fontsize=fs(8), fontweight="bold", fontfamily=FONT, zorder=8,
                bbox=dict(
                    boxstyle=f"round,pad={0.15 * sc:.2f}", facecolor=BG,
                    edgecolor=col, linewidth=lwx(0.7), alpha=0.92))

    fig.text(0.5, 0.01, _ephem_local_str(t),
             ha="center", color=ACCENT, fontsize=fs(7), fontfamily=FONT)
    fig.subplots_adjust(left=0.04, right=0.96, top=0.96, bottom=0.04)
    return fig


def chart_to_nsimage(lat, lon, dpi=90, when=None, figsize=7.0):
    import matplotlib.pyplot as plt
    fig = build_chart(lat, lon, when, figsize=figsize)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    data = buf.read()
    ns_data = AppKit.NSData.dataWithBytes_length_(data, len(data))
    return AppKit.NSImage.alloc().initWithData_(ns_data)


# ── Sky panel view (chart left | info right) ──────────────────────────────────

CHART_PX = 363
INFO_PX  = 200
PANEL_FIG = 7.0
PANEL_DPI = 90
PAD      = 10
SLIDER_H = 30
SLIDER_TOP_GAP = 8
TIME_CONTROL_ROW_H = 26
TIME_MID_GAP = 6
# Separate window: larger matplot figure and pixel density, wider info column
EXPAND_FIG = 9.0
EXPAND_DPI = 120
EXPAND_INNER = 10
# Bottom strip (d/w/m, Now) + gap + slider row, same as menu
EXPAND_CONTROLS_H = float(
    TIME_CONTROL_ROW_H + TIME_MID_GAP + SLIDER_H + SLIDER_TOP_GAP
)
# Window content: pad + [chart|Scroll/summary] + pad + controls
EXPAND_BODY_MIN = 400.0
EXPAND_W = 900.0
EXPAND_H = 2.0 * EXPAND_INNER + EXPAND_CONTROLS_H + EXPAND_BODY_MIN
EXPAND_MIN_SPLIT = 0.50
EXPAND_MAX_SPLIT = 0.70
PANEL_W  = PAD + CHART_PX + PAD + 1 + PAD + INFO_PX + PAD
PANEL_H = (
    CHART_PX
    + 2 * PAD
    + SLIDER_TOP_GAP
    + SLIDER_H
    + TIME_MID_GAP
    + TIME_CONTROL_ROW_H
)


def _nscolor(hex_str, alpha=1.0):
    r = int(hex_str[1:3], 16) / 255
    g = int(hex_str[3:5], 16) / 255
    b = int(hex_str[5:7], 16) / 255
    return AppKit.NSColor.colorWithRed_green_blue_alpha_(r, g, b, alpha)


def _font(size, bold=False):
    try:
        w = AppKit.NSFontWeightSemibold if bold else AppKit.NSFontWeightRegular
        return AppKit.NSFont.monospacedSystemFontOfSize_weight_(size, w)
    except Exception:
        return AppKit.NSFont.fontWithName_size_(
            "Menlo-Bold" if bold else "Menlo-Regular", size
        )


class SkyPanelView(AppKit.NSView):

    def init(self):
        frame = AppKit.NSMakeRect(0, 0, PANEL_W, PANEL_H)
        self = objc.super(SkyPanelView, self).initWithFrame_(frame)
        if self is None:
            return None

        y_tf = float(PAD)
        y_sli = y_tf + float(TIME_CONTROL_ROW_H) + float(TIME_MID_GAP)
        y_chart = y_sli + float(SLIDER_H) + float(SLIDER_TOP_GAP)

        # d / w / m + Now (target wired from AppController)
        seg_w = 116.0
        now_w = 50.0
        self._tf_seg = AppKit.NSSegmentedControl.alloc().initWithFrame_(
            AppKit.NSMakeRect(float(PAD), y_tf, seg_w, 24.0)
        )
        self._tf_seg.setSegmentCount_(3)
        for i, lab in enumerate(["d", "w", "m"]):
            self._tf_seg.setLabel_forSegment_(lab, i)
        self._tf_seg.setSelected_forSegment_(True, 0)
        _seg_style = getattr(
            AppKit, "NSSegmentStyleTexturedSquare", 2
        )
        self._tf_seg.setSegmentStyle_(_seg_style)

        self._now_btn = AppKit.NSButton.alloc().initWithFrame_(
            AppKit.NSMakeRect(float(PAD) + seg_w + 8.0, y_tf + 1.0, now_w, 22.0)
        )
        self._now_btn.setTitle_("Now")
        self._now_btn.setButtonType_(
            getattr(AppKit, "NSButtonTypeMomentaryLight", 0)
        )
        self._now_btn.setBezelStyle_(getattr(AppKit, "NSBezelStyleRounded", 1))
        if hasattr(AppKit, "NSControlSizeSmall"):
            self._now_btn.setControlSize_(AppKit.NSControlSizeSmall)

        ex_x = float(PANEL_W) - float(PAD) - 52.0
        self._expand_btn = AppKit.NSButton.alloc().initWithFrame_(
            AppKit.NSMakeRect(ex_x, y_tf + 1.0, 50.0, 22.0)
        )
        self._expand_btn.setTitle_("⤢")
        self._expand_btn.setButtonType_(
            getattr(AppKit, "NSButtonTypeMomentaryLight", 0)
        )
        self._expand_btn.setBezelStyle_(getattr(AppKit, "NSBezelStyleRounded", 1))
        self._expand_btn.setFont_(_font(10, True))
        if hasattr(self._expand_btn, "setToolTip_"):
            self._expand_btn.setToolTip_(
                "Open astral chart in a larger window"
            )
        self._day_label = AppKit.NSTextField.alloc().initWithFrame_(
            AppKit.NSMakeRect(0, 0, 0, 0)
        )
        self._day_label.setStringValue_("Now")
        self._day_label.setBezeled_(False)
        self._day_label.setDrawsBackground_(False)
        self._day_label.setEditable_(False)
        self._day_label.setSelectable_(False)
        self._day_label.setFont_(_font(10, True))
        self._day_label.setTextColor_(_nscolor("#7c6fa0"))
        self._day_label.setAlignment_(AppKit.NSTextAlignmentRight)

        label_w = 64.0
        slider_w = PANEL_W - 2 * PAD - label_w - 8.0
        self._day_slider = AppKit.NSSlider.alloc().initWithFrame_(
            AppKit.NSMakeRect(
                float(PAD), y_sli, slider_w, 22.0
            )
        )
        self._apply_timeframe_to_slider(TF_DAY, 0.0)
        self._day_slider.setAllowsTickMarkValuesOnly_(False)
        self._day_slider.setContinuous_(True)
        self._day_label.setFrame_(
            AppKit.NSMakeRect(
                float(PAD) + slider_w + 8.0,
                y_sli,
                label_w,
                22.0
            )
        )
        self._chart_iv = AppKit.NSImageView.alloc().initWithFrame_(
            AppKit.NSMakeRect(PAD, y_chart, CHART_PX, CHART_PX)
        )
        self._chart_iv.setImageScaling_(AppKit.NSImageScaleProportionallyUpOrDown)
        self.addSubview_(self._chart_iv)

        # Divider
        div = AppKit.NSBox.alloc().initWithFrame_(
            AppKit.NSMakeRect(PAD + CHART_PX + PAD, y_chart, 1, CHART_PX)
        )
        div.setBoxType_(AppKit.NSBoxSeparator)
        self.addSubview_(div)

        # Text view (right)
        info_x = PAD + CHART_PX + PAD + 1 + PAD
        self._tv = AppKit.NSTextView.alloc().initWithFrame_(
            AppKit.NSMakeRect(info_x, y_chart, INFO_PX, CHART_PX)
        )
        self._tv.setEditable_(False)
        self._tv.setSelectable_(False)
        self._tv.setDrawsBackground_(False)
        self._tv.setRichText_(True)
        self.addSubview_(self._tv)

        self.addSubview_(self._day_slider)
        self.addSubview_(self._day_label)
        self.addSubview_(self._tf_seg)
        self.addSubview_(self._now_btn)
        self.addSubview_(self._expand_btn)

        return self

    def _apply_timeframe_to_slider(self, tf, slider_value):
        lo, hi, ticks = TIME_SLIDER[tf]
        self._day_slider.setMinValue_(lo)
        self._day_slider.setMaxValue_(hi)
        self._day_slider.setNumberOfTickMarks_(int(ticks))
        self._day_slider.setDoubleValue_(float(slider_value))
        for s in (0, 1, 2):
            self._tf_seg.setSelected_forSegment_(s == tf, s)

    def drawRect_(self, rect):
        AppKit.NSColor.colorWithRed_green_blue_alpha_(
            BG_COLOR[0], BG_COLOR[1], BG_COLOR[2], 1.0
        ).setFill()
        AppKit.NSBezierPath.fillRect_(rect)

    def setChartImage_(self, img):
        self._chart_iv.setImage_(img)

    def setInfoText_(self, astr):
        self._tv.textStorage().setAttributedString_(astr)

    def timeframeIndex(self):
        return int(self._tf_seg.selectedSegment())

    def timeSliderValue(self):
        return self._day_slider.doubleValue()

    def setOffsetLabel_(self, text):
        self._day_label.setStringValue_(text)

    def reapplyTimeframe_value_(self, tf, slider_value):
        self._apply_timeframe_to_slider(tf, slider_value)

    def setSliderTarget_action_(self, target, action):
        self._day_slider.setTarget_(target)
        self._day_slider.setAction_(action)

    def setTimeframeTarget_action_(self, target, action):
        self._tf_seg.setTarget_(target)
        self._tf_seg.setAction_(action)

    def setNowTarget_action_(self, target, action):
        self._now_btn.setTarget_(target)
        self._now_btn.setAction_(action)

    def setExpandTarget_action_(self, target, action):
        self._expand_btn.setTarget_(target)
        self._expand_btn.setAction_(action)


def build_info_astr(emoji, name, illum, days_to_full, lat, lon, when=None):
    t = when if when is not None else ephem.now()
    dt = ephem.Date(t).datetime().replace(tzinfo=timezone.utc).astimezone()
    wn = int(dt.isocalendar()[1])
    weekday_time = (
        f"{dt.strftime('%A, %B %d, %Y  ·  %H:%M')}  ·  week {wn}"
    )
    lines = [
        (f"{emoji}  {name}", 13, "#f0c040", True),
        (weekday_time, 10, "#8e82b8", True),
        (f"{illum:.0f}%  illuminated", 10, "#aaaacc", False),
        (f"{days_to_full:.1f} days to full moon", 10, "#aaaacc", False),
    ]
    if lat is not None:
        rise, sett = moon_riseset(lat, lon, t)
        lines.append((f"↑ {rise}   ↓ {sett}", 10, "#aaaacc", False))
    lines += [
        ("", 5, "#555577", False),
        ("── Planets ──", 11, "#7c6fa0", True),
    ]
    for glyph, pname, sym, sign, deg in sky_positions(t):
        col = PLANET_COLORS.get(pname, "#cccccc")
        lines.append((f"{glyph} {pname:<8} {sym}{sign} {deg:.0f}°", 12, col, False))
    tz = dt.strftime("%Z")
    ts = dt.strftime("%H:%M")
    loc = f"{lat:.1f},{lon:.1f}" if lat is not None else "–"
    lines += [
        ("", 4, "#555577", False),
        (f"📍{loc}  {tz}  {ts}", 7.5, "#666688", False),
    ]

    result = AppKit.NSMutableAttributedString.alloc().init()
    for i, (text, size, hex_col, bold) in enumerate(lines):
        if i > 0:
            result.appendAttributedString_(
                AppKit.NSAttributedString.alloc().initWithString_("\n")
            )
        part = AppKit.NSAttributedString.alloc().initWithString_attributes_(
            text,
            {
                AppKit.NSForegroundColorAttributeName: _nscolor(hex_col),
                AppKit.NSFontAttributeName: _font(size, bold),
            },
        )
        result.appendAttributedString_(part)
    return result


# ── Expand window (optional) ─────────────────────────────────────────────────

class AstralBgView(AppKit.NSView):

    def drawRect_(self, rect):
        AppKit.NSColor.colorWithRed_green_blue_alpha_(
            BG_COLOR[0], BG_COLOR[1], BG_COLOR[2], 1.0
        ).setFill()
        AppKit.NSBezierPath.fillRect_(rect)


# ── App controller ────────────────────────────────────────────────────────────

class AppController(AppKit.NSObject):

    def init(self):
        self = objc.super(AppController, self).init()
        if self is None:
            return None

        self._expand_window = None
        self._expand_chart_iv = None
        self._expand_info_tv = None
        self._exp_tf_seg = None
        self._exp_now_btn = None
        self._exp_day_slider = None
        self._exp_day_label = None
        self._exp_split = None
        self._exp_syncing = False
        self._expand_open_once = False

        # Status item
        bar = AppKit.NSStatusBar.systemStatusBar()
        self._item = bar.statusItemWithLength_(AppKit.NSVariableStatusItemLength)
        self._item.button().setTitle_("🌑")

        # Menu with one custom-view item + separator + Quit
        menu = AppKit.NSMenu.alloc().init()
        menu.setAutoenablesItems_(False)

        self._panel_view = SkyPanelView.alloc().init()
        view_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "", None, ""
        )
        view_item.setView_(self._panel_view)
        menu.addItem_(view_item)

        menu.addItem_(AppKit.NSMenuItem.separatorItem())

        quit_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit", "terminate:", "q"
        )
        quit_item.setTarget_(AppKit.NSApplication.sharedApplication())
        menu.addItem_(quit_item)

        self._item.setMenu_(menu)

        self._panel_view.setSliderTarget_action_(self, "daySliderChanged:")
        self._panel_view.setTimeframeTarget_action_(self, "timeframeChanged:")
        self._panel_view.setNowTarget_action_(self, "nowClicked:")
        self._panel_view.setExpandTarget_action_(self, "expandClicked:")
        self._timeframe = 0

        # Location
        self._loc = LocationManager.alloc().init()
        self._loc.on_update = self._location_received
        self._loc.request()

        # Hourly refresh timer
        self._timer = AppKit.NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            3600, self, "tick:", None, True
        )

        self._refresh()
        return self

    def _location_received(self, lat, lon):
        AppKit.NSOperationQueue.mainQueue().addOperationWithBlock_(
            lambda: self._refresh()
        )

    def tick_(self, _timer):
        self._refresh()

    def daySliderChanged_(self, sender):
        self._refresh()

    def nowClicked_(self, sender):
        tf = int(self._panel_view.timeframeIndex())
        self._timeframe = tf
        self._panel_view.reapplyTimeframe_value_(tf, 0.0)
        self._refresh()

    def timeframeChanged_(self, sender):
        new = int(sender.selectedSegment())
        if new == self._timeframe:
            return
        prev = self._timeframe
        v = self._panel_view.timeSliderValue()
        off = offset_days_from_timeframe_unit(prev, v)
        s_new = _slider_value_for_offset_days(new, off)
        self._timeframe = new
        self._panel_view.reapplyTimeframe_value_(new, s_new)
        self._refresh()

    def expandClicked_(self, sender):
        if self._expand_window is None:
            self._build_expand_window()
        self._expand_open_once = True
        self._expand_window.makeKeyAndOrderFront_(sender)
        try:
            AppKit.NSApp.activateIgnoringOtherApps_(True)
        except Exception:
            pass
        self._refresh()

    def _build_expand_window(self):
        pad = float(EXPAND_INNER)
        w, h = float(EXPAND_W), float(EXPAND_H)
        m = (
            getattr(AppKit, "NSWindowStyleMaskTitled", 1)
            | getattr(AppKit, "NSWindowStyleMaskClosable", 2)
            | getattr(AppKit, "NSWindowStyleMaskMiniaturizable", 4)
            | getattr(AppKit, "NSWindowStyleMaskResizable", 8)
        )
        rect = AppKit.NSMakeRect(200, 200, w, h)
        back = getattr(AppKit, "NSBackingStoreBuffered", 2)
        win = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, m, back, False
        )
        win.setTitle_("Astral chart")
        win.setReleasedWhenClosed_(False)
        win.setMinSize_(AppKit.NSMakeSize(700, 480))

        root = AstralBgView.alloc().initWithFrame_(
            AppKit.NSMakeRect(0, 0, w, h)
        )
        fmask = (
            getattr(AppKit, "NSViewWidthSizable", 2)
            | getattr(AppKit, "NSViewHeightSizable", 16)
        )
        root.setAutoresizingMask_(fmask)

        # Bottom: d / w / m, Now, slider + offset (same as menu, no ⤢)
        y_row1 = float(PAD)
        y_row2 = y_row1 + float(TIME_CONTROL_ROW_H) + float(TIME_MID_GAP)
        seg_w = 116.0
        now_w = 50.0
        exp_seg = AppKit.NSSegmentedControl.alloc().initWithFrame_(
            AppKit.NSMakeRect(pad, y_row1, seg_w, 24.0)
        )
        exp_seg.setSegmentCount_(3)
        for i, lab in enumerate(["d", "w", "m"]):
            exp_seg.setLabel_forSegment_(lab, i)
        exp_seg.setSelected_forSegment_(True, 0)
        exp_seg.setSegmentStyle_(
            getattr(AppKit, "NSSegmentStyleTexturedSquare", 2)
        )
        exp_now = AppKit.NSButton.alloc().initWithFrame_(
            AppKit.NSMakeRect(pad + seg_w + 8.0, y_row1 + 1.0, now_w, 22.0)
        )
        exp_now.setTitle_("Now")
        exp_now.setButtonType_(
            getattr(AppKit, "NSButtonTypeMomentaryLight", 0)
        )
        exp_now.setBezelStyle_(getattr(AppKit, "NSBezelStyleRounded", 1))
        if hasattr(AppKit, "NSControlSizeSmall"):
            exp_now.setControlSize_(AppKit.NSControlSizeSmall)
        self._exp_day_label = AppKit.NSTextField.alloc().initWithFrame_(
            AppKit.NSMakeRect(0, 0, 0, 0)
        )
        self._exp_day_label.setStringValue_("Now")
        self._exp_day_label.setBezeled_(False)
        self._exp_day_label.setDrawsBackground_(False)
        self._exp_day_label.setEditable_(False)
        self._exp_day_label.setSelectable_(False)
        self._exp_day_label.setFont_(_font(10, True))
        self._exp_day_label.setTextColor_(_nscolor("#7c6fa0"))
        self._exp_day_label.setAlignment_(AppKit.NSTextAlignmentRight)
        label_w = 64.0
        sli_w = w - 2.0 * pad - label_w - 8.0
        exp_sli = AppKit.NSSlider.alloc().initWithFrame_(
            AppKit.NSMakeRect(pad, y_row2, sli_w, 22.0)
        )
        lo, hi, ticks = TIME_SLIDER[0]
        exp_sli.setMinValue_(lo)
        exp_sli.setMaxValue_(hi)
        exp_sli.setNumberOfTickMarks_(int(ticks))
        exp_sli.setDoubleValue_(0.0)
        exp_sli.setAllowsTickMarkValuesOnly_(False)
        exp_sli.setContinuous_(True)
        self._exp_day_label.setFrame_(
            AppKit.NSMakeRect(pad + sli_w + 8.0, y_row2, label_w, 22.0)
        )
        y_main0 = y_row2 + float(SLIDER_H) + float(SLIDER_TOP_GAP)
        main_h = h - y_main0 - pad
        main_w = w - 2.0 * pad
        if main_h < 200:
            main_h = 200.0

        split = AppKit.NSSplitView.alloc().initWithFrame_(
            AppKit.NSMakeRect(pad, y_main0, main_w, main_h)
        )
        # NO = side-by-side panes with a vertical divider (chart | summary)
        if hasattr(split, "setVertical_"):
            split.setVertical_(False)
        split.setAutoresizingMask_(fmask)
        if hasattr(split, "setDividerStyle_"):
            split.setDividerStyle_(getattr(AppKit, "NSSplitViewDividerStyleThin", 2))

        leftp = AppKit.NSView.alloc().initWithFrame_(
            AppKit.NSMakeRect(0, 0, main_w * 0.56, main_h)
        )
        rightp = AppKit.NSView.alloc().initWithFrame_(
            AppKit.NSMakeRect(0, 0, main_w * 0.44, main_h)
        )
        lmask = fmask
        leftp.setAutoresizingMask_(lmask)
        rightp.setAutoresizingMask_(lmask)

        chart_iv = AppKit.NSImageView.alloc().initWithFrame_(
            AppKit.NSMakeRect(0, 0, 100, 100)
        )
        chart_iv.setImageScaling_(AppKit.NSImageScaleProportionallyUpOrDown)
        chart_iv.setAutoresizingMask_(fmask)
        leftp.addSubview_(chart_iv)

        scroll = AppKit.NSScrollView.alloc().initWithFrame_(
            AppKit.NSMakeRect(0, 0, 100, 100)
        )
        scroll.setHasVerticalScroller_(True)
        scroll.setAutohidesScrollers_(True)
        scroll.setDrawsBackground_(False)
        if hasattr(scroll, "setAutoresizingMask_"):
            scroll.setAutoresizingMask_(fmask)
        borderless = getattr(AppKit, "NSNoBorder", 0)
        if hasattr(scroll, "setBorderType_"):
            scroll.setBorderType_(borderless)
        else:
            scroll.setBorderType_(0)

        tv = AppKit.NSTextView.alloc().initWithFrame_(
            AppKit.NSMakeRect(0, 0, 200, 4000)
        )
        tv.setEditable_(False)
        tv.setSelectable_(True)
        tv.setDrawsBackground_(False)
        tv.setRichText_(True)
        if hasattr(scroll, "setDocumentView_"):
            scroll.setDocumentView_(tv)
        scroll.setAutohidesScrollers_(True)
        if hasattr(AppKit, "NSViewWidthSizable") and hasattr(tv, "setAutoresizingMask_"):
            wsz = (
                AppKit.NSViewWidthSizable
                | getattr(AppKit, "NSViewHeightSizable", 16)
            )
            tv.setAutoresizingMask_(wsz)
        try:
            tc = tv.textContainer()
            if tc and hasattr(tc, "setWidthTracksTextView_"):
                tc.setWidthTracksTextView_(True)
        except Exception:
            pass
        if hasattr(tv, "setHorizontallyResizable_"):
            tv.setHorizontallyResizable_(False)
        if hasattr(tv, "setVerticallyResizable_"):
            tv.setVerticallyResizable_(True)
        rightp.addSubview_(scroll)
        scroll.setAutoresizingMask_(fmask)
        for sub in (leftp, rightp):
            split.addSubview_(sub)

        root.addSubview_(split)
        for sub in (exp_sli, self._exp_day_label, exp_seg, exp_now):
            root.addSubview_(sub)

        win.setContentView_(root)
        if hasattr(win, "center"):
            win.center()
        self._expand_window = win
        self._expand_chart_iv = chart_iv
        self._expand_info_tv = tv
        self._exp_split = split
        self._exp_left = leftp
        self._exp_right = rightp
        self._exp_scroll = scroll
        self._exp_tf_seg = exp_seg
        self._exp_now_btn = exp_now
        self._exp_day_slider = exp_sli
        # Wiring (separate from menu so expand ↔ panel can stay in sync)
        exp_sli.setTarget_(self)
        exp_sli.setAction_("expDaySliderChanged:")
        exp_seg.setTarget_(self)
        exp_seg.setAction_("expTimeframeChanged:")
        exp_now.setTarget_(self)
        exp_now.setAction_("expNowClicked:")

        def _layout_split():
            if not self._exp_split:
                return
            f = self._exp_split.frame()
            mw = float(f.size.width)
            if mw < 1:
                return
            pos = mw * 0.56
            pmin = float(mw) * EXPAND_MIN_SPLIT
            pmax = float(mw) * EXPAND_MAX_SPLIT
            pos = max(pmin, min(pmax, pos))
            if hasattr(self._exp_split, "setPosition_ofDividerAtIndex_"):
                self._exp_split.setPosition_ofDividerAtIndex_(pos, 0)
            for pane, v in (self._exp_left, self._expand_chart_iv), (self._exp_right, self._exp_scroll):
                b = pane.bounds()
                pbr = AppKit.NSMakeRect(0, 0, b.size.width, b.size.height)
                v.setFrame_(pbr)

        AppKit.NSOperationQueue.mainQueue().addOperationWithBlock_(_layout_split)

    def _sync_exp_from_panel(self):
        if self._exp_day_slider is None or self._exp_tf_seg is None:
            return
        if self._exp_syncing:
            return
        tf = int(self._panel_view.timeframeIndex())
        s = float(self._panel_view.timeSliderValue())
        cap = time_offset_caption(tf, s)
        self._exp_syncing = True
        try:
            lo, hi, tks = TIME_SLIDER[tf]
            self._exp_day_slider.setMinValue_(lo)
            self._exp_day_slider.setMaxValue_(hi)
            self._exp_day_slider.setNumberOfTickMarks_(int(tks))
            self._exp_day_slider.setDoubleValue_(s)
            for seg in (0, 1, 2):
                self._exp_tf_seg.setSelected_forSegment_(seg == tf, seg)
            if self._exp_day_label is not None:
                self._exp_day_label.setStringValue_(cap)
        finally:
            self._exp_syncing = False

    def expDaySliderChanged_(self, sender):
        if self._exp_syncing:
            return
        tf = int(self._exp_tf_seg.selectedSegment())
        s = self._exp_day_slider.doubleValue()
        self._timeframe = tf
        self._panel_view.reapplyTimeframe_value_(tf, s)
        self._refresh()

    def expTimeframeChanged_(self, sender):
        if self._exp_syncing:
            return
        new = int(self._exp_tf_seg.selectedSegment())
        if new == self._timeframe:
            return
        prev = self._timeframe
        v = self._exp_day_slider.doubleValue()
        off = offset_days_from_timeframe_unit(prev, v)
        s_new = _slider_value_for_offset_days(new, off)
        self._timeframe = new
        self._panel_view.reapplyTimeframe_value_(new, s_new)
        self._refresh()

    def expNowClicked_(self, sender):
        if self._exp_syncing:
            return
        tf = int(self._exp_tf_seg.selectedSegment())
        self._timeframe = tf
        self._panel_view.reapplyTimeframe_value_(tf, 0.0)
        self._refresh()

    def _refresh(self):
        emoji_menu, _, _, _ = moon_phase()
        self._item.button().setTitle_(emoji_menu)

        self._timeframe = int(self._panel_view.timeframeIndex())
        tf = self._timeframe
        s = self._panel_view.timeSliderValue()
        self._panel_view.setOffsetLabel_(time_offset_caption(tf, s))
        off = offset_days_from_timeframe_unit(tf, s)
        when = when_from_offset_days(off)
        emoji, name, illum, dtf = moon_phase(when)

        lat, lon = self._loc.lat, self._loc.lon
        astr = build_info_astr(emoji, name, illum, dtf, lat, lon, when)
        self._panel_view.setInfoText_(astr)
        if self._expand_window is not None and self._expand_info_tv is not None:
            self._expand_info_tv.textStorage().setAttributedString_(astr)
        self._sync_exp_from_panel()

        ex_open = bool(self._expand_open_once)
        if ex_open:
            self._expand_open_once = False
        also_expand = self._expand_window is not None and (
            (self._expand_window.isVisible()) or ex_open
        )
        if lat is not None:
            threading.Thread(
                target=self._render_chart,
                args=(lat, lon, off, also_expand),
                daemon=True,
            ).start()

    def _render_chart(self, lat, lon, offset_days, also_expand=False):
        when = when_from_offset_days(offset_days)
        pimg = chart_to_nsimage(
            lat, lon, dpi=PANEL_DPI, when=when, figsize=PANEL_FIG
        )
        eimg = None
        if also_expand:
            eimg = chart_to_nsimage(
                lat, lon, dpi=EXPAND_DPI, when=when, figsize=EXPAND_FIG
            )

        def on_main():
            self._panel_view.setChartImage_(pimg)
            if eimg is not None and self._expand_chart_iv is not None:
                self._expand_chart_iv.setImage_(eimg)

        AppKit.NSOperationQueue.mainQueue().addOperationWithBlock_(on_main)


# ── Entry point ───────────────────────────────────────────────────────────────

_controller_ref = None   # module-level strong reference prevents GC

def main():
    global _controller_ref
    app = AppKit.NSApplication.sharedApplication()
    app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)
    _controller_ref = AppController.alloc().init()
    app.run()


if __name__ == "__main__":
    main()
