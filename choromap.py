import pandas as pd
import geopandas as gpd

import numpy as np

from datetime import date, timedelta, datetime
from dateutil.parser import *
from babel.dates import format_date

import os

from IPython.display import Image, Video, HTML, IFrame, display
# from moviepy.editor import *

import matplotlib.pyplot as plt
from matplotlib import colors
from matplotlib.ticker import ScalarFormatter, MaxNLocator
from mpl_toolkits.axes_grid1 import make_axes_locatable

class ChoroMapBuilder():
    """ 
    A class for building animated choropleth maps. 
      
    Attributes: 
        merged_df : pd.DataFrame
            DataFrame containing locations in the index, dates in the columns and one column with Shapely geometries
    """
    def __init__(self, merged_df):
        self.merged_df = merged_df

    def make_map(self, title, subtitle, unit, save_name, 
                    labels=True, lang='en', fig_size=(16,8), 
                    color='OrRd', count='all', begin_date=None, norm=colors.Normalize, fps=8):
        """
        It calls for the whole process of creating the maps and turning them into videos.
        
        Parameters:
            title : str
                Title to be displayed above the map
            subtitle : str
                Possible use is to reference the source of the data
            unit : str
                Units for colorbar
            save_name : str
                Name to be used in exports (static map images, gifs, videos) and directory paths
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
            begin_date : str
                Date formatted as yyyy-mm-dd to match dates in merged_df
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
                                fig_size=fig_size, color=color, count=count, begin_date=begin_date, norm=norm, png_output_path=png_output_path)
        
        self.create_exports_directory()
        self.make_video(fps=fps, png_output_path=png_output_path, save_name=save_name)
        return self.display_video(save_name=save_name)

    def make_static_maps(self, merged_df, title, subtitle, unit, labels, lang, fig_size, color, count, begin_date, norm, png_output_path):
        """
        Called by make_map method to draw all static maps, then close the figure window 
        so it doesn't render in Notebook automatically.
        """
        fig, ax, cax, tax, vmin, vmax = self.build_figure(merged_df=merged_df, fig_size=fig_size, norm=norm)
        list_of_dates = self.get_dates(merged_df=merged_df, count=count, begin_date=begin_date)

        file_num = 0

        for date in list_of_dates:
            # https://geopandas.org/reference.html#geopandas.GeoDataFrame.plot
            ax = merged_df.plot(column=date, ax=ax, cax=cax, cmap=color, alpha=1,
                    linewidth=1.5, edgecolor='white', vmin=vmin, vmax=vmax, 
                    legend=True, norm=norm(vmin=vmin, vmax=vmax),
                    legend_kwds={'orientation': "vertical"})

            if labels:
                merged_df.apply(lambda x: ax.annotate(s=x.name, xy=x.geometry.centroid.coords[0], 
                    **{"fontsize": "x-small", "ha": "center", "va": "top"}), axis=1)
            
            self.make_timeline(tax=tax, list_of_dates=list_of_dates, date=date, lang=lang)
            self.format_plot(fig=fig, ax=ax, cax=cax, date=date, title=title, subtitle=subtitle, unit=unit, lang=lang)
            
            file_num = str(file_num).zfill(4)
            self.save_and_clear_fig(ax=ax, tax=tax, file_num=file_num, png_output_path=png_output_path)
            file_num = int(file_num) + 1

        plt.close()
            
    def build_figure(self, merged_df, fig_size, norm):
        """
        Builds the figure to be used in all maps. The figure includes a main axis (ax) that will contain the maps
        Additional axes: timeline (tax) and colorbar (cax).
        It also sets the minimum and maximum values for the graph. 
        It finds the maximum value by looking at the whole table except the 'geometry' column.
        """
        plt.style.use('ggplot')
        
        fig, ax = plt.subplots(1, 1, figsize=fig_size, dpi=200)

        divider = make_axes_locatable(ax)
        tax = divider.append_axes("bottom", size="1%", pad=0.3)

        cax = fig.add_axes([0.85, 0.25, 0.01, 0.5])
        
        vmax = merged_df.iloc[:, 1:].max().max()
        if norm == colors.LogNorm:
            vmin = 1
        else:
            vmin = 0

        return (fig, ax, cax, tax, vmin, vmax)

    def format_plot(self, fig, ax, cax, date, title, subtitle, unit, lang):
        """
        Add title, subtitle, date, colorbar units, colorbar ticks.
        """       
        # Add title
        fig.suptitle(title, fontsize=15, weight='bold')
        
        # Add subtitle
        ax.set_title(subtitle, fontsize=12)        
        ax.set_axis_off()
        
        # Add date on the bottom-left
        ax.text(0, 0, self.pretty_date(date, lang), fontdict={
                'fontsize': 12}, transform=ax.transAxes)

        # Format colorbar
        cax.yaxis.set_major_formatter(ScalarFormatter())
        cax.yaxis.set_major_locator(MaxNLocator())
        cax.set_ylabel(unit)
        cax.yaxis.set_label_position('left')
    
    def make_timeline(self, tax, list_of_dates, date, lang):
        tax.barh(1, (list_of_dates.index(date)+1)/len(list_of_dates), color='Blue', alpha=0.5)
        tax.yaxis.set_visible(False)
        
        lim_date = lambda x: self.pretty_date(list_of_dates[x], lang=lang, format='medium')
        tax.set_xlim(lim_date(0), lim_date(-1))

    def save_and_clear_fig(self, ax, tax, file_num, png_output_path):
        """
        Save static figure, then clear ax to avoid memory over-use.
        
        Attributes:
            ax : axis plotted in make_static_maps
            date : date from the iterable in make_static_maps 
            png_output_path : str passed from self.choro_map()
        """
        filepath = os.path.join(png_output_path, file_num+'.png')

        plt.savefig(filepath)
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
    
    def get_dates(self, merged_df, count, begin_date):
        """
        A function to get a list of dates to process for the map.
            Parameters:
                merged_df: pd.Dataframe returned from get_merged_df
                count: 'all' or int higher than 1 representing the number of days to include in the animated map
            Returns:
                list_of_dates: list
        """
        if begin_date is None:
            begin_date = merged_df.columns.min()
        
        begin_date = date.fromisoformat(begin_date)

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
            
    def make_video(self, fps, png_output_path, save_name):
        os.system(f"""ffmpeg -y -f image2 -r 6 -i {png_output_path}/%04d.png -vcodec libx264 -crf 25 -pix_fmt yuv420p ./charts/exports/{save_name}.mp4""")

    def display_video(self, save_name):
        return HTML(f"""<video width='640' height='480' controls>
                <source src='charts/exports/{save_name}.mp4'>
                Your browser does not support the video tag.</video>""")

class DataFramePrepper():
    """
    A class for manipulating informational and geospatial dataframes in preparation for using ChoroMapBuilder.
    
    Attributes:
        info_df : pd.DataFrame
            the informational dataframe containing values to be tracked

        map_df : pd.DataFrame
            the dataframe containing geometrical information for building maps
    """
    def __init__(self, info_df, geom_df):
        self.info_df = info_df
        self.geom_df = geom_df

    def prep_info_df(self, category, col_dates, col_location, col_categories=None, col_values=None, long=False, roll_avg=False, info_df=None):
        """
        Prepares info_df for processing:
            1. Focus on relevant information: dates, locations and category to be tracked
            2. Pivot table so locations are indexes and dates are now columns
            3. Interpolate values so there are no gaps
            4. (Optional) Roll averages with 7-day windows to smooth out highly unstable values
            5. Fill NaN with 0: applies to eariler dates since we used interpolation already.
        
        category : str 
            the name of the column to focus on from the informational dataframe. 
            For dataframes in 'long' format, the category to focus on from col_categories
        col_dates : str
            the name of the column that contains dates
        col_location : the name of the column that contains the locations (e.g. 'States', 'Countries', etc.)
        col_values : applicable for dataframes in 'long' formats
        long : bool
            whether the dataframe is in a wide (False) or long (True) format
        roll_avg : bool, optional
                indicates whether or not to apply a rolling average 
                to smooth out highly variable data
        info_df : parameter used for testing. In practice, info_df will take the value of self.info_df, initialized along with the DataFramePrepper instance
        """
        if info_df is None:
            info_df = self.info_df
        
        if long:
            temp_df = self.long2wide(info_df=info_df, category=category,
                                col_categories=col_categories, col_values=col_values)
        else:
            temp_df = info_df

        temp_df.rename(columns={col_dates: 'date',
                                col_location: 'location'}, inplace=True)

        temp_df = temp_df[['location', 'date', category]]
        temp_df = temp_df.pivot_table(
            index='location', columns='date', values=category, dropna=False)
        temp_df.interpolate(
            method='linear', limit_direction='forward', axis=1, inplace=True)

        if roll_avg:
            temp_df = temp_df.rolling(7, axis=1).mean()

        temp_df.fillna(0, inplace=True)

        self.ready_info_df = temp_df
        return self.ready_info_df

    @staticmethod
    def long2wide(info_df, category, col_categories, col_values):
        temp_df = info_df.groupby([col_categories]).get_group(category)
        temp_df.drop(columns=[col_categories], inplace=True)
        temp_df.rename(columns={col_values: category}, inplace=True)
        return temp_df


    def prep_geom_df(self, location_col, geometry_col, geom_df=None):
        if geom_df is None:
            geom_df = self.geom_df

        temp_df = geom_df
        temp_df = temp_df.rename(columns={location_col: 'location'})
        temp_df = temp_df[['location', geometry_col]]
        temp_df.set_index('location', inplace=True)
        
        self.ready_geom_df = temp_df
        return self.ready_geom_df


    def merge_info_geom(self, info_df=None, geom_df=None):
        """
        Merges info_df with geom_df.
        Returns a dataframe with geographical information and relevant data to be tracked,
        indexed by location.
        The returned dataframe will then be passed as an argument when initializing ChoroMapBuilder
        """
        if info_df is None:
            info_df = self.ready_info_df
        
        if geom_df is None:
            geom_df = self.ready_geom_df

        temp_df = geom_df.merge(info_df, on='location', how='left')

        self.merged_df = temp_df
        return self.merged_df
