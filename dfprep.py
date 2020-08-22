def prep_info_df(info_df, category, col_dates, col_location, col_categories=None, col_values=None, long=False, roll_avg=False):
    """
    Prepares info_df for processing:
        1. Focus on relevant information: 'location', 'date' and the category to be tracked
        2. Pivot table so locations are indexes and dates are now columns
        3. Interpolate values so there are no gaps
        4. (Optional) Roll averages with 7-day windows to smooth out highly unstable values
        5. Fill NaN with 0: applies to eariler dates since we used interpolation already.

    roll_avg : bool, optional
            indicates whether or not to apply a rolling average 
            to smooth out highly variable data
    """
    temp_df = info_df
    
    if long:
        temp_df = long2wide(info_df=info_df, category=category, col_categories=col_categories, col_values=col_values)

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
    return temp_df

def long2wide(info_df, category, col_categories, col_values):
    temp_df = info_df.groupby([col_categories]).get_group(category)
    temp_df.drop(columns=[col_categories], inplace=True)
    temp_df.rename(columns={col_values: category}, inplace=True)
    return temp_df

def prep_geom_df(geom_df, location_col, geometry_col):
    clean_geom_df = geom_df.rename(columns={location_col: 'location'})
    clean_geom_df = clean_geom_df[['location', geometry_col]]
    clean_geom_df.set_index('location', inplace=True)
    return clean_geom_df

def merge_info_geom_df(info_df, geom_df):
    """
    Merges info_df with geom_df.
    Returns a dataframe with geographical information and relevant data to be tracked,
    indexed by location.
    """
    merged_df = geom_df.merge(info_df, on='location', how='left')
    return merged_df

# def prep_uru_info_df(info_df, column, roll_avg=True):
#     clean_info_df = info_df.groupby(['Indicador']).get_group(column)
#     clean_info_df.drop('Indicador', axis=1, inplace=True)
#     clean_info_df.rename(columns={
#                          'Fecha': 'date', 'Territorio': 'location', 'Valor': column}, inplace=True)
#     clean_info_df = prep_info_df(clean_info_df, column=column, roll_avg=roll_avg)
#     return clean_info_df


