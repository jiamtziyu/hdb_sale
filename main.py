import pandas as pd
import streamlit as st
import altair as alt
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# READING THE CSV FILE AND TIDYING UP
df = pd.read_csv("hdb_data_preprocessed.csv.gz")
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
    col1, col2 = st.columns(2)

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
            index=0
        )
        selected_chart_interest = interest_mapping[selected_display_interest]

    start_year, end_year = st.select_slider(
        "Select the range of Year",
        options=range(df['year'].min(), df['year'].max()+1),
        value=(df['year'].min(), df['year'].max()),
        label_visibility="visible"
    )

    df_filter_year = df[(df['year'] >= start_year) & (df['year'] <= end_year)]

    latest_date = df_filter_year['year_month'].max()
    earliest_date = df_filter_year['year_month'].min()

    st.text(f"{selected_display_interval} {selected_display_interest} data is selected between {earliest_date} and {latest_date}.")

# CHART SETTINGS
smooth_window = 5
chart_height = 600
xtick = 50000 if selected_chart_interest == "resale_price" else 50

# Price vs Time
with st.container():

    # Group the data and calculate Q1, Median, and Q3
    df_stats = df_filter_year.groupby([selected_chart_interval])[selected_chart_interest].agg(
        q1=lambda x: x.quantile(0.25),
        median='median',
        q3=lambda x: x.quantile(0.75)
    ).reset_index()

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
        title=f"HDB Median {selected_display_interest} (All)",
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
        yaxis=dict(dtick=xtick),
        showlegend=False
    )

    # Show the chart in Streamlit
    st.plotly_chart(fig, use_container_width=True)


# CAGR HEAT MAP
with st.container():

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
                hovertemplate="Year Bought: %{y}<br>Duration of Ownership: %{x}<br>Change: %{z:.2f}%"  # Customize hover template
 # Display 'text' as the hover information

            )
        )

        fig.update_layout(
            title="Percentage Change in Resale Value Over Time",
            xaxis_title="Duration of Ownership",
            yaxis_title="Year Bought",
            height=800,
            xaxis=dict(
                tickmode='auto',  # Ensure every label is shown on the y-axis
                # List of positions to show the ticks
                tickvals=list(heatmap_data_cleaned.columns),
                # Corresponding labels
                ticktext=[f"{x}" for x in heatmap_data_cleaned.columns]
            ),
            yaxis=dict(
                tickmode='auto',  # Ensure every label is shown on the y-axis
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
                hovertemplate="Year Bought: %{y}<br>Duration of Ownership: %{x}<br>Annual Change: %{z:.2f}%"  # Customize hover template
# Disable hover information as it's redundant
            )
        )

        # Custom Y-axis labels and values
        fig.update_layout(
            title="Annualized Percentage Change in Resale Value Over Time",
            xaxis_title="Duration of Ownership",
            yaxis_title="Year Bought",
            height=800,
            xaxis=dict(
                # List of positions to show the ticks
                tickvals=list(heatmap_data_cleaned.columns),
                # Corresponding labels
                ticktext=[str(x) for x in heatmap_data_cleaned.columns]
            ),
            yaxis=dict(
                tickmode='auto',  # Ensure every label is shown on the y-axis
                # List of positions to show the ticks
                tickvals=list(heatmap_data_cleaned.index)
            )
        )

        # Display in Streamlit
        st.plotly_chart(fig, use_container_width=True)


# col1, col2 = st.columns(2)

# with col1:
#     df_sub = df_filter_year.groupby([chart_interval, 'geographical_location', 'town'])[
#         'resale_price'].median().reset_index()

#     unique_geographical_locations = df['geographical_location'].unique(
#     ).tolist()

#     for location in unique_geographical_locations:

#         df_geo = df_sub[(df_sub["geographical_location"] == location)].copy()

#         # Apply rolling median for each town separately
#         df_geo['resale_price'] = df_geo.groupby('town')['resale_price'].transform(
#             lambda x: x.rolling(window=smooth_window, min_periods=1).median())

#         fig1 = px.line(data_frame=df_geo,
#                        x=chart_interval,
#                        y="resale_price",
#                        labels={f"{chart_interval}": 'Year',
#                                'resale_price': 'Resale Value', 'town': "Town"},
#                        color="town",
#                        title=f"Median Resale Value by Town ({location.upper()})",
#                        height=chart_height)

#         st.plotly_chart(fig1,
#                         use_container_width=True)

# with col2:

#     df_sub = df_filter_year.groupby([chart_interval, 'geographical_location'])[
#         'resale_price'].median().reset_index()

#     fig1 = px.line(data_frame=df_sub,
#                    x=chart_interval,
#                    y="resale_price",
#                    color="geographical_location",
#                    title="Median Resale Price by Geographical Location",
#                    height=chart_height)

#     st.plotly_chart(fig1,
#                     use_container_width=True)

#     df_sub = df_filter_year.groupby([chart_interval, 'storey_range_bin'])[
#         'resale_price'].median().reset_index()

#     fig1 = px.line(data_frame=df_sub,
#                    x=chart_interval,
#                    y="resale_price",
#                    color="storey_range_bin",
#                    title="Median Resale Price by Storey Range",
#                    height=chart_height)

#     st.plotly_chart(fig1,
#                     use_container_width=True)

#     df_sub = df_filter_year.groupby([chart_interval, 'estate_type'])[
#         'resale_price'].median().reset_index()

#     fig1 = px.line(data_frame=df_sub,
#                    x=chart_interval,
#                    y="resale_price",
#                    color="estate_type",
#                    title="Median Resale Price by Estate",
#                    height=chart_height)

#     st.plotly_chart(fig1,
#                     use_container_width=True)


# flat_type = st.sidebar.multiselect(label="Select Flat Type",
#                                    options=df['flat_type'].unique())
# town = st.sidebar.multiselect(label="Select Town",
#                               options=df['town'].unique())
# lease_commence_bin = st.sidebar.multiselect(label="Select Lease Commence Bin",
#                                             options=df['lease_commence_bin'].unique())

# df_selection = df.query(
#     "flat_type == @flat_type & town == @town & lease_commence_bin == @lease_commence_bin"
# )


# df_selection['year_month'] = pd.to_datetime(
#     df_selection['year_month'], format='%Y-%m-%d')
# latest_month = df_selection['year_month'].max()
# last_3_months = [(latest_month - pd.DateOffset(months=i)
#                   ).strftime('%Y-%m-%d') for i in range(1, 4)]
# last_6_months = [(latest_month - pd.DateOffset(months=i)
#                   ).strftime('%Y-%m-%d') for i in range(1, 7)]
# last_12_months = [(latest_month - pd.DateOffset(months=i)
#                    ).strftime('%Y-%m-%d') for i in range(1, 13)]
# last_5_years = [(latest_month - pd.DateOffset(months=i)
#                  ).strftime('%Y-%m-%d') for i in range(1, 61)]
# df_last_3_months = df_selection[df_selection['year_month'].dt.strftime(
#     '%Y-%m-%d').isin(last_3_months)]
# df_last_6_months = df_selection[df_selection['year_month'].dt.strftime(
#     '%Y-%m-%d').isin(last_6_months)]
# df_last_12_months = df_selection[df_selection['year_month'].dt.strftime(
#     '%Y-%m-%d').isin(last_12_months)]
# df_last_5_years = df_selection[df_selection['year_month'].dt.strftime(
#     '%Y-%m-%d').isin(last_5_years)]
# l3m_highest_psf = round(df_last_3_months['resale_psf'].max(), 1)
# l3m_lowest_psf = round(df_last_3_months['resale_psf'].min(), 1)
# l6m_highest_psf = round(df_last_6_months['resale_psf'].max(), 1)
# l6m_lowest_psf = round(df_last_6_months['resale_psf'].min(), 1)
# l12m_highest_psf = round(df_last_12_months['resale_psf'].max(), 1)
# l12m_lowest_psf = round(df_last_12_months['resale_psf'].min(), 1)
# l5y_highest_psf = round(df_last_5_years['resale_psf'].max(), 1)
# l5y_lowest_psf = round(df_last_5_years['resale_psf'].min(), 1)

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