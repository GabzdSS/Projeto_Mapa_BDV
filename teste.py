import openrouteservice
from openrouteservice import convert
import folium

client = openrouteservice.Client(key='eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6ImFhMzQwMzk1MDM0MjQ2NjQ4NjI5Nzg0ZTFmYmZjZjNhIiwiaCI6Im11cm11cjY0In0=')  # pega em https://openrouteservice.org/dev/#/signup

# ponto inicial e final (LONGITUDE, LATITUDE) — ATENÇÃO à ordem!
coords = (
    (row["LONG_LANCADA"], row["LAT_LANCADA"]),
    (row["LONG_POSTO"], row["LAT_POSTO"])
)

# solicita a rota
rota = client.directions(coords, profile='driving-car', format='geojson')

# desenha no mapa
folium.GeoJson(
    rota,
    name='Rota via ruas'
).add_to(m)
