def prep_info_df(info_df, column, roll_avg=False):
    """
    Prepares info_df for processing:
        1. Focus on relevant information: 'location', 'date' and the column to be tracked
        2. Pivot table so locations are indexes and dates are now columns
        3. Interpolate values so there are no gaps
        4. (Optional) Roll averages with 7-day windows to smooth out highly unstable values
        5. Fill NaN with 0: applies to eariler dates since we used interpolation already.

    roll_avg : bool, optional
            indicates whether or not to apply a rolling average 
            to smooth out highly variable data
    """
    temp_df = info_df[['location', 'date', column]]
    temp_df = temp_df.pivot_table(
        index='location', columns='date', values=column)
    temp_df.interpolate(
        method='linear', limit_direction='forward', axis=1, inplace=True)
    if roll_avg:
        temp_df = temp_df.rolling(7, axis=1).mean()
    temp_df.fillna(0, inplace=True)
    return temp_df


def prep_uru_info_df(info_df, column, roll_avg=True):
    clean_info_df = info_df.groupby(['Indicador']).get_group(column)
    clean_info_df.drop('Indicador', axis=1, inplace=True)
    clean_info_df.rename(columns={
                         'Fecha': 'date', 'Territorio': 'location', 'Valor': column}, inplace=True)
    clean_info_df = prep_info_df(clean_info_df, column=column, roll_avg=roll_avg)
    return clean_info_df
