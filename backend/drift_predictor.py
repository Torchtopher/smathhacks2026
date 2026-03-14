from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import lru_cache
import logging

from opendrift.models.oceandrift import OceanDrift
from opendrift.readers import reader_netCDF_CF_generic

_HYCOM_SOURCE_URL = "https://tds.hycom.org/thredds/dodsC/GLBy0.08/expt_93.0"


class _SuppressCfDecodeNoise(logging.Filter):
    """Suppress known benign OpenDrift CF decode warnings for HYCOM."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return "Removing variables that cannot be CF decoded:" not in msg


logging.getLogger("opendrift.readers").addFilter(_SuppressCfDecodeNoise())


@lru_cache(maxsize=1)
def _get_reader() -> reader_netCDF_CF_generic.Reader:
    return reader_netCDF_CF_generic.Reader(_HYCOM_SOURCE_URL)


def _to_utc_datetime(epoch_like: float) -> datetime:
    # Some clients send ms since epoch; normalize to seconds if needed.
    ts_seconds = epoch_like / 1000.0 if epoch_like > 1e11 else epoch_like
    return datetime.fromtimestamp(ts_seconds, tz=timezone.utc)


def predict_drift_days(
    detected_at: float,
    lat: float,
    lon: float,
    days: int,
) -> list[dict[str, float]]:
    start_t = _to_utc_datetime(detected_at).replace(year=2024, tzinfo=None)
    reader = _get_reader()

    model = OceanDrift(loglevel=30)
    model.add_reader([reader])
    model.seed_elements(
        lat=lat,
        lon=lon,
        number=1,
        radius=0,
        time=start_t,
    )
    model.run(
        duration=timedelta(days=days),
        time_step=timedelta(hours=12),
    )

    lats = model.result.lat.values[0]
    lons = model.result.lon.values[0]

    return [
        {
            "lat": float(lat_i),
            "lon": float(lon_i),
            "time_offset_hours": float(idx * 12),
        }
        for idx, (lat_i, lon_i) in enumerate(zip(lats, lons))
    ]
