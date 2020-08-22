import pandas as pd
import geopandas as gpd

import numpy as np

from datetime import date, timedelta, datetime
from dateutil.parser import *
from babel.dates import format_date

import os

from IPython.display import Image, Video, HTML, IFrame, display
from moviepy.editor import *

import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib import colors
from matplotlib import cm
from matplotlib.ticker import ScalarFormatter, MaxNLocator
from mpl_toolkits.axes_grid1 import make_axes_locatable

import contextily as ctx

class ChoroMap():
    """ 
    A class for building animated choropleth maps. 
      
    Attributes: 
        column : str 
            the name of the column to focus on from the informational dataframe
        
        info_df : pd.DataFrame
            the informational dataframe containing data to be tracked
        
        map_df : pd.DataFrame
            the dataframe containing geometrical information for building maps
        
        
    """
    def __init__(self, merged_df):
        self.merged_df = merged_df

    def choro_map(self, title, subtitle, unit, save_name, 
                    labels=True, lang='en', video=True, fig_size=(16,8), 
                    color='OrRd', count='all', norm=colors.Normalize, fps=8):
        """
        Usually only method that needs to be called externally. 
        It calls for the whole process of creating the maps and turning them into gifs and/or videos.
        
        Parameters:
            title : str
                Title to be displayed above the map
            save_name : str
                Name to be used in exports (static map images, gifs, videos) and directory paths
            video : bool
                If true, a video will be created. If left at default False, only a gif will be created and displayed.
            labels : bool
                If true, the make_static_maps method will insert labels in -hopefully- safe regions of the map
            lang : language code for babel.format_date, passed to pretty_date method
            fig_size : tuple (height, width)
                Size for the figure.
            color : passes to cmap option in Pandas plot function, which in turn uses Matplotlib Colormaps. 
                Information and options here: https://matplotlib.org/3.1.0/tutorials/colors/colormaps.html
                Some of my favorites are 'OrRd', 'gist_heat_r', 'copper_r' .
                (the _r at the end reverses the color sequence)
            count : 'all' or int > 1
                Number of maps to be created.
            norm : Normalization class to use for mapping values into the colormap. 
                The classes are part of Matplotlib module colors. 
                colors.Normalize provides linear normalization
                colors.LogNorm provides logarithmic normalization
            fps : int
                Frames per second - passed to make_gif method,
                then as an argument to gifski
        """        
        png_output_path = f'charts/maps/{save_name}'
        self.create_png_directory(png_output_path=png_output_path)
        self.delete_static_maps(png_output_path=png_output_path)
        self.make_static_maps(merged_df=self.merged_df, title=title, subtitle=subtitle, unit=unit, labels=labels, lang=lang, 
                                fig_size=fig_size, color=color, count=count, norm=norm, png_output_path=png_output_path)
        self.create_exports_directory()
        self.make_gif(fps=fps, save_name=save_name, png_output_path=png_output_path)
        if video:
            self.make_video(save_name=save_name)
            return self.display_video(save_name=save_name)
        else:
            return self.display_gif(save_name=save_name)

    def make_static_maps(self, merged_df, title, subtitle, unit, labels, lang, fig_size, color, count, norm, png_output_path):
        """
        Called by choro_map method to draw all static maps, then close the figure window 
        so it doesn't render in Notebook automatically.
        """
        fig, ax, cax, tax, vmin, vmax = self.build_figure(merged_df=merged_df, fig_size=fig_size, norm=norm)
        list_of_dates = self.get_dates(merged_df=merged_df, count=count)

        # OrRd_clrs = cm.get_cmap('OrRd', 256)
        # w_OrRd_clrs = OrRd_clrs(np.linspace(0, 1, 256))
        # white = np.array([256/256, 256/256, 256/256, 1])
        # w_OrRd_clrs[:1, :] = white
        # w_OrRd = colors.ListedColormap(w_OrRd_clrs)

        for date in list_of_dates:
            # https://geopandas.org/reference.html#geopandas.GeoDataFrame.plot
            ax = merged_df.plot(column=date, ax=ax, cax=cax, cmap=color, alpha=1,
                    linewidth=0.2, edgecolor='0.8', vmin=vmin, vmax=vmax, 
                    legend=True, norm=norm(vmin=vmin, vmax=vmax),
                    legend_kwds={'orientation': "vertical"})
            # fig.delaxes(fig.get_axes()[1])
            if labels:
                merged_df.apply(lambda x: ax.annotate(s=x.name, xy=x.geometry.centroid.coords[0], 
                    **{"fontsize": "x-small", "ha": "center", "va": "top"}), axis=1)
            # ctx.add_basemap(
            #     ax=ax, source=ctx.providers.OpenStreetMap.Mapnik)
            
            self.make_timeline(tax=tax, list_of_dates=list_of_dates, date=date, lang=lang)
            self.format_plot(fig=fig, ax=ax, cax=cax, date=date, title=title, subtitle=subtitle, unit=unit, lang=lang)
            self.save_and_clear_fig(ax=ax, tax=tax, date=date, png_output_path=png_output_path)
        plt.close()
            
    def build_figure(self, merged_df, fig_size, norm):
        """
        Builds the figure to be used in all maps. The figure includes a main axis (ax) that will contain the maps
        and a secondary axis containing the colorbar (cax).
        It also sets the minimum and maximum values for the graph. 
        It finds the maximum value by looking at the whole table except the 'geometry' column.
        """
        plt.style.use('ggplot')
        
        fig, ax = plt.subplots(1, 1, figsize=fig_size)

        divider = make_axes_locatable(ax)
        tax = divider.append_axes("bottom", size="1%", pad=0.3)
        # tax = fig.add_axes([0.4, 0.12, 0.3, 0.01])

        # cax = divider.append_axes("right", size="3%", pad=0.3)
        cax = fig.add_axes([0.8, 0.25, 0.01, 0.5])
        
        
        
        vmax = merged_df.iloc[:, 1:].max().max()
        if norm == colors.LogNorm:
            vmin = 1
        else:
            vmin = 0


        return (fig, ax, cax, tax, vmin, vmax)

    def format_plot(self, fig, ax, cax, date, title, subtitle, unit, lang):
        """
        Format title, date and colorbar ticks.
        
        Arguments:
            fig : fig created in build_figure
            ax : axis created in build_figure, plotted in make_static_maps
            date : date from the iterable in make_static_maps
            title : entered by user when calling choro_map method
        """        

        # light_blue = '#d4f6ff'
        # dark_blue = '#132157'
        # plt.rcParams['savefig.facecolor'] = dark_blue

        # COLOR = 'white'
        # rcParams['text.color'] = COLOR
        # rcParams['axes.titlecolor'] = COLOR
        # rcParams['axes.labelcolor'] = COLOR
        # rcParams['xtick.color'] = COLOR
        # rcParams['ytick.color'] = COLOR
        fig.suptitle(title, fontsize=15, weight='bold')
        ax.set_title(subtitle, fontsize=12)        
        ax.set_axis_off()
        ax.text(0, 0, self.pretty_date(date, lang), fontdict={
                'fontsize': 12}, transform=ax.transAxes)

        # cb = ax.get_figure().get_axes()[1]
        # ###
        # # Possibly include LogFormatter() and LogLocator() in case of LogNorm
        # # https://matplotlib.org/3.3.0/api/ticker_api.html
        # ###
        cax.yaxis.set_major_formatter(ScalarFormatter())
        cax.yaxis.set_major_locator(MaxNLocator())
        cax.set_ylabel(unit)
        cax.yaxis.set_label_position('left')
    
    def make_timeline(self, tax, list_of_dates, date, lang):
        tax.barh(1, (list_of_dates.index(date)+1)/len(list_of_dates), color='Blue', alpha=0.5)
        tax.yaxis.set_visible(False)
        
        lim_date = lambda x: self.pretty_date(list_of_dates[x], lang=lang, format='medium')
        tax.set_xlim(lim_date(0), lim_date(-1))

    def save_and_clear_fig(self, ax, tax, date, png_output_path):
        """
        Save static figure, then clear ax to avoid memory over-use.
        
        Attributes:
            ax : axis plotted in make_static_maps
            date : date from the iterable in make_static_maps 
            png_output_path : str passed from self.choro_map()
        """
        filepath = os.path.join(png_output_path, date+'.png')

        plt.savefig(filepath, dpi=100)
        ax.clear()
        tax.clear()
            
    def delete_static_maps(self, png_output_path):
        os.system(f'rm ./{png_output_path}/*')
    
    def create_png_directory(self, png_output_path):
        """
        Create the directory where static maps (png) will be saved 
        if it doesn't exist already.
        """
        if not os.path.exists(png_output_path):
            os.makedirs(png_output_path)

    def create_exports_directory(self):
        """
        Create the directory where exports (gifs, videos) will be saved 
        if it doesn't exist already.
        """
        if not os.path.exists('charts/exports'):
            os.makedirs('charts/exports')
        
    @staticmethod
    def pretty_date(ugly_date, lang, format='long'):
        """
        Converts a date from 'yyyy-mm-dd' to 'Month day, Year' to project on the map.
        Example: 02-01-2020 -> February 01, 2020
        lang 
        """
        ugly_datetime = datetime.strptime(ugly_date, '%Y-%m-%d')
        pretty_date = format_date(ugly_datetime, format=format, locale=lang)
        return pretty_date

        # return datetime.strptime(ugly_date, '%Y-%m-%d').strftime('%B %d, %Y')
    
    def get_dates(self, merged_df, count):
        """
        A function to get a list of dates to process for the map.
            Parameters:
                merged_df: pd.Dataframe returned from get_merged_df
                count: 'all' or int higher than 1 representing the number of days to include in the animated map
            Returns:
                list_of_dates: list
        """
        begin_date = date.fromisoformat(merged_df.columns.min())

        most_recent_date = date.fromisoformat(merged_df.columns[-1])
        day = timedelta(days=1)

        if count == 'all':
            end_date = most_recent_date + day
        elif isinstance(count, int) and count > 1:
            end_date = begin_date + (day*count)
        else: raise ValueError('Invalid count: must be "all" or an integer higher than 1')

        list_of_dates = [(begin_date + timedelta(n)).__str__() \
                         for n in range(int((end_date - begin_date).days))]

        return list_of_dates
            
    def make_gif(self, fps, save_name, png_output_path):
        os.system(f'gifski -o ./charts/exports/{save_name}.gif ./{png_output_path}/*.png --fps {fps} --fast')

    def display_gif(self, save_name):
        HTML(f'<iframe src="charts/exports/{save_name}.gif" frameborder="0" allowfullscreen></iframe>')
        
    def make_video(self, save_name):
        my_clip = VideoFileClip(f"charts/exports/{save_name}.gif")
        my_clip.write_videofile(f"charts/exports/{save_name}.mp4", logger=None)
        
    def display_video(self, save_name):
        return HTML(f"""<video width='640' height='480' controls>
                <source src='charts/exports/{save_name}.mp4'>
                Your browser does not support the video tag.</video>""")

