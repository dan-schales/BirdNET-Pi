import argparse
import os
import sqlite3
import textwrap
from datetime import datetime
from time import sleep

import matplotlib.font_manager as font_manager
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import rcParams
from matplotlib.colors import LogNorm

from utils.helpers import DB_PATH, FONT_DIR, get_settings, get_font


def get_data(now=None):
    uri = f"file:{DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    if now is None:
        now = datetime.now()
    df = pd.read_sql_query(f"SELECT * from detections WHERE Date = DATE('{now.strftime('%Y-%m-%d')}')",
                           conn)

    # Convert Date and Time Fields to Panda's format
    df['Date'] = pd.to_datetime(df['Date'])
    df['Time'] = pd.to_datetime(df['Time'], unit='ns')

    # Add round hours to dataframe
    df['Hour of Day'] = [r.hour for r in df.Time]

    return df, now


# Function to show value on bars
def show_values_on_bars(ax, label, is_dark=False):
    for i, p in enumerate(ax.patches):
        x = p.get_x() + p.get_width() + 0.5
        y = p.get_y() + p.get_height() / 2
        value = '{:n}'.format(p.get_width())
        color = '#aaa' if is_dark else '#666'
        ax.text(x, y, value, ha='left', va='center', size=9, color=color, fontweight='500')


def wrap_width(txt):
    # try to estimate wrap width
    w = 16
    for c in txt:
        if c in ['M', 'm', 'W', 'w']:
            w -= 0.33
        if c in ['I', 'i', 'j', 'l']:
            w += 0.33
    return round(w)


def create_plot(df_plt_today, now, is_top=None):
    if is_top is not None:
        readings = 10
        if is_top:
            plt_selection_today = (df_plt_today['Sci_Name'].value_counts()[:readings])
        else:
            plt_selection_today = (df_plt_today['Sci_Name'].value_counts()[-readings:])
    else:
        plt_selection_today = df_plt_today['Sci_Name'].value_counts()
        readings = len(df_plt_today['Sci_Name'].value_counts())

    df_plt_selection_today = df_plt_today[df_plt_today.Sci_Name.isin(plt_selection_today.index)]

    conf = get_settings()
    is_dark = conf['COLOR_SCHEME'] == "dark"

    # Modern color scheme
    if is_dark:
        facecolor = '#1e1e1e'
        text_color = '#e0e0e0'
        grid_color = '#333333'
        bar_edge = '#1e1e1e'
        heatmap_line = '#1e1e1e'
        title_color = '#b0b0b0'
        tick_color = '#aaaaaa'
        highlight_color = '#5eeaa0'
    else:
        facecolor = '#ffffff'
        text_color = '#2d2d2d'
        grid_color = '#f0f0f0'
        bar_edge = '#ffffff'
        heatmap_line = '#ffffff'
        title_color = '#666666'
        tick_color = '#666666'
        highlight_color = '#1a6b3c'

    # Set up plot axes and titles
    height = max(readings / 3, 0) + 1.06

    f, axs = plt.subplots(1, 2, figsize=(10, height), gridspec_kw=dict(width_ratios=[3, 6]),
                          facecolor=facecolor)

    for ax in axs:
        ax.set_facecolor(facecolor)

    # generate y-axis order for all figures based on frequency
    freq_order = df_plt_selection_today['Sci_Name'].value_counts().index

    # make color for max confidence
    confmax = df_plt_selection_today.groupby('Sci_Name')['Confidence'].max()
    confmax = confmax.reindex(freq_order)

    # norm values for color palette
    norm = plt.Normalize(confmax.values.min(), confmax.values.max())
    if is_top or is_top is None:
        if is_dark:
            # Dark theme: vibrant teal-green gradient
            from matplotlib.colors import LinearSegmentedColormap
            dark_greens = LinearSegmentedColormap.from_list('dark_greens', ['#1a5c3a', '#2e9e6a', '#5eeaa0'])
            colors = dark_greens(norm(confmax)).tolist()
            pal_heatmap = LinearSegmentedColormap.from_list('dark_heat', ['#1a3328', '#2e9e6a', '#5eeaa0'])
        else:
            # Light theme: clean teal-green gradient
            from matplotlib.colors import LinearSegmentedColormap
            modern_greens = LinearSegmentedColormap.from_list('modern_greens', ['#b2dfdb', '#4db6ac', '#1a6b3c'])
            colors = modern_greens(norm(confmax)).tolist()
            pal_heatmap = LinearSegmentedColormap.from_list('modern_heat', ['#e8f5e9', '#66bb6a', '#1a6b3c'])

        if is_top:
            plot_type = "Top"
        else:
            plot_type = 'All'
        name = "Combo"
    else:
        from matplotlib.colors import LinearSegmentedColormap
        if is_dark:
            modern_reds = LinearSegmentedColormap.from_list('dark_reds', ['#4a1a1a', '#c04040', '#ff7070'])
        else:
            modern_reds = LinearSegmentedColormap.from_list('modern_reds', ['#ffcdd2', '#ef5350', '#b71c1c'])
        colors = modern_reds(norm(confmax)).tolist()
        pal_heatmap = modern_reds
        plot_type = "Bottom"
        name = "Combo2"

    # Generate frequency plot with modern styling
    plot = sns.countplot(y='Sci_Name', hue='Sci_Name', legend=False, data=df_plt_selection_today,
                         palette=dict(zip(confmax.index, colors)), order=freq_order, ax=axs[0],
                         edgecolor=bar_edge, linewidth=0.5)

    # Print count values next to bars (not on them)
    show_values_on_bars(axs[0], confmax, is_dark)

    # Style the bar chart axis
    axs[0].spines['top'].set_visible(False)
    axs[0].spines['right'].set_visible(False)
    axs[0].spines['bottom'].set_color(grid_color)
    axs[0].spines['left'].set_visible(False)
    axs[0].tick_params(axis='y', length=0)
    axs[0].tick_params(axis='x', colors=tick_color, labelsize=8)
    axs[0].xaxis.label.set_color(tick_color)
    axs[0].grid(axis='x', color=grid_color, linewidth=0.5, alpha=0.5)

    # Set y-axis labels to common names
    names_key = df_plt_today.sort_values('Time', ascending=False).groupby('Sci_Name').first()['Com_Name']
    common_names = [names_key[tick_label.get_text()] for tick_label in plot.get_yticklabels()]
    yticklabels = ['\n'.join(textwrap.wrap(ticklabel, wrap_width(ticklabel))) for ticklabel in common_names]
    yticks = plot.get_yticks()
    plot.set_yticks(yticks)
    plot.set_yticklabels(yticklabels, fontsize=10, color=text_color)
    plot.set(ylabel=None)
    plot.set(xlabel="Detections")

    # Generate crosstab matrix for heatmap plot
    heat = pd.crosstab(df_plt_selection_today['Sci_Name'], df_plt_selection_today['Hour of Day'])

    # Order heatmap Birds by frequency of occurrence
    heat.index = pd.CategoricalIndex(heat.index, categories=freq_order)
    heat.sort_index(level=0, inplace=True)

    hours_in_day = pd.Series(data=range(0, 24))
    heat_frame = pd.DataFrame(data=0, index=heat.index, columns=hours_in_day)
    heat = (heat+heat_frame).fillna(0)
    heat[heat == 0] = np.nan

    # Generate heatmap with modern styling
    annot_color = text_color
    heatmap = sns.heatmap(heat, norm=LogNorm(), annot=True,
                          annot_kws={"fontsize": 7, "color": annot_color},
                          fmt="g", cmap=pal_heatmap, square=False,
                          cbar=False, linewidths=1.5, linecolor=facecolor,
                          ax=axs[1], yticklabels=False)

    # Style heatmap axis
    axs[1].spines['top'].set_visible(False)
    axs[1].spines['right'].set_visible(False)
    axs[1].spines['bottom'].set_visible(False)
    axs[1].spines['left'].set_visible(False)
    axs[1].tick_params(axis='x', colors=tick_color, labelsize=8)
    axs[1].tick_params(axis='y', length=0)
    axs[1].xaxis.label.set_color(tick_color)

    # Highlight current hour
    for label in heatmap.get_xticklabels():
        if int(label.get_text()) == now.hour:
            label.set_color(highlight_color)
            label.set_fontweight('bold')

    heatmap.set_xticklabels(heatmap.get_xticklabels(), rotation=0, size=8)
    heatmap.set(ylabel=None)
    heatmap.set(xlabel="Hour of Day")

    # Title
    y = 1 - 8 / (height * 100)
    plt.suptitle(f"{plot_type} {readings}  |  {now.strftime('%Y-%m-%d %H:%M')}",
                 y=y, color=title_color, fontsize=11, fontweight='400')
    f.tight_layout()
    top = 1 - 40 / (height * 100)
    f.subplots_adjust(left=0.125, right=0.95, top=top, wspace=0.02)

    # Save with transparency for dark mode, white bg for light
    save_name = os.path.expanduser(f"~/BirdSongs/Extracted/Charts/{name}-{now.strftime('%Y-%m-%d')}.png")
    plt.savefig(save_name, facecolor=facecolor, edgecolor='none', dpi=120, bbox_inches='tight',
                pad_inches=0.2)
    plt.show()
    plt.close()


def load_fonts():
    # Add every font at the specified location
    font_dir = [FONT_DIR]
    for font in font_manager.findSystemFonts(font_dir, fontext='ttf'):
        font_manager.fontManager.addfont(font)
    # Set font family globally
    rcParams['font.family'] = get_font()['font.family']


def main(daemon, sleep_m):
    load_fonts()
    last_run = None
    while True:
        now = datetime.now()
        if last_run and now.day != last_run.day:
            print("getting yesterday's dataset")
            yesterday = last_run.replace(hour=23, minute=59)
            data, time = get_data(yesterday)
        else:
            data, time = get_data(now)
        if not data.empty:
            create_plot(data, time)
        else:
            print('empty dataset')
        if daemon:
            last_run = now
            sleep(60 * sleep_m)
        else:
            break


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--daemon', action='store_true')
    parser.add_argument('--sleep', default=2, type=int, help='Time between runs (minutes)')
    args = parser.parse_args()
    main(args.daemon, args.sleep)
