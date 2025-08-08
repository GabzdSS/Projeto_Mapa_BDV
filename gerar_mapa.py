import pandas as pd
import folium
from folium.plugins import MarkerCluster
import openrouteservice
from openrouteservice import convert
from math import radians, cos, sin, asin, sqrt

def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371000  # Raio da Terra em metros
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * asin(sqrt(a))
    return R * c

def gerar_mapa_filtrado(df):
    # Conversão de dados
    df["LAT_LANCADA"] = df["LAT_LANCADA"].astype(float) / 100000.0
    df["LONG_LANCADA"] = df["LONG_LANCADA"].astype(float) / 100000.0
    df["LAT_POSTO"] = df["LAT_POSTO"].astype(float) / 100000.0
    df["LONG_POSTO"] = df["LONG_POSTO"].astype(float) / 100000.0
    df["DTHRCHEGADA"] = pd.to_datetime(df["DTHRCHEGADA"], errors="coerce")
    df["DTHRSAIDA"] = pd.to_datetime(df["DTHRSAIDA"], errors="coerce")
    df = df.dropna(subset=["LAT_LANCADA", "LONG_LANCADA"])

    # Tempo parado no local (em minutos)
    df["TEMPO_PARADO_MIN"] = (df["DTHRSAIDA"] - df["DTHRCHEGADA"]).dt.total_seconds() // 60

 
    m = folium.Map(location=[df["LAT_LANCADA"].iloc[0], df["LONG_LANCADA"].iloc[0]], zoom_start=14)
    marker_cluster = MarkerCluster().add_to(m)

    client = openrouteservice.Client(key='eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6ImFhMzQwMzk1MDM0MjQ2NjQ4NjI5Nzg0ZTFmYmZjZjNhIiwiaCI6Im11cm11cjY0In0=') 

    # Marcação ponto a ponto
    for _, row in df.iterrows():
        popup = f"""
        <b>Funcionário:</b> {row.get('NOME_FUNCIONARIO', 'N/A')}<br>
        <b>Cliente:</b> {row.get('NOME_CLIENTE', 'N/A')}<br>
        <b>Posto:</b> {row.get('NOME_POSTO', 'N/A')}<br>
        <b>Chegada:</b> {row.get('DTHRCHEGADA', 'N/A')}<br>
        <b>Distância (m):</b> {row.get('DISTANCIA_METROS', 'N/A')}
        <b>Tempo parado (min):</b> {row.get("TEMPO_PARADO_MIN", "N/A")}<br>
        """

        folium.Marker(
            location=[row["LAT_LANCADA"], row["LONG_LANCADA"]],
            popup=popup,
            icon=folium.Icon(color="blue", icon="user")
        ).add_to(marker_cluster)

        if pd.notnull(row["LAT_POSTO"]) and pd.notnull(row["LONG_POSTO"]):
            # Define cor conforme distância
            dist_metros = calcular_distancia(
                row["LAT_LANCADA"], row["LONG_LANCADA"],
                row["LAT_POSTO"], row["LONG_POSTO"]
            )

            if dist_metros <= 50:
                cor = "green"
            elif dist_metros <= 300:
                cor = "orange"
            else:
                cor = "red"

            folium.PolyLine(
                locations=[
                    [row["LAT_LANCADA"], row["LONG_LANCADA"]],
                    [row["LAT_POSTO"], row["LONG_POSTO"]]
                ],
                color=cor,
                weight=3,
                opacity=0.8,
                tooltip=f"{int(dist_metros)} metros do destino"
            ).add_to(m)

            folium.Marker(
                location=[row["LAT_POSTO"], row["LONG_POSTO"]],
                icon=folium.Icon(color="red", icon="flag")
            ).add_to(marker_cluster)

    resumo_rota = {
        "funcionarios": []
    }

    for nome_funcionario, grupo in df.groupby("NOME_FUNCIONARIO"):
        grupo = grupo.sort_values("DTHRCHEGADA")
        grupo["DTHRCHEGADA"] = pd.to_datetime(grupo["DTHRCHEGADA"])

        # Rota entre batidas
        pontos = grupo[["LAT_LANCADA", "LONG_LANCADA"]]
        coords = [(lon, lat) for lat, lon in pontos.values.tolist()]

        from functools import lru_cache

        # cache simples pra evitar chamadas repetidas à API
        @lru_cache(maxsize=2048)
        def _rota_trecho_ors(lon1, lat1, lon2, lat2):
            try:
                rota = client.directions(
                    coordinates=[(lon1, lat1), (lon2, lat2)],
                    profile="driving-car",
                    format="geojson"
                )
                props = rota["features"][0]["properties"]["summary"]
                return float(props["distance"]), float(props["duration"])  # metros, segundos
            except Exception:
                return None, None

        # ...dentro do loop por funcionário:
        grupo = grupo.sort_values("DTHRCHEGADA").copy()
        grupo["DTHRCHEGADA"] = pd.to_datetime(grupo["DTHRCHEGADA"])

        tempos_entre_batidas = []

        for i in range(1, len(grupo)):
            t1 = grupo.iloc[i - 1]["DTHRCHEGADA"]
            t2 = grupo.iloc[i]["DTHRCHEGADA"]
            dt_min = int((t2 - t1).total_seconds() // 60)

            lat1, lon1 = float(grupo.iloc[i - 1]["LAT_LANCADA"]), float(grupo.iloc[i - 1]["LONG_LANCADA"])
            lat2, lon2 = float(grupo.iloc[i]["LAT_LANCADA"]), float(grupo.iloc[i]["LONG_LANCADA"])

            dist_m, dur_s = _rota_trecho_ors(lon1, lat1, lon2, lat2)

            tempos_entre_batidas.append({
                "origem": t1.strftime("%H:%M"),
                "destino": t2.strftime("%H:%M"),
                "minutos": dt_min,                               # diferença entre marcações
                "dist_km": round(dist_m / 1000, 2) if dist_m else None,
                "dur_est_min": int(dur_s // 60) if dur_s else None
            })

        try:
            rota_completa = client.directions(
                coordinates=coords,
                profile='driving-car',
                format='geojson'
            )

            duracao_segundos = rota_completa['features'][0]['properties']['summary']['duration']
            distancia_metros = rota_completa['features'][0]['properties']['summary']['distance']

            folium.GeoJson(
                rota_completa,
                name=f"Rota completa {nome_funcionario}",
                tooltip=f"{nome_funcionario}: {round(distancia_metros / 1000, 2)} km em {int(duracao_segundos // 60)} min"
            ).add_to(m)

            resumo_rota["funcionarios"].append({
                "nome": nome_funcionario,
                "duracao_min": int(duracao_segundos // 60),
                "distancia_km": round(distancia_metros / 1000, 2),
                "batidas": len(grupo),
                "tempos_entre_batidas": tempos_entre_batidas,
                "CODIGOATIVO": str(grupo["CODIGOATIVO"].iloc[0]) if "CODIGOATIVO" in grupo.columns else ""
            })

        except Exception as e:
            print(f"Erro na rota completa de {nome_funcionario}: {e}")

    nome_arquivo = "mapa_filtrado.html"
    m.save(nome_arquivo)
    return nome_arquivo, resumo_rota