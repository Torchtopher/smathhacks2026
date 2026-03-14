import holoocean

print(holoocean.util.get_holoocean_path())
with holoocean.make('SLAMCloud-test') as env:
#with holoocean.make('SimpleUnderwater-Torpedo') as env:
    for i in range(1000):
        env.tick()
        print("tick")

