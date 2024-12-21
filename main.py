import pandas as pd
import streamlit as st
import altair as alt
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# READING THE CSV FILE AND TIDYING UP
df = pd.read_csv("hdb_data_preprocessed.csv.gz", compression='gzip')
df['floor_area_sf'] = np.ceil(df['floor_area_sf'])
df['resale_psf'] = np.ceil(df['resale_psf'])
df['year'] = df['year'].astype(int)


# WEB CONFIGURATION
st.set_page_config(page_title="HDB Resale Dashboard",
                   page_icon=":house:",
                   layout="wide",
                   initial_sidebar_state="collapsed")
st.title(":house: HDB Resale Value Dashboard")
st.divider()


# USER CONFIGURATION
with st.container():
    col1, col2, col3 = st.columns(3)

    with col1:
        interval_mapping = {
            "Yearly": "year",
            "Quarterly": "year_quarter",
            "Monthly": "year_month"
        }
        selected_display_interval = st.selectbox(
            label="Select Interval",
            options=list(interval_mapping.keys()),
            index=0
        )
        selected_chart_interval = interval_mapping[selected_display_interval]

    with col2:
        interest_mapping = {
            "Price": "resale_price",
            "PSF": "resale_psf"
        }
        selected_display_interest = st.selectbox(
            label="Select Interest",
            options=list(interest_mapping.keys()),
            index=1
        )
        selected_chart_interest = interest_mapping[selected_display_interest]

    start_year, end_year = st.select_slider(
        "Select the range of Year",
        options=range(df['year'].min(), df['year'].max()+1),
        value=(df['year'].min(), df['year'].max()),
        label_visibility="visible"
    )

    with col3:
        selected_display_change = st.selectbox(
            label="Select Change",
            options=['Relative', 'Absolute'],
            index=0
        )

    df_filter_year = df[(df['year'] >= start_year) & (df['year'] <= end_year)]

    latest_date = df_filter_year['year_month'].max()
    earliest_date = df_filter_year['year_month'].min()

    st.markdown(f"{selected_display_interval} {selected_display_interest} data is selected between {earliest_date} and {latest_date}.<br>"
                f"The charts will display :red[{selected_display_change.lower()}] change in :red[{selected_display_interest.lower()}].",
                unsafe_allow_html=True)
    st.divider()
# CHART SETTINGS
smooth_window = 5
chart_height = 500
ytick = 50000 if selected_chart_interest == "resale_price" else 50

# QUICK FUN METRICS
with st.container():

    col1, col2, col3, col4 = st.columns(4)

    # Column for highest PSF
    with col1:
        tx_highest_psf = df_filter_year.loc[df_filter_year['resale_psf'].idxmax(
        )]
        highest_resale_psf_value = int(tx_highest_psf['resale_psf'])
        st.metric(label='Highest PSF Sold',
                  value=f"${highest_resale_psf_value}")
        st.markdown(
            f":orange[{tx_highest_psf['block']} {tx_highest_psf['street_name']}<br>"
            f"{tx_highest_psf['flat_type']}, STOREY {tx_highest_psf['storey_range_bin']}<br>"
            f"Sold at ${tx_highest_psf['resale_price']:,.0f} on {tx_highest_psf['year']}-{tx_highest_psf['month']}]",
            unsafe_allow_html=True
        )

    # Column for lowest PSF
    with col2:
        tx_lowest_psf = df_filter_year.loc[df_filter_year['resale_psf'].idxmin(
        )]
        lowest_resale_psf_value = int(tx_lowest_psf['resale_psf'])
        st.metric(label='Lowest PSF Sold',
                  value=f"${lowest_resale_psf_value}")
        st.markdown(
            f":orange[{tx_lowest_psf['block']} {tx_lowest_psf['street_name']}<br>"
            f"{tx_lowest_psf['flat_type']}, STOREY {tx_lowest_psf['storey_range_bin']}<br>"
            f"Sold at ${tx_lowest_psf['resale_price']:,.0f} on {tx_lowest_psf['year']}-{tx_lowest_psf['month']}]",
            unsafe_allow_html=True
        )

    num_year = end_year - start_year + 1
    town_counts = df['town'].value_counts()

    with col3:
        most_common_town = town_counts.idxmax()
        most_common_count = town_counts.max()

        st.metric(label='Most Transactions/Year',
                  value=f"{int(most_common_count/num_year)}",)
        st.markdown(
            f":orange[{most_common_town}]",
            unsafe_allow_html=True
        )

    with col4:
        town_counts = df['town'].value_counts()
        least_common_town = town_counts.idxmin()
        least_common_count = town_counts.min()

        st.metric(label='Least Transactions/Year',
                  value=f"{int(least_common_count/num_year)}",)
        st.markdown(
            f":orange[{least_common_town}]",
            unsafe_allow_html=True
        )

# Price vs Time
with st.container():

    # Group the data and calculate Q1, Median, and Q3
    df_stats = df_filter_year.groupby([selected_chart_interval])[selected_chart_interest].agg(
        q1=lambda x: x.quantile(0.25),
        median='median',
        q3=lambda x: x.quantile(0.75)
    ).reset_index()

    if selected_display_change == 'Relative':
        # Calculate relative percentage changes for Q1, Median, and Q3
        df_stats['q1'] = (
            (df_stats['q1'] - df_stats['q1'].iloc[0]) / df_stats['q1'].iloc[0]) * 100
        df_stats['median'] = (
            (df_stats['median'] - df_stats['median'].iloc[0]) / df_stats['median'].iloc[0]) * 100
        df_stats['q3'] = (
            (df_stats['q3'] - df_stats['q3'].iloc[0]) / df_stats['q3'].iloc[0]) * 100

    # Prepare data for shading (long format)
    df_area = pd.concat([
        df_stats[[selected_chart_interval, 'q1']].rename(
            columns={'q1': selected_chart_interest}),
        df_stats[[selected_chart_interval, 'q3']].rename(
            columns={'q3': selected_chart_interest})
    ])
    df_area['type'] = ['Q1'] * len(df_stats) + ['Q3'] * len(df_stats)

    # Plot the median line
    fig = px.line(
        df_stats,
        x=selected_chart_interval,
        y='median',
        labels={f"{selected_chart_interval}": 'Year',
                'median': f"Median {selected_chart_interest}"},
        title=f"HDB Median {selected_display_interest}",
        height=chart_height
    )

    # Add the IQR area using traces
    fig.add_traces([
        dict(
            type='scatter',
            x=pd.concat([df_stats[selected_chart_interval],
                        df_stats[selected_chart_interval][::-1]]),
            y=pd.concat([df_stats['q1'], df_stats['q3'][::-1]]),
            fill='toself',
            fillcolor='rgba(0, 100, 250, 0.2)',
            line=dict(color='rgba(255,255,255,0)'),
            showlegend=False
        )
    ])

    # Update layout
    fig.update_layout(
        xaxis_title="",
        yaxis_title="",
        xaxis=dict(tickmode='auto'),
        yaxis=dict(dtick=ytick if selected_display_change ==
                   "Absolute" else 10),
        showlegend=False
    )

    # Show the chart in Streamlit
    st.plotly_chart(fig, use_container_width=True)


# CAGR HEAT MAP
with st.container():

    st.header("Change in Resale Value Over Time",
              anchor=None, help=None, divider=False)

    col1, col2 = st.columns(2)

    with col1:
        # Step 1: Calculate the yearly median resale price
        grouped_data = df_filter_year.groupby(
            'year')['resale_price'].median().reset_index()
        grouped_data = grouped_data.rename(
            columns={'resale_price': 'median_price'})

        # Step 2: Prepare an empty DataFrame to store percentage changes
        years_later = range(5, 20)  # Time gaps: 5 to 15 years
        heatmap_data = pd.DataFrame(
            index=grouped_data['year'], columns=years_later)

        # Step 3: Calculate percentage changes for each start year and time gap
        for diff in years_later:
            future_years = grouped_data['year'] + diff  # Compute future years
            merged = grouped_data.merge(
                grouped_data, left_on=future_years, right_on='year', suffixes=('', '_future'))
            merged['percent_change'] = (
                (merged['median_price_future'] - merged['median_price']) / merged['median_price']) * 100

            # Store the percentage change for the given time gap
            heatmap_data[diff] = merged.set_index('year')['percent_change']

        heatmap_data_cleaned = heatmap_data.dropna(how='all')

        zmin = heatmap_data_cleaned.min().min()  # Minimum value in the data
        zmax = heatmap_data_cleaned.max().max()  # Maximum value in the data

        # Step 4: Interactive Heatmap using Plotly
        fig = go.Figure(
            data=go.Heatmap(
                z=heatmap_data_cleaned.values,
                x=heatmap_data_cleaned.columns,
                y=heatmap_data_cleaned.index,
                colorscale='RdBu',  # Diverging color map for percentage changes
                colorbar=dict(title='Change (%)'),
                zmid=0,
                zmin=zmin,  # Minimum value for color scale
                zmax=zmax,  # Maximum value for color scale
                # Directly display values in cells
                text=[[f"{v:.1f}" for v in row]
                      for row in heatmap_data_cleaned.values],
                # Customize hover template
                hovertemplate="Year Bought: %{y}<br>Duration of Ownership: %{x} Years<br>Change: %{z:.2f}%")
        )

        fig.update_layout(
            title="Percentage Change",
            xaxis_title="Duration of Ownership",
            yaxis_title="Year Bought",
            height=chart_height,
            xaxis=dict(
                # List of positions to show the ticks
                tickvals=list(heatmap_data_cleaned.columns),
            ),
            yaxis=dict(
                # List of positions to show the ticks
                tickvals=list(heatmap_data_cleaned.index)
            ))

        # Display in Streamlit
        st.plotly_chart(fig, use_container_width=True)

    with col2:

        # Step 1: Calculate the yearly median resale price
        grouped_data = df_filter_year.groupby(
            'year')['resale_price'].median().reset_index()
        grouped_data = grouped_data.rename(
            columns={'resale_price': 'median_price'})

        # Step 2: Prepare an empty DataFrame to store annualized percentage changes
        years_later = range(5, 20)  # Time gaps: 5 to 19 years
        heatmap_data = pd.DataFrame(
            index=grouped_data['year'], columns=years_later)

        # Step 3: Calculate annualized percentage changes for each start year and time gap
        for diff in years_later:
            future_years = grouped_data['year'] + diff  # Compute future years
            merged = grouped_data.merge(
                grouped_data, left_on=future_years, right_on='year', suffixes=('', '_future'))

            # Calculate the annualized percentage change using the CAGR formula
            merged['annualized_change'] = (
                ((merged['median_price_future'] /
                 merged['median_price']) ** (1 / diff)) - 1
            ) * 100  # Convert to percentage

            # Store the annualized percentage change for the given time gap
            heatmap_data[diff] = merged.set_index('year')['annualized_change']

        # Step 4: Drop rows with all missing values (NaN)
        heatmap_data_cleaned = heatmap_data.dropna(how='all')

        zmin = heatmap_data_cleaned.min().min()  # Minimum value in the data
        zmax = heatmap_data_cleaned.max().max()  # Maximum value in the data

        # Step 4: Interactive Heatmap using Plotly with direct value display in cells
        fig = go.Figure(
            data=go.Heatmap(
                z=heatmap_data_cleaned.values,
                x=heatmap_data_cleaned.columns,
                y=heatmap_data_cleaned.index,
                colorscale='RdBu',  # Diverging color map for annualized changes
                colorbar=dict(title='Change (%)'),
                zmid=0,  # Centered around 0
                zmin=zmin,  # Minimum value for color scale
                zmax=zmax,  # Maximum value for color scale
                # Directly display values in cells
                text=[[f"{v:.2f}" for v in row]
                      for row in heatmap_data_cleaned.values],
                # Customize hover template
                hovertemplate="Year Bought: %{y}<br>Duration of Ownership: %{x} Years<br>Annual Change: %{z:.2f}%"
                # Disable hover information as it's redundant
            )
        )

        # Custom Y-axis labels and values
        fig.update_layout(
            title="Annualized Percentage Change",
            xaxis_title="Duration of Ownership",
            yaxis_title="Year Bought",
            height=chart_height,
            xaxis=dict(
                # List of positions to show the ticks
                tickvals=list(heatmap_data_cleaned.columns),
            ),
            yaxis=dict(
                # List of positions to show the ticks
                tickvals=list(heatmap_data_cleaned.index)
            )
        )

        # Display in Streamlit
        st.plotly_chart(fig, use_container_width=True)

with st.container():
    st.header("Resale Value by Geographical Region",
              anchor=None, help=None, divider=False)

    df_sub = df_filter_year.groupby([selected_chart_interval, 'geographical_location'])[
        selected_chart_interest].median().reset_index()

    if selected_display_change == "Relative":
        # Compute relative percentage change for each geographical location
        df_sub['relative_change'] = df_sub.groupby('geographical_location')[selected_chart_interest].transform(
            lambda x: ((x - x.iloc[0]) / x.iloc[0]) * 100
        )

    fig1 = px.line(data_frame=df_sub,
                   x=selected_chart_interval,
                   y=selected_chart_interest if selected_display_change == "Absolute" else "relative_change",
                   color="geographical_location",
                   height=chart_height)
    fig1.update_layout(
        legend_title_text='',
        xaxis_title="",
        yaxis_title="",
        xaxis=dict(tickmode='auto'),
        yaxis=dict(dtick=ytick if selected_display_change ==
                   "Absolute" else 10),
        legend=dict(
            orientation="h",  # Horizontal legend
            yanchor="top",    # Align the top of the legend box
            y=1.1,           # Push it below the chart; adjust this value as needed
            xanchor="center",  # Center the legend horizontally
            x=0.5             # Position it at the center of the chart
        ), margin=dict(b=50)     # Adjust bottom margin to ensure legend fits
    )

    st.plotly_chart(fig1,
                    use_container_width=True)

    df_sub = df_filter_year.groupby([selected_chart_interval, 'geographical_location', 'town'])[
        selected_chart_interest].median().reset_index()

    col1, col2 = st.columns(2)

    with col1:

        location = "Central"
        df_geo = df_sub[(df_sub["geographical_location"]
                         == location)].copy()

        # Apply rolling median for each town separately
        df_geo[selected_chart_interest] = df_geo.groupby('town')[selected_chart_interest].transform(
            lambda x: x.rolling(window=smooth_window, min_periods=1).median())

        if selected_display_change == "Relative":
            # Compute relative percentage change for each geographical location
            df_geo['relative_change'] = df_geo.groupby('town')[selected_chart_interest].transform(
                lambda x: ((x - x.iloc[0]) / x.iloc[0]) * 100
            )

        fig1 = px.line(data_frame=df_geo,
                       x=selected_chart_interval,
                       y=selected_chart_interest if selected_display_change == "Absolute" else "relative_change",
                       labels={f"{selected_chart_interval}": 'Year',
                               f'{selected_chart_interest}': 'Resale Value',
                               'town': "Town"},
                       color="town",
                       title=f"{location.upper()} REGION",
                       height=chart_height)

        fig1.update_layout(
            legend_title_text='',
            xaxis_title="",
            yaxis_title="",
            xaxis=dict(tickmode='auto'),
            yaxis=dict(dtick=ytick if selected_display_change ==
                       "Absolute" else 10),
        )
        st.plotly_chart(fig1,
                        use_container_width=True)

    with col2:
        location = "West"
        df_geo = df_sub[(df_sub["geographical_location"]
                         == location)].copy()

        # Apply rolling median for each town separately
        df_geo[selected_chart_interest] = df_geo.groupby('town')[selected_chart_interest].transform(
            lambda x: x.rolling(window=smooth_window, min_periods=1).median())

        if selected_display_change == "Relative":
            # Compute relative percentage change for each geographical location
            df_geo['relative_change'] = df_geo.groupby('town')[selected_chart_interest].transform(
                lambda x: ((x - x.iloc[0]) / x.iloc[0]) * 100
            )

        fig1 = px.line(data_frame=df_geo,
                       x=selected_chart_interval,
                       y=selected_chart_interest if selected_display_change == "Absolute" else "relative_change",
                       labels={f"{selected_chart_interval}": 'Year',
                               f"{selected_chart_interest}": 'Resale Value',
                               'town': "Town"},
                       color="town",
                       title=f"{location.upper()} REGION",
                       height=chart_height)

        fig1.update_layout(
            legend_title_text='',
            xaxis_title="",
            yaxis_title="",
            xaxis=dict(tickmode='auto'),
            yaxis=dict(dtick=ytick if selected_display_change ==
                       "Absolute" else 10),
        )
        st.plotly_chart(fig1,
                        use_container_width=True)

    col1, col2, col3 = st.columns(3)
    with col1:

        location = "North"
        df_geo = df_sub[(df_sub["geographical_location"]
                         == location)].copy()

        # Apply rolling median for each town separately
        df_geo[selected_chart_interest] = df_geo.groupby('town')[selected_chart_interest].transform(
            lambda x: x.rolling(window=smooth_window, min_periods=1).median())

        if selected_display_change == "Relative":
            # Compute relative percentage change for each geographical location
            df_geo['relative_change'] = df_geo.groupby('town')[selected_chart_interest].transform(
                lambda x: ((x - x.iloc[0]) / x.iloc[0]) * 100
            )

        fig1 = px.line(data_frame=df_geo,
                       x=selected_chart_interval,
                       y=selected_chart_interest if selected_display_change == "Absolute" else "relative_change",
                       labels={f"{selected_chart_interval}": 'Year',
                               f'{selected_chart_interest}': 'Resale Value',
                               'town': "Town"},
                       color="town",
                       title=f"{location.upper()} REGION",
                       height=chart_height)
        fig1.update_layout(
            legend_title_text='',
            xaxis_title="",
            yaxis_title="",
            xaxis=dict(tickmode='auto'),
            yaxis=dict(dtick=ytick if selected_display_change ==
                       "Absolute" else 10),
        )
        st.plotly_chart(fig1,
                        use_container_width=True)
    with col2:

        location = "North-East"
        df_geo = df_sub[(df_sub["geographical_location"]
                         == location)].copy()

        # Apply rolling median for each town separately
        df_geo[selected_chart_interest] = df_geo.groupby('town')[selected_chart_interest].transform(
            lambda x: x.rolling(window=smooth_window, min_periods=1).median())

        if selected_display_change == "Relative":
            # Compute relative percentage change for each geographical location
            df_geo['relative_change'] = df_geo.groupby('town')[selected_chart_interest].transform(
                lambda x: ((x - x.iloc[0]) / x.iloc[0]) * 100
            )

        fig1 = px.line(data_frame=df_geo,
                       x=selected_chart_interval,
                       y=selected_chart_interest if selected_display_change == "Absolute" else "relative_change",
                       labels={f"{selected_chart_interval}": 'Year',
                               f'{selected_chart_interest}': 'Resale Value',
                               'town': "Town"},
                       color="town",
                       title=f"{location.upper()} REGION",
                       height=chart_height)
        fig1.update_layout(
            legend_title_text='',
            xaxis_title="",
            yaxis_title="",
            xaxis=dict(tickmode='auto'),
            yaxis=dict(dtick=ytick if selected_display_change ==
                       "Absolute" else 10),
        )
        st.plotly_chart(fig1,
                        use_container_width=True)
    with col3:

        location = "East"
        df_geo = df_sub[(df_sub["geographical_location"]
                         == location)].copy()

        # Apply rolling median for each town separately
        df_geo[selected_chart_interest] = df_geo.groupby('town')[selected_chart_interest].transform(
            lambda x: x.rolling(window=smooth_window, min_periods=1).median())

        if selected_display_change == "Relative":
            # Compute relative percentage change for each geographical location
            df_geo['relative_change'] = df_geo.groupby('town')[selected_chart_interest].transform(
                lambda x: ((x - x.iloc[0]) / x.iloc[0]) * 100
            )

        fig1 = px.line(data_frame=df_geo,
                       x=selected_chart_interval,
                       y=selected_chart_interest if selected_display_change == "Absolute" else "relative_change",
                       labels={f"{selected_chart_interval}": 'Year',
                               f'{selected_chart_interest}': 'Resale Value',
                               'town': "Town"},
                       color="town",
                       title=f"{location.upper()} REGION",
                       height=chart_height)
        fig1.update_layout(
            legend_title_text='',
            xaxis_title="",
            yaxis_title="",
            xaxis=dict(tickmode='auto'),
            yaxis=dict(dtick=ytick if selected_display_change ==
                       "Absolute" else 10),
        )
        st.plotly_chart(fig1,
                        use_container_width=True)
        


with st.container():
    st.header("Resale Value by Flat Type",
              anchor=None, help=None, divider=False)

    df_sub = df_filter_year.groupby([selected_chart_interval, 'flat_type'])[
        selected_chart_interest].median().reset_index()

    if selected_display_change == "Relative":
        # Compute relative percentage change for each geographical location
        df_sub['relative_change'] = df_sub.groupby('flat_type')[selected_chart_interest].transform(
            lambda x: ((x - x.iloc[0]) / x.iloc[0]) * 100
        )

    fig1 = px.line(data_frame=df_sub,
                   x=selected_chart_interval,
                   y=selected_chart_interest if selected_display_change == "Absolute" else "relative_change",
                   color="flat_type",
                   height=chart_height)
    fig1.update_layout(
        legend_title_text='',
        xaxis_title="",
        yaxis_title="",
        xaxis=dict(tickmode='auto'),
        yaxis=dict(dtick=ytick if selected_display_change ==
                   "Absolute" else 10),
        legend=dict(
            orientation="h",  # Horizontal legend
            yanchor="top",    # Align the top of the legend box
            y=1.1,           # Push it below the chart; adjust this value as needed
            xanchor="center",  # Center the legend horizontally
            x=0.5             # Position it at the center of the chart
        ), margin=dict(b=50)     # Adjust bottom margin to ensure legend fits
    )

    st.plotly_chart(fig1,
                    use_container_width=True)

with st.container():
    st.header("Resale Value by Lease Commence Year",
              anchor=None, help=None, divider=False)

    df_sub = df_filter_year.groupby([selected_chart_interval, 'lease_commence_bin'])[
        selected_chart_interest].median().reset_index()

    if selected_display_change == "Relative":
        # Compute relative percentage change
        df_sub['relative_change'] = df_sub.groupby('lease_commence_bin')[selected_chart_interest].transform(
            lambda x: ((x - x.iloc[0]) / x.iloc[0]) * 100
        )

    fig1 = px.line(data_frame=df_sub,
                   x=selected_chart_interval,
                   y=selected_chart_interest if selected_display_change == "Absolute" else "relative_change",
                   color="lease_commence_bin",
                   height=chart_height)
    fig1.update_layout(
        legend_title_text='',
        xaxis_title="",
        yaxis_title="",
        xaxis=dict(tickmode='auto'),
        yaxis=dict(dtick=ytick if selected_display_change ==
                   "Absolute" else 10),
        legend=dict(
            orientation="h",  # Horizontal legend
            yanchor="top",    # Align the top of the legend box
            y=1.1,           # Push it below the chart; adjust this value as needed
            xanchor="center",  # Center the legend horizontally
            x=0.5             # Position it at the center of the chart
        ), margin=dict(b=50)     # Adjust bottom margin to ensure legend fits
    )

    st.plotly_chart(fig1,
                    use_container_width=True)



# flat_type = st.sidebar.multiselect(label="Select Flat Type",
#                                    options=df['flat_type'].unique())
# town = st.sidebar.multiselect(label="Select Town",
#                               options=df['town'].unique())
# lease_commence_bin = st.sidebar.multiselect(label="Select Lease Commence Bin",
#                                             options=df['lease_commence_bin'].unique())

# df_selection = df.query(
#     "flat_type == @flat_type & town == @town & lease_commence_bin == @lease_commence_bin"
# )


# col_1, col_2, col_3, col_4 = st.columns(4)

# with col_1:
#     st.metric("L3M Highest PSF ($)",
#               l3m_highest_psf)
#     st.metric("L3M Lowest PSF ($)",
#               l3m_lowest_psf)

# with col_2:
#     st.metric("L6M Highest PSF ($)",
#               l6m_highest_psf)
#     st.metric("L6M Lowest PSF ($)",
#               l6m_lowest_psf)

# with col_3:
#     st.metric("L12M Highest PSF ($)",
#               l12m_highest_psf)
#     st.metric("L12M Lowest PSF ($)",
#               l12m_lowest_psf)

# with col_4:
#     st.metric("L5Y Highest PSF ($)",
#               l5y_highest_psf)
#     st.metric("L5Y Lowest PSF ($)",
#               l5y_lowest_psf)


# TO SEE STOREY
# df_sub = df_filter_year.groupby([selected_chart_interval, 'storey_range_bin'])[
#     'resale_price'].median().reset_index()

# fig1 = px.line(data_frame=df_sub,
#             x=selected_chart_interval,
#             y="resale_price",
#             color="storey_range_bin",
#             title="Median Resale Price by Storey Range",
#             height=chart_height)

# st.plotly_chart(fig1,
#                 use_container_width=True)

# df_sub = df_filter_year.groupby([selected_chart_interval, 'estate_type'])[
#     'resale_price'].median().reset_index()

# fig1 = px.line(data_frame=df_sub,
#             x=selected_chart_interval,
#             y="resale_price",
#             color="estate_type",
#             title="Median Resale Price by Estate",
#             height=chart_height)

# fig1.update_layout(showlegend=True, legend_title_text='')


# st.plotly_chart(fig1,
#                 use_container_width=True)

# For user to see
with st.expander("View Data"):
    selected_columns = ['year_month', 'estate_type', 'geographical_location', 'town', 'flat_type', 'block', 'street_name',
                        'storey_range_bin', 'flat_model', 'floor_area_sf', 'lease_commence_date', 'remaining_lease', 'resale_price', 'resale_psf']
    df_rearranged = df[selected_columns]

    csv = df_rearranged.to_csv(index=False).encode('utf8')
    st.dataframe(df_rearranged,
                 height=200,
                 hide_index=True,
                 use_container_width=True)
    st.download_button('Download CSV File',
                       data=csv,
                       file_name="Resale_Prices_HDB.csv")


# # Group by year_quarter and calculate Q1, Q3, and Median
# stats = df.groupby("year_quarter")["resale_price"].agg(
#     q1_price=lambda x: x.quantile(0.25),
#     median_price="median",
#     q3_price=lambda x: x.quantile(0.75)
# ).reset_index()

# # Create a base chart for x-axis
# base = alt.Chart(stats).encode(
#     x=alt.X("year_quarter:O", title="Time")
# )

# # Median line
# median_line = base.mark_line(color="yellow").encode(
#     y=alt.Y("median_price:Q", title="Price ($)")
# )

# # IQR area
# iqr_area = base.mark_area(opacity=0.1, color="yellow").encode(
#     y=alt.Y("q1_price:Q", title=None),
#     y2="q3_price:Q"  # Upper boundary of the IQR

# )

# # Combine median line and IQR area
# chart = (iqr_area + median_line).properties(
#     width=600,
#     height=600,
#     title="Median Price and IQR Range"
# )

# # Display chart in Streamlit
# st.altair_chart(chart, use_container_width=True)
