from opendrift.models.oceandrift import OceanDrift
from opendrift.readers import reader_netCDF_CF_generic
from datetime import datetime, timedelta

o = OceanDrift(loglevel=20)

# Uses old data, not sure the exact dates
reader = reader_netCDF_CF_generic.Reader(
    'https://tds.hycom.org/thredds/dodsC/GLBy0.08/expt_93.0')

o.add_reader([reader])

o.seed_elements(
    # Off the coast of NC
    lat=34.7657861111,
    lon=-75.7673472222,
    number=20,
    radius=1000,
    time=datetime(2023,1,1)
)

# Calculate position over 2 days
o.run(duration=timedelta(days=2), time_step=900)
o.animation()
