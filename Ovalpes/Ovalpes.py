import json
import math
import heapq
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import colors, cm
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import aacgmv2
import datetime


class cameraclass:
    def __init__(self, data):
        self.name = data.get('name', None)
        self.lon  = float(data['lon'])
        self.lat  = float(data['lat'])
        self.qdlat = get_qd_latitude(self.lat, self.lon, datetime.datetime(2024, 5, 10))
        self.lumd = data['lumd'] 
        times = pd.to_datetime(list(self.lumd.keys()), format="%Y%m%dT%H%M")
        self.df = (pd.DataFrame({'lumd': list(self.lumd.values())}, index=times).sort_index())

class magnetometerclass:
    def __init__(self, data):
        self.lon    = float(data['lon'])
        self.lat    = float(data['lat'])
        self.time   = data['time']     
        self.valeur = data['valeur']
        times = pd.to_datetime(self.time, format="%Y%m%dT%H%M")
        self.df = (pd.DataFrame({'H': self.valeur}, index=times).sort_index())


def load_fripon_data(input_file):
    with open(input_file, 'r') as f:
        raw = json.load(f)
    return {name: cameraclass({**camdata, 'name': name}) for name, camdata in raw.items()}

def load_magneto_data(input_file):
    with open(input_file, 'r') as f:
        raw = json.load(f)
    return {name: magnetometerclass(d) for name, d in raw.items()}

def get_qd_latitude(lat, lon, dtime=None, height=110):
    if dtime is None:
        dtime = datetime.datetime.utcnow()
    qdlat, qdlon, _ = aacgmv2.get_aacgm_coord(lat, lon, height, dtime)
    return qdlat

_cmap_cache = {}
def get_red_green_cmap(lat_min, lat_max, lat_center=46.0):
    key = (lat_min, lat_max, lat_center)
    if key in _cmap_cache:
        return _cmap_cache[key]
    n = 256
    t = lambda lat: (lat - lat_min) / (lat_max - lat_min)
    idx = int(n * t(lat_center))
    reds   = plt.get_cmap("Reds" )(np.linspace(0.1,1.0,idx))[::-1]
    greens = plt.get_cmap("Greens")(np.linspace(0.1,1.0,n-idx))
    cmap = colors.LinearSegmentedColormap.from_list("RGsplit", np.vstack([reds, greens]))
    norm = colors.Normalize(vmin=lat_min, vmax=lat_max)
    _cmap_cache[key] = (cmap, norm)
    return cmap, norm

def plot_all_cameras(Fripon, x_min, x_max, y_min, y_max, lat_transition=46):
    lat_min, lat_max = 42, 50
    cmap, norm = get_red_green_cmap(lat_min, lat_max, lat_transition)
    fig, ax = plt.subplots(figsize=(12, 6))

    for name, cam in Fripon.items():
        lat = cam.lat
        if not (lat_min <= lat <= lat_max):
            continue
        df = cam.df.loc[x_min:x_max]
        if df.empty:
            continue
        ax.plot(df.index, df['lumd'],
                color=cmap(norm(lat)),
                linewidth=2, alpha=0.3,
                label=f"{name} ({lat:.1f}°N)")
    ax.set_xlabel("Time UTC")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.tick_params(axis='x', rotation=30)
    ax.set_ylabel("Brightness (mag/arcsec²)")
    ax.set_ylim(y_min, y_max)
    ax.grid(axis='x', linestyle='--', alpha=0.3)
    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, pad=0.01)
    cbar.set_label("Latitude (°N)")
    plt.title("Luminosity from FRIPON cameras by latitude (42°–50°N)")
    plt.tight_layout()
    plt.show()



def diff_degres(lat1, lon1, lat2, lon2):
    return math.hypot(lat1 - lat2, lon1 - lon2)

def closest_cam_from_mag(Magnetometre, Fripon, k):
    assoc_cam    = {}
    proches_cams = {}
    for mname, mag in Magnetometre.items():
        latm, lonm = mag.lat, mag.lon
        heap = [
            (diff_degres(latm, lonm, cam.lat, cam.lon), cname)
            for cname, cam in Fripon.items()
        ]
        best = heapq.nsmallest(k, heap, key=lambda x: x[0])
        if best:
            assoc_cam[mname]    = (best[0][1], best[0][0])
            proches_cams[mname] = best
        else:
            assoc_cam[mname]    = (None, None)
            proches_cams[mname] = []
    return assoc_cam, proches_cams

def plot_graph(Magnetometre, Fripon, x_min, x_max, y_min, y_max, output_path):
    assoc_cam, _ = closest_cam_from_mag(Magnetometre, Fripon, k=3)
    for mname, mag in Magnetometre.items():
        cname, dist = assoc_cam[mname]
        if cname is None:
            continue
        dfm = mag.df.loc[x_min:x_max]
        dfc = Fripon[cname].df.loc[x_min:x_max]
        fig, ax1 = plt.subplots(figsize=(10,4))
        ax1.plot(dfm.index, dfm['H'], color='tab:blue', label=f"{mname} ({mag.lat:.2f}°N)", linewidth=1.5)
        ax1.set_xlabel("Time UTC")
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        ax1.set_ylabel("H component (nT)", color='tab:blue')
        ax1.tick_params(axis='y', labelcolor='tab:blue')
        ax1.set_xlim(x_min, x_max)
        ax1.grid(axis='x', linestyle='--', alpha=0.5)

        ax2 = ax1.twinx()
        ax2.plot(dfc.index, dfc['lumd'], color='tab:orange', label=f"{cname} ({Fripon[cname].lat:.2f}°N)", linewidth=1.5)
        ax2.set_ylabel("Brightness (mag/arcsec²)", color='tab:orange')
        ax2.tick_params(axis='y', labelcolor='tab:orange')
        ax2.set_ylim(y_min, y_max)

        h1,l1 = ax1.get_legend_handles_labels()
        h2,l2 = ax2.get_legend_handles_labels()
        ax1.legend(h1+h2, l1+l2, loc='lower left')

        plt.title(f"{mname} & {cname} ({dist:.2f}° apart)")
        out = f"{output_path}\\graph_{mname}_vs_{cname}.png"
        print(f"{output_path}\\graph_{mname}_vs_{cname}")
        plt.savefig(out, dpi=150)
        plt.close()

def plot_graph_stack(Magnetometre, Fripon, x_min, x_max, y_min, y_max, stack_mags, output_path):
    assoc_cam, proches_cams = closest_cam_from_mag(Magnetometre, Fripon, k=1)
    fig, axes = plt.subplots(len(stack_mags), 1, sharex=True, figsize=(12,3*len(stack_mags)))
    for ax, mname in zip(axes, stack_mags):
        mag = Magnetometre[mname]
        dfm = mag.df.loc[x_min:x_max]
        ax.plot(dfm.index, dfm['H'], color='tab:blue', linewidth=1, label=f"{mname} ({mag.lat:.2f}°N)")
        ax.set_ylabel("H (nT)", color='tab:blue')
        ax.tick_params(axis='y', labelcolor='tab:blue', labelsize=8)
        ax.grid(axis='x', linestyle='--', alpha=0.3)

        ax2 = ax.twinx()
        for dist, cname in proches_cams[mname]:
            dfc = Fripon[cname].df.loc[x_min:x_max]
            ax2.plot(dfc.index, dfc['lumd'], color='tab:orange', linewidth=1.5, label=f"{cname} ({Fripon[cname].lat:.2f}°N)")
            ax2.set_ylabel("Brightness (mag/arcsec²)", color='tab:orange')
            ax2.tick_params(axis='y', labelcolor='tab:orange', labelsize=8)
        ax2.set_ylim(y_min, y_max)
        ax.set_title(mname, fontsize=9)
        h1,l1 = ax.get_legend_handles_labels()
        h2,l2 = ax2.get_legend_handles_labels()
        ax.legend(h1+h2, l1+l2, loc='upper right', fontsize=7)

    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    axes[-1].set_xlabel("Time UTC")
    plt.tight_layout()
    out = f"{output_path}\\stack_{'_'.join(stack_mags)}.png"
    print(f"{output_path}\\stack_{'_'.join(stack_mags)}")
    plt.savefig(out, dpi=150)
    plt.close()



def ploteurope(Fripon, cameras, Magnetometre, magnetos, x_min, x_max, y_min, y_max, output_path, last):
    df_base = Magnetometre[magnetos[0]].df
    times = df_base.loc[x_min:x_max].index

    for t in times:
        fig, ax = plt.subplots(figsize=(12, 12),
                               subplot_kw={'projection': ccrs.NearsidePerspective(central_longitude=5, central_latitude=40, satellite_height=35785831)})

        ax.set_extent([-15, 30, 35, 65], crs=ccrs.PlateCarree())

        # Fond de carte
        ax.add_feature(cfeature.COASTLINE)
        ax.add_feature(cfeature.BORDERS, linestyle='--')
        ax.add_feature(cfeature.LAND, facecolor='black')
        ax.add_feature(cfeature.OCEAN, facecolor='gray')
        ax.add_feature(cfeature.LAKES, facecolor='gray')
        # ax.add_feature(cfeature.RIVERS)

        # --- Caméras ---
        norm_cam = colors.Normalize(vmin=y_min, vmax=y_max)
        for cam_name, cam in Fripon.items():
            if t in cam.df.index:
                val = cam.df.at[t, 'lumd']
                last[cam_name] = t
            elif cam_name in last:
                val = cam.df.at[last[cam_name], 'lumd']
            else:
                continue  # aucune mesure

            ax.plot(cam.lon, cam.lat,
                    marker='o', markersize=8,
                    color=plt.cm.Greys(norm_cam(val)),
                    transform=ccrs.PlateCarree())

        # Barre de couleur pour les caméras
        sm_cam = cm.ScalarMappable(cmap=plt.cm.Greys, norm=norm_cam)
        sm_cam.set_array([])
        cbar_cam = plt.colorbar(sm_cam, ax=ax, pad=0.02, fraction=0.04)
        cbar_cam.set_label("Brightness (mag/arcsec²)", fontsize=10)

        plt.title(t.strftime("%Y-%m-%d %H:%M"))
        out_file = f"{output_path}\\{t:%Y%m%dT%H%M}.png"
        print(out_file)
        plt.savefig(out_file, dpi=200)
        plt.close()

def find_lat_for_lon(lon, lat_mag, height_km, tol, step, date):
    for lat in np.arange(30, 90, step):
        mlat, _, _ = aacgmv2.get_aacgm_coord(lat, lon, height_km, date)
        if abs(mlat - lat_mag) <= tol:
            return lat
    return np.nan

def ploteuropetest(Fripon, cameras, Magnetometre, magnetos, x_min, x_max, y_min, y_max, output_path, last):
    df_base = Magnetometre[magnetos[0]].df
    times = df_base.loc[x_min:x_max].index

    # Pré-calcule les lignes QD tous les 5°
    qd_lines = []
    for qd_lat in range(30, 65, 5):
        lats_geo = []
        lons_geo = []
        for lon in np.linspace(-40, 60, 300):
            date = datetime.datetime(2024, 5, 10, 22, 0)
            lat_geo = find_lat_for_lon(lon, qd_lat, height_km=110, tol=0.1, step=0.05, date=date)
            if not np.isnan(lat_geo):
                lats_geo.append(lat_geo)
                lons_geo.append(lon)
        if len(lats_geo) > 2:
            qd_lines.append((qd_lat, lons_geo, lats_geo))

    # Génère une image par instant
    for t in times:
        fig, ax = plt.subplots(figsize=(12, 12),
                               subplot_kw={'projection': ccrs.NearsidePerspective(
                                   central_longitude=5, central_latitude=40,
                                   satellite_height=35785831)})

        ax.set_extent([-15, 30, 35, 65], crs=ccrs.PlateCarree())

        # Fond de carte
        ax.add_feature(cfeature.COASTLINE)
        ax.add_feature(cfeature.BORDERS, linestyle='--')
        ax.add_feature(cfeature.LAND, facecolor='black')
        ax.add_feature(cfeature.OCEAN, facecolor='gray')
        ax.add_feature(cfeature.LAKES, facecolor='gray')

        # --- Caméras ---
        norm_cam = colors.Normalize(vmin=y_min, vmax=y_max)
        for cam_name, cam in Fripon.items():
            if t in cam.df.index:
                val = cam.df.at[t, 'lumd']
                last[cam_name] = t
            elif cam_name in last:
                val = cam.df.at[last[cam_name], 'lumd']
            else:
                continue  # aucune mesure

            ax.plot(cam.lon, cam.lat,
                    marker='o', markersize=8,
                    color=plt.cm.Greys(norm_cam(val)),
                    transform=ccrs.PlateCarree())

        # --- Lignes QD marquées (5°) ---
        for qd_lat, lons_geo, lats_geo in qd_lines:
            ax.plot(lons_geo, lats_geo,
                    transform=ccrs.PlateCarree(),
                    linestyle='--', color='white', linewidth=0.8, alpha=0.6, zorder=3)
            mid = len(lons_geo) // 2
            # Décalage vers la gauche en longitude (exemple 20°)
            x_text = lons_geo[mid] - 20
            y_text = lats_geo[mid]  
            ax.text(x_text, y_text, f"{qd_lat}°",transform=ccrs.PlateCarree(),fontsize=7, color='white', alpha=0.6, ha='center', va='bottom')

        # Barre de couleur pour les caméras
        sm_cam = cm.ScalarMappable(cmap=plt.cm.Greys, norm=norm_cam)
        sm_cam.set_array([])
        cbar_cam = plt.colorbar(sm_cam, ax=ax, pad=0.02, fraction=0.04)
        cbar_cam.set_label("Brightness (mag/arcsec²)", fontsize=10)

        plt.title(t.strftime("%Y-%m-%d %H:%M"))
        out_file = f"{output_path}\\{t:%Y%m%dT%H%M}.png"
        print(out_file)
        plt.savefig(out_file, dpi=200)
        plt.close()

def ploteuropedelta(Fripon, cameras, Magnetometre, magnetos, x_min, x_max, y_min, y_max, output_path, last, ref_time_str="2024-05-10 21:40"):
    ref_time = pd.to_datetime(ref_time_str)
    df_base = Magnetometre[magnetos[0]].df
    times = df_base.loc[x_min:x_max].index

    # Pré-calcule les luminosités de référence pour chaque caméra
    ref_lumd_dict = {}
    for cam_name, cam in Fripon.items():
        df = cam.df
        if df.empty:
            continue
        closest_index = df.index.get_indexer([ref_time], method='nearest')[0]
        ref_lumd_dict[cam_name] = df.iloc[closest_index]['lumd']

    # Pré-calcule les lignes QD tous les 5°
    qd_lines = []
    for qd_lat in range(30, 65, 5):
        lats_geo = []
        lons_geo = []
        for lon in np.linspace(-40, 60, 300):
            date = datetime.datetime(2024, 5, 10, 22, 0)
            lat_geo = find_lat_for_lon(lon, qd_lat, height_km=110, tol=0.1, step=0.05, date=date)
            if not np.isnan(lat_geo):
                lats_geo.append(lat_geo)
                lons_geo.append(lon)
        if len(lats_geo) > 2:
            qd_lines.append((qd_lat, lons_geo, lats_geo))

    # Génère une image par instant
    for t in times:
        fig, ax = plt.subplots(figsize=(12, 12),
                               subplot_kw={'projection': ccrs.NearsidePerspective(
                                   central_longitude=5, central_latitude=40,
                                   satellite_height=35785831)})

        ax.set_extent([-15, 30, 35, 65], crs=ccrs.PlateCarree())

        # Fond de carte
        ax.add_feature(cfeature.COASTLINE)
        ax.add_feature(cfeature.BORDERS, linestyle='--')
        ax.add_feature(cfeature.LAND, facecolor='black')
        ax.add_feature(cfeature.OCEAN, facecolor='gray')
        ax.add_feature(cfeature.LAKES, facecolor='gray')

        # --- Caméras ---
        norm_cam = colors.Normalize(vmin=-3, vmax=3)  # centrée sur la différence
        for cam_name, cam in Fripon.items():
            if t in cam.df.index:
                lumd = cam.df.at[t, 'lumd']
                last[cam_name] = t
            elif cam_name in last:
                lumd = cam.df.at[last[cam_name], 'lumd']
            else:
                continue  # aucune mesure

            ref_lumd = ref_lumd_dict.get(cam_name)
            if ref_lumd is None:
                continue

            delta_lumd = lumd - ref_lumd

            ax.plot(cam.lon, cam.lat,
                    marker='o', markersize=8,
                    color=plt.cm.berlin(norm_cam(delta_lumd)),
                    transform=ccrs.PlateCarree())

        # --- Lignes QD marquées (5°) ---
        for qd_lat, lons_geo, lats_geo in qd_lines:
            ax.plot(lons_geo, lats_geo,
                    transform=ccrs.PlateCarree(),
                    linestyle='--', color='white', linewidth=0.8, alpha=0.6, zorder=3)
            mid = len(lons_geo) // 2
            x_text = lons_geo[mid] - 20
            y_text = lats_geo[mid]  
            ax.text(x_text, y_text, f"{qd_lat}°", transform=ccrs.PlateCarree(), fontsize=7, color='white', alpha=0.6, ha='center', va='bottom')

        # Barre de couleur pour les caméras
        sm_cam = cm.ScalarMappable(cmap=plt.cm.berlin, norm=norm_cam)
        sm_cam.set_array([])
        cbar_cam = plt.colorbar(sm_cam, ax=ax, pad=0.02, fraction=0.04)
        cbar_cam.set_label("Δ Brightness (mag/arcsec²)", fontsize=10)

        plt.title(t.strftime("%Y-%m-%d %H:%M"))
        out_file = f"{output_path}\\{t:%Y%m%dT%H%M}.png"
        print(out_file)
        plt.savefig(out_file, dpi=200)
        plt.close()



def plot_brightness_vs_qd_latitude(Fripon, x_min, x_max, lat_min, lat_max, y_min, y_max, output_path):
    import matplotlib.dates as mdates
    from matplotlib.colors import Normalize
    from matplotlib.cm import ScalarMappable

    # plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_facecolor('black')
    cmap = plt.get_cmap('viridis_r')
    norm = Normalize(vmin=y_min, vmax=y_max)

    for name, cam in Fripon.items():
        df = cam.df.loc[x_min:x_max]
        if df.empty:
            continue

        qd_lat = cam.qdlat
        df = df.copy()
        df["next_time"] = df.index.to_series().shift(-1)
        df["duration"] = (df["next_time"] - df.index.to_series()).fillna(pd.Timedelta(minutes=10))
        df = df.dropna()

        ax.barh(
            y=[qd_lat] * len(df),
            width=df["duration"],
            left=df.index,
            height=0.2,
            color=cmap(norm(df["lumd"])),
            edgecolor="none"
        )

    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel("Magnetic QD Latitude (°)")
    ax.set_ylim(lat_min, lat_max)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.tick_params(axis='x', rotation=30)
    sm = ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    plt.colorbar(sm, ax=ax, label="Brightness (mag/arcsec²)")
    plt.title("Brightness by Magnetic QD Latitude and Time")
    plt.tight_layout()
    out = f"{output_path}\\Brightness.png"
    plt.savefig(out, dpi=150)
    plt.show()
    plt.close()
    print(f"{output_path}\\Brightness.png")

def plot_brightness_delta_vs_qd_latitude(Fripon, x_min, x_max, lat_min, lat_max, output_path, ref_time_str="2024-05-10 21:40"):
    ref_time = pd.to_datetime(ref_time_str)
    # plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_facecolor('black')
    cmap = plt.get_cmap('berlin')
    norm = Normalize(vmin=-3, vmax=3)  # Ajustable selon tes écarts attendus

    for name, cam in Fripon.items():
        df = cam.df.loc[x_min:x_max].copy()
        if df.empty:
            continue

        # Trouve la valeur la plus proche de 21h50 pour cette caméra
        closest_index = df.index.get_indexer([ref_time], method='nearest')[0]
        t_ref = df.index[closest_index]
        ref_lumd = df.iloc[closest_index]['lumd']

        # Calcul des différences
        df['delta_lumd'] = df['lumd'] - ref_lumd
        df['next_time'] = df.index.to_series().shift(-1)
        df['duration'] = (df['next_time'] - df.index.to_series()).fillna(pd.Timedelta(minutes=10))
        df = df.dropna()

        qd_lat = cam.qdlat
        ax.barh(
            y=[qd_lat] * len(df),
            width=df["duration"],
            left=df.index,
            height=0.2,
            color=cmap(norm(df["delta_lumd"])),
            edgecolor="none"
        )

    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel("Magnetic QD Latitude (°)")
    ax.set_ylim(lat_min, lat_max)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.tick_params(axis='x', rotation=30)

    sm = ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    plt.colorbar(sm, ax=ax, label="Δ Brightness (mag/arcsec²) from 21:40")
    plt.title("Brightness Variation from Nearest 21:40 by Magnetic QD Latitude")
    plt.tight_layout()
    out = f"{output_path}\\Delta_Brightness.png"
    plt.savefig(out, dpi=150)
    plt.show()
    plt.close()
    print(f"{output_path}\\Delta_Brightness.png")    

def plot_brightness_delta_vs_qd_latitude_mean(Fripon, x_min, x_max, lat_min, lat_max, output_path):
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_facecolor('black')
    cmap = plt.get_cmap('berlin')
    norm = Normalize(vmin=-3, vmax=3)  # Ajustable selon tes écarts attendus

    ref_start = pd.Timestamp("2024-05-10 00:00:00")
    ref_end = pd.Timestamp("2024-05-10 01:30:00")

    for name, cam in Fripon.items():
        full_df = cam.df.copy()

        # Synchroniser le fuseau horaire si besoin
        if full_df.index.tz is not None:
            ref_start_tz = ref_start.tz_localize(full_df.index.tz)
            ref_end_tz = ref_end.tz_localize(full_df.index.tz)
        else:
            ref_start_tz = ref_start
            ref_end_tz = ref_end

        # Calcul de la moyenne entre 00h00 et 01h30
        ref_period = full_df.loc[ref_start_tz:ref_end_tz]
        if ref_period.empty:
            print(f"Avertissement : Pas de données pour la caméra {name} entre {ref_start_tz} et {ref_end_tz}")
            continue
        ref_lumd = ref_period['lumd'].mean()

        # Puis on filtre uniquement les données à afficher
        df = full_df.loc[x_min:x_max].copy()
        if df.empty:
            continue

        # Calcul des différences avec la moyenne
        df['delta_lumd'] = df['lumd'] - ref_lumd
        df['next_time'] = df.index.to_series().shift(-1)
        df['duration'] = (df['next_time'] - df.index.to_series()).fillna(pd.Timedelta(minutes=10))
        df = df.dropna()

        qd_lat = cam.qdlat
        ax.barh(
            y=[qd_lat] * len(df),
            width=df["duration"],
            left=df.index,
            height=0.2,
            color=cmap(norm(df["delta_lumd"])),
            edgecolor="none"
        )

    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel("Magnetic QD Latitude (°)")
    ax.set_ylim(lat_min, lat_max)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.tick_params(axis='x', rotation=30)

    sm = ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    plt.colorbar(sm, ax=ax, label="Δ Brightness (mag/arcsec²) from 00:00–01:30 Mean")
    plt.title("Brightness Variation by Magnetic QD Latitude")
    plt.tight_layout()
    out = f"{output_path}\\Delta_Brightness_mean.png"
    plt.savefig(out, dpi=150)
    plt.show()
    plt.close()
    print(out)
    

def main():
    Fripon = load_fripon_data(r"C:\Users\Olivi\Documents\Doc\AurorAlpes\COMEA\Outils\Fripon\Ovalpes\fripon_data_complet.json")
    Magnetometre = load_magneto_data(r"C:\Users\Olivi\Documents\Doc\AurorAlpes\COMEA\Outils\Fripon\Ovalpes\magneto_data.json")
    output_path = r"C:\Users\Olivi\Documents\Doc\AurorAlpes\COMEA\Outils\Fripon\Ovalpes\graph\test"
    last = {}
    magnetos = list(Magnetometre.keys())
    cameras = list(Fripon.keys())
  
    #CHOOSE DATETIME
    x_min = pd.to_datetime("2024-05-10T21:00", format="%Y-%m-%dT%H:%M") #Put 21h30 to avoid day light
    x_max = pd.to_datetime("2024-05-11T2:30", format="%Y-%m-%dT%H:%M")
    
    #CHOOSE BRIGHTNESS Y-AXIS LIMITS
    y_min = 16                                                          
    y_max = 21          #21.8 mag/arcsec² is a really dark sky

    ############# CHOOSE WHAT TO PLOT ###############

    # ploteuropetest(Fripon, cameras, Magnetometre, magnetos, x_min, x_max, y_min, y_max, output_path, last)                #PLOT MAP OF EUROPE
    # ploteuropedelta(Fripon, cameras, Magnetometre, magnetos, x_min, x_max, y_min, y_max, output_path, last, ref_time_str="2024-05-10 21:40")
    # plot_graph(Magnetometre, Fripon, x_min, x_max, y_min, y_max, output_path)                                         #PLOT GRAPH OF CLOSEST CAM AND MAG 
    
    ##STACK PLOT##
    # stack_mags = ["ESK", "HAD", "CLF", "EBR"]         #Around 82,13 magnetic longitude
    # stack_mags = ["HLP", "BEL", "PEG"]                #Around 104,27 magnetic longitude
    # stack_mags = ["FUR", "THY"]                       #Around 97,37 magnetic longitude
    # plot_graph_stack(Magnetometre, Fripon, x_min, x_max, y_min, y_max, stack_mags, output_path)                       #PLOT STACK GRAPH OF CLOSEST CAM AND MAG
    
    ##EXPERIMENTAL##
    # plot_all_cameras(Fripon, x_min, x_max, y_min, y_max, lat_transition=46)                                             #ALL CAM IN ONE GRAPH (hard to read)
    # plot_brightness_vs_qd_latitude(Fripon, x_min, x_max, lat_min=30, lat_max=52, y_min=y_min, y_max=y_max, output_path=output_path)
    # plot_brightness_delta_vs_qd_latitude(Fripon, x_min, x_max, lat_min=30, lat_max=52, output_path=output_path)
    # plot_brightness_delta_vs_qd_latitude_mean(Fripon, x_min, x_max, lat_min=30, lat_max=52, output_path=output_path)

if __name__ == "__main__":
    main()
