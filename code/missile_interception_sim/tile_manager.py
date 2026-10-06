import math
import os
import requests
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt

def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return xtile, ytile

def num2deg(xtile, ytile, zoom):
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lon_deg

def _load_carto_key():
    """Read CARTO_API_KEY from the environment or the git-ignored .env file."""
    key = os.environ.get("CARTO_API_KEY", "").strip()
    if not key:
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("CARTO_API_KEY="):
                        key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
    return key

def get_carto_tile(z, x, y):
    # The keyed /rastertiles/ endpoint returns clean tiles; the unkeyed one is stamped "API KEY REQUIRED".
    key = _load_carto_key()
    url = f"https://a.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}.png?key={key}"
    cache_dir = os.path.expanduser("~/.cache/missile_sim_tiles_keyed")
    os.makedirs(cache_dir, exist_ok=True)
    filepath = os.path.join(cache_dir, f"carto_dark_{z}_{x}_{y}.png")
    
    if not os.path.exists(filepath):
        try:
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(r.content)
        except Exception:
            pass
            
    if os.path.exists(filepath):
        return QPixmap(filepath)
    return None
