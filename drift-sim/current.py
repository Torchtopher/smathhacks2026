from opendrift.models.oceandrift import OceanDrift
from opendrift.readers import reader_netCDF_CF_generic
from datetime import datetime, timedelta

reader = reader_netCDF_CF_generic.Reader(
    'https://tds.hycom.org/thredds/dodsC/GLBy0.08/expt_93.0'
)

def predict(start_t, dt, lat, lon):
    o = OceanDrift(loglevel=20)
    o.add_reader([reader])
    o.seed_elements(
        lat=lat,
        lon=lon,
        number=1,
        radius=0,
        time=start_t
    )

    o.run(duration=dt, time_step=dt)
    print(o.elements.lon)
    print(o.elements.lat)

while True:
    days = int(input("Enter the number of days: "))
    predict(datetime(2024, 1, 1), timedelta(days=days), lat=35, lon=-74)
