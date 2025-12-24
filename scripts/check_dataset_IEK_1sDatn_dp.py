#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def _save_or_show(fig, out_path: str | None, save_figs: bool):
    """
    If save_figs=True, save figure to out_path and close it (avoid memory leak).
    If save_figs=False, keep it open for plt.show().
    """
    if save_figs:
        if out_path is None:
            raise ValueError("out_path is required when save_figs=True")
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close(fig)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("csv_path", help="Ruta al CSV (24h o el que tengas)")
    p.add_argument("--time-col", default="Time", help="Nombre columna tiempo")
    p.add_argument("--v-col", default="NRE DCbus U", help="Nombre columna tensión DC bus")
    p.add_argument("--p-col", default="Nachladung P", help="Nombre columna potencia (opcional)")
    p.add_argument("--sep", default=",", help="Separador CSV")
    p.add_argument(
        "--dvdt-th",
        type=float,
        default=0.2,
        help="Umbral para 'evento' en V/s (p.ej. 0.2 V/s). Ajusta según tu ruido.",
    )
    p.add_argument("--plot-top", type=int, default=10, help="Cuantos top eventos por |dv/dt| mostrar en zoom")
    p.add_argument("--window-s", type=int, default=120, help="Ventana +- segundos alrededor del evento")
    p.add_argument("--save-figs", action="store_true", help="Guardar PNGs en ./out_plots/check_dataset_IEK_1sDatn_dp/")
    p.add_argument("--max-zoom-plots", type=int, default=20, help="Limite de zoom plots para no generar demasiados")

    args = p.parse_args()

    # Output dir
    out_dir = os.path.join(os.getcwd(), "out_plots")
    if args.save_figs:
        os.makedirs(out_dir, exist_ok=True)

    # Leer
    df = pd.read_csv(args.csv_path, sep=args.sep)

    # Parse time
    if args.time_col not in df.columns:
        raise ValueError(f"No encuentro columna de tiempo: {args.time_col}. Columnas: {list(df.columns)}")

    df[args.time_col] = pd.to_datetime(df[args.time_col], errors="coerce")
    df = df.dropna(subset=[args.time_col]).sort_values(args.time_col).reset_index(drop=True)

    # Columnas objetivo
    if args.v_col not in df.columns:
        raise ValueError(f"No encuentro columna de tensión: {args.v_col}. Columnas: {list(df.columns)}")

    v = pd.to_numeric(df[args.v_col], errors="coerce")
    t = df[args.time_col]

    # dt en segundos (puede haber jitter)
    dt = t.diff().dt.total_seconds()
    dv = v.diff()

    # dv/dt (V/s). Evita división por 0 o NaN
    dvdt = dv / dt.replace(0, np.nan)

    df["dv_V"] = dv
    df["dt_s"] = dt
    df["dvdt_Vps"] = dvdt

    # Métricas básicas
    v_clean = v.dropna()
    dvdt_clean = dvdt.dropna()

    print("=== Resumen tensión (V) ===")
    print(f"Muestras: {len(v_clean)}")
    print(f"Min: {v_clean.min():.3f}  Max: {v_clean.max():.3f}  P2P: {(v_clean.max()-v_clean.min()):.3f}")
    print(f"Media: {v_clean.mean():.3f}  Std: {v_clean.std():.3f}")

    print("\n=== Resumen dv/dt (V/s) ===")
    print(f"Muestras dv/dt: {len(dvdt_clean)}")
    print(f"Min: {dvdt_clean.min():.6f}  Max: {dvdt_clean.max():.6f}")
    print(f"Media: {dvdt_clean.mean():.6f}  Std: {dvdt_clean.std():.6f}")
    print(f"P95(|dv/dt|): {np.percentile(np.abs(dvdt_clean), 95):.6f}")
    print(f"P99(|dv/dt|): {np.percentile(np.abs(dvdt_clean), 99):.6f}")

    # Detectar "eventos" por umbral
    events = df.index[np.abs(df["dvdt_Vps"]) >= args.dvdt_th].to_list()
    print(f"\n=== Eventos por |dv/dt| >= {args.dvdt_th} V/s ===")
    print(f"Count: {len(events)}")
    if len(events) > 0:
        sample = events[:10]
        print("Primeros eventos:")
        for i in sample:
            print(f"  {df.loc[i, args.time_col]}  V={df.loc[i, args.v_col]:.3f}  dv/dt={df.loc[i, 'dvdt_Vps']:.3f}")

    # Top eventos + zoom plots
    if len(events) > 0:
        df_events = df.loc[events].copy()
        df_events["abs_dvdt"] = np.abs(df_events["dvdt_Vps"])
        df_top = df_events.sort_values("abs_dvdt", ascending=False).head(args.plot_top)

        print("\n=== Eventos con mayor |dv/dt| ===")
        for _, row in df_top.iterrows():
            print(f"  {row[args.time_col]}  V={row[args.v_col]:.3f}  dv/dt={row['dvdt_Vps']:.3f}")

        for k, (_, row) in enumerate(df_top.iterrows(), start=1):
            if k > args.max_zoom_plots:
                break

            t0 = row[args.time_col]
            t_start = t0 - pd.Timedelta(seconds=args.window_s)
            t_end = t0 + pd.Timedelta(seconds=args.window_s)

            w = df[(df[args.time_col] >= t_start) & (df[args.time_col] <= t_end)].copy()
            if w.empty:
                continue

            # 1) Voltage zoom
            fig, ax = plt.subplots()
            ax.plot(w[args.time_col], pd.to_numeric(w[args.v_col], errors="coerce"), label=args.v_col)
            ax.axvline(t0, linestyle="--", label="event")
            ax.set_title(f"Zoom V around event #{k} ({t0})")
            ax.set_xlabel("Time")
            ax.set_ylabel("Voltage (V)")
            ax.grid(True)
            ax.legend()

            out_path = None
            if args.save_figs:
                out_path = os.path.join(out_dir, f"zoom_{k:02d}_V.png")
            _save_or_show(fig, out_path, args.save_figs)

            # 2) dv/dt zoom
            fig, ax = plt.subplots()
            ax.plot(w[args.time_col], w["dvdt_Vps"], label="dv/dt (V/s)")
            ax.axhline(args.dvdt_th, linestyle="--", label="threshold")
            ax.axhline(-args.dvdt_th, linestyle="--")
            ax.axvline(t0, linestyle="--", label="event")
            ax.set_title(f"Zoom dV/dt around event #{k} ({t0})")
            ax.set_xlabel("Time")
            ax.set_ylabel("dV/dt (V/s)")
            ax.grid(True)
            ax.legend()

            out_path = None
            if args.save_figs:
                out_path = os.path.join(out_dir, f"zoom_{k:02d}_dvdt.png")
            _save_or_show(fig, out_path, args.save_figs)

            # 3) Power zoom (optional)
            if args.p_col in df.columns:
                pwr = pd.to_numeric(w[args.p_col], errors="coerce")
                fig, ax = plt.subplots()
                ax.plot(w[args.time_col], pwr, label=args.p_col)
                ax.axvline(t0, linestyle="--", label="event")
                ax.set_title(f"Zoom Power around event #{k} ({t0})")
                ax.set_xlabel("Time")
                ax.set_ylabel("Power")
                ax.grid(True)
                ax.legend()

                out_path = None
                if args.save_figs:
                    out_path = os.path.join(out_dir, f"zoom_{k:02d}_power.png")
                _save_or_show(fig, out_path, args.save_figs)

    # Plots globales (24h) solo si NO estás guardando figs
    # (si los quieres también como PNG, dímelo y los añadimos con flag aparte)
    if not args.save_figs:
        fig, ax = plt.subplots()
        ax.plot(t, v, label=args.v_col)
        ax.set_title("DC bus voltage")
        ax.set_xlabel("Time")
        ax.set_ylabel("Voltage (V)")
        ax.grid(True)
        ax.legend()

        fig, ax = plt.subplots()
        ax.plot(t, dvdt, label="dv/dt (V/s)")
        ax.axhline(args.dvdt_th, linestyle="--", label="threshold")
        ax.axhline(-args.dvdt_th, linestyle="--")
        ax.set_title("Voltage derivative")
        ax.set_xlabel("Time")
        ax.set_ylabel("dV/dt (V/s)")
        ax.grid(True)
        ax.legend()

        if args.p_col in df.columns:
            pwr = pd.to_numeric(df[args.p_col], errors="coerce")
            fig, ax = plt.subplots()
            ax.plot(t, pwr, label=args.p_col)
            ax.set_title("Power (reference)")
            ax.set_xlabel("Time")
            ax.set_ylabel("Power")
            ax.grid(True)
            ax.legend()

        plt.show()

    if args.save_figs:
        print(f"\nSaved plots to: {out_dir}")


if __name__ == "__main__":
    main()
