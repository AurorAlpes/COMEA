import json
import math
import heapq
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import colors, cm
from mpl_toolkits.basemap import Basemap


class cameraclass:
    def __init__(self, data):
        self.name = data.get('name', None)
        self.lon  = float(data['lon'])
        self.lat  = float(data['lat'])
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
    # on prend le premier magnétomètre pour récupérer la série de temps
    df_base = Magnetometre[magnetos[0]].df
    times = df_base.loc[x_min:x_max].index

    for t in times:
        fig, ax = plt.subplots(figsize=(12,12))
        m = Basemap(projection='merc',
                    llcrnrlat=35, urcrnrlat=65,
                    llcrnrlon=-20, urcrnrlon=40,
                    resolution='i', ax=ax)
        m.drawcoastlines()
        m.drawcountries()
        m.drawmapboundary(fill_color='gray')
        m.fillcontinents('black', lake_color='gray')

        # --- Caméras ---
        norm_cam = colors.Normalize(vmin=y_min, vmax=y_max)
        for cam_name, cam in Fripon.items():
            # Essaye la mesure au temps t
            if t in cam.df.index:
                val = cam.df.at[t, 'lumd']
                last[cam_name] = t
            else:
                # pas de mesure nouvelle → réutilise la dernière
                if cam_name not in last:
                    continue  # jamais eu de mesure
                t_last = last[cam_name]
                val = cam.df.at[t_last, 'lumd']

            x, y = m(cam.lon, cam.lat)
            m.plot(x, y, 'o', markersize=8, color=plt.cm.Greys(norm_cam(val)))

        # norm_mag = colors.Normalize(
        #     vmin=df_base['H'].min(),
        #     vmax=df_base['H'].max()
        # )
        # for mag_name, mag in Magnetometre.items():
        #     if t in mag.df.index:
        #         val = mag.df.at[t, 'H']
        #         last[mag_name] = t
        #     else:
        #         if mag_name not in last:
        #             continue
        #         t_last = last[mag_name]
        #         val = mag.df.at[t_last, 'H']

        #     x, y = m(mag.lon, mag.lat)
        #     m.plot(x, y, 's', markersize=6, color=plt.cm.inferno(norm_mag(val)))

        # colorbar fripon
        sm_cam = cm.ScalarMappable(cmap=plt.cm.Greys, norm=norm_cam)
        sm_cam.set_array([])
        cbar_cam = plt.colorbar(sm_cam, ax=ax, pad=0.02, fraction=0.04)
        cbar_cam.set_label("Brightness (mag/arcsec²)", fontsize=10)

        # Colorbar magnetos
        # sm_mag = cm.ScalarMappable(cmap=plt.cm.inferno, norm=norm_mag)
        # sm_mag.set_array([])
        # cbar_mag = plt.colorbar(sm_mag, ax=ax, pad=0.02, fraction=0.04, location='right')
        # cbar_mag.set_label("H component (nT)", fontsize=10)

        plt.title(t.strftime("%Y-%m-%d %H:%M"))
        out_file = f"{output_path}\\{t:%Y%m%dT%H%M}.png"
        print(f"{output_path}\\{t:%Y%m%dT%H%M}")
        plt.savefig(out_file, dpi=200)
        plt.close()



def main():
    Fripon = load_fripon_data(r"C:\Users\Olivi\Documents\Doc\AurorAlpes\COMEA\Outils\Fripon\Ovalpes\fripon_data.json")
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
    y_max = 21.8          #21.8 mag/arcsec² is a really dar sky

    ############# CHOOSE WHAT TO PLOT ###############

    ploteurope(Fripon, cameras, Magnetometre, magnetos, x_min, x_max, y_min, y_max, output_path, last)                #PLOT MAP OF EUROPE

    # plot_graph(Magnetometre, Fripon, x_min, x_max, y_min, y_max, output_path)                                         #PLOT GRAPH OF CLOSEST CAM AND MAG 
    
    ##STACK PLOT##
    # stack_mags = ["ESK", "HAD", "CLF", "EBR"]         #Around 82,13 magnetic longitude
    # stack_mags = ["HLP", "BEL", "PEG"]                #Around 104,27 magnetic longitude
    # stack_mags = ["FUR", "THY"]                       #Around 97,37 magnetic longitude
    # plot_graph_stack(Magnetometre, Fripon, x_min, x_max, y_min, y_max, stack_mags, output_path)                       #PLOT STACK GRAPH OF CLOSEST CAM AND MAG
    
    ##EXPERIMENTAL##
    # plot_all_cameras(Fripon, x_min, x_max, y_min, y_max, lat_transition=46)                                             #ALL CAM IN ONE GRAPH (hard to read)

if __name__ == "__main__":
    main()
