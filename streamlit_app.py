import streamlit as st
import pandas as pd
import math
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title='GDP dashboard',
    page_icon=':earth_americas:', # This is an emoji shortcode. Could be a URL too.
)

# -----------------------------------------------------------------------------
# Declare some useful functions.

@st.cache_data
def get_gdp_data():
    """Grab GDP data from a CSV file.

    This uses caching to avoid having to read the file every time. If we were
    reading from an HTTP endpoint instead of a file, it's a good idea to set
    a maximum age to the cache with the TTL argument: @st.cache_data(ttl='1d')
    """

    # Instead of a CSV on disk, you could read from an HTTP endpoint here too.
    DATA_FILENAME = Path(__file__).parent/'data/gdp_data.csv'
    raw_gdp_df = pd.read_csv(DATA_FILENAME)

    MIN_YEAR = 1960
    MAX_YEAR = 2022

    # The data above has columns like:
    # - Country Name
    # - Country Code
    # - [Stuff I don't care about]
    # - GDP for 1960
    # - GDP for 1961
    # - GDP for 1962
    # - ...
    # - GDP for 2022
    #
    # ...but I want this instead:
    # - Country Name
    # - Country Code
    # - Year
    # - GDP
    #
    # So let's pivot all those year-columns into two: Year and GDP
    gdp_df = raw_gdp_df.melt(
        ['Country Code'],
        [str(x) for x in range(MIN_YEAR, MAX_YEAR + 1)],
        'Year',
        'GDP',
    )

    # Convert years from string to integers
    gdp_df['Year'] = pd.to_numeric(gdp_df['Year'])

    return gdp_df

def calculate_growth_rate(country_data):
    """Calculate average annual growth rate for a country."""
    if len(country_data) < 2:
        return 0
    
    # Use last 10 years of data for growth rate calculation
    recent_data = country_data.tail(10)
    if len(recent_data) < 2:
        return 0
    
    # Calculate compound annual growth rate (CAGR)
    first_gdp = recent_data.iloc[0]['GDP']
    last_gdp = recent_data.iloc[-1]['GDP']
    years = len(recent_data) - 1
    
    if first_gdp <= 0 or last_gdp <= 0:
        return 0
    
    growth_rate = (last_gdp / first_gdp) ** (1/years) - 1
    return growth_rate

def project_gdp(country_data, projection_years=10):
    """Project GDP for future years based on historical growth rate."""
    if len(country_data) == 0:
        return pd.DataFrame()
    
    growth_rate = calculate_growth_rate(country_data)
    last_year = country_data['Year'].max()
    last_gdp = country_data['GDP'].iloc[-1]
    
    if math.isnan(last_gdp) or last_gdp <= 0:
        return pd.DataFrame()
    
    # Create projection data
    projection_data = []
    for i in range(1, projection_years + 1):
        year = last_year + i
        projected_gdp = last_gdp * (1 + growth_rate) ** i
        projection_data.append({
            'Country Code': country_data['Country Code'].iloc[0],
            'Year': year,
            'GDP': projected_gdp,
            'Projected': True
        })
    
    return pd.DataFrame(projection_data)

def create_gdp_chart(filtered_gdp_df, show_projections=False):
    """Create an interactive chart with historical and projected data."""
    if len(filtered_gdp_df) == 0:
        return None
    
    # Separate historical and projected data
    if show_projections and 'Projected' in filtered_gdp_df.columns:
        historical_data = filtered_gdp_df[filtered_gdp_df['Projected'] != True].copy()
        projected_data = filtered_gdp_df[filtered_gdp_df['Projected'] == True].copy()
        
        # Create the chart
        fig = go.Figure()
        
        # Add historical data with solid lines
        for country in historical_data['Country Code'].unique():
            country_data = historical_data[historical_data['Country Code'] == country]
            fig.add_trace(go.Scatter(
                x=country_data['Year'],
                y=country_data['GDP'],
                mode='lines',
                name=f'{country} (Historical)',
                line=dict(width=2),
                showlegend=True
            ))
        
        # Add projected data with dashed lines
        for country in projected_data['Country Code'].unique():
            country_data = projected_data[projected_data['Country Code'] == country]
            fig.add_trace(go.Scatter(
                x=country_data['Year'],
                y=country_data['GDP'],
                mode='lines',
                name=f'{country} (Projected)',
                line=dict(width=2, dash='dash'),
                showlegend=True
            ))
        
        fig.update_layout(
            title='GDP Over Time (Historical vs Projected)',
            xaxis_title='Year',
            yaxis_title='GDP (US$)',
            hovermode='x unified'
        )
        
        return fig
    else:
        # Simple chart without projections
        fig = px.line(
            filtered_gdp_df,
            x='Year',
            y='GDP',
            color='Country Code',
            title='GDP Over Time'
        )
        return fig

gdp_df = get_gdp_data()

# -----------------------------------------------------------------------------
# Draw the actual page

# Set the title that appears at the top of the page.
'''
# :earth_americas: GDP dashboard

Browse GDP data from the [World Bank Open Data](https://data.worldbank.org/) website. As you'll
notice, the data only goes to 2022 right now, and datapoints for certain years are often missing.
But it's otherwise a great (and did I mention _free_?) source of data.
'''

# Add some spacing
''
''

min_value = gdp_df['Year'].min()
max_value = gdp_df['Year'].max()

# Add projection toggle
col1, col2 = st.columns([3, 1])
with col1:
    from_year, to_year = st.slider(
        'Which years are you interested in?',
        min_value=min_value,
        max_value=2032 if st.checkbox('Include projections (2023-2032)', value=False) else max_value,
        value=[min_value, max_value])

with col2:
    st.write("")
    st.write("")
    show_projections = st.checkbox('Show projections', value=False)

countries = gdp_df['Country Code'].unique()

if not len(countries):
    st.warning("Select at least one country")

selected_countries = st.multiselect(
    'Which countries would you like to view?',
    countries,
    ['DEU', 'FRA', 'GBR', 'BRA', 'MEX', 'JPN'])

''
''
''

# Filter the data
filtered_gdp_df = gdp_df[
    (gdp_df['Country Code'].isin(selected_countries))
    & (gdp_df['Year'] <= to_year)
    & (from_year <= gdp_df['Year'])
]

# Add projections if requested
if show_projections and to_year > 2022:
    projection_data = []
    for country in selected_countries:
        country_data = gdp_df[gdp_df['Country Code'] == country].copy()
        if len(country_data) > 0:
            projections = project_gdp(country_data, projection_years=to_year-2022)
            if len(projections) > 0:
                # Filter projections to requested year range
                projections = projections[
                    (projections['Year'] <= to_year) & 
                    (projections['Year'] > 2022)
                ]
                if len(projections) > 0:
                    projection_data.append(projections)
    
    if projection_data:
        projected_df = pd.concat(projection_data, ignore_index=True)
        # Combine historical and projected data
        combined_df = pd.concat([filtered_gdp_df, projected_df], ignore_index=True)
        filtered_gdp_df = combined_df.sort_values(['Country Code', 'Year'])

st.header('GDP over time', divider='gray')

''

# Create the interactive chart
chart = create_gdp_chart(filtered_gdp_df, show_projections)
if chart:
    st.plotly_chart(chart, use_container_width=True)
    if show_projections:
        st.caption("💡 **Solid lines**: Historical data | **Dashed lines**: Projected data")
        st.warning("⚠️ **Projection Disclaimer**: These are simple estimates based on recent growth trends. Real GDP is affected by many factors including economic cycles, policy changes, and global events. Use projections as rough estimates only.")

''
''

# Show growth rate analysis
if show_projections:
    st.header('Growth Rate Analysis', divider='gray')
    
    growth_data = []
    for country in selected_countries:
        country_data = gdp_df[gdp_df['Country Code'] == country]
        if len(country_data) > 0:
            growth_rate = calculate_growth_rate(country_data)
            last_gdp = country_data['GDP'].iloc[-1]
            growth_data.append({
                'Country': country,
                'Average Annual Growth Rate': f"{growth_rate:.2%}",
                'Last GDP (2022)': f"${last_gdp:,.0f}B" if not math.isnan(last_gdp) else "N/A"
            })
    
    if growth_data:
        growth_df = pd.DataFrame(growth_data)
        st.dataframe(growth_df, use_container_width=True)

# Get data for the selected years, ensuring we have valid data
first_year_data = gdp_df[gdp_df['Year'] == from_year]
last_year_data = gdp_df[gdp_df['Year'] == to_year]

# Handle projected data for the end year
if show_projections and to_year > 2022 and 'Projected' in filtered_gdp_df.columns:
    # Get projected data for the end year
    projected_end_year = filtered_gdp_df[
        (filtered_gdp_df['Year'] == to_year) & 
        (filtered_gdp_df['Projected'] == True)
    ]
    if len(projected_end_year) > 0:
        last_year_data = projected_end_year

st.header(f'GDP in {to_year}', divider='gray')

''

cols = st.columns(4)

for i, country in enumerate(selected_countries):
    col = cols[i % len(cols)]

    with col:
        # Get first year data safely
        first_year_data = first_year_data[first_year_data['Country Code'] == country]
        if len(first_year_data) > 0:
            first_gdp = first_year_data['GDP'].iat[0] / 1000000000
        else:
            first_gdp = float('nan')
        
        # Get last year data safely
        last_year_data = last_year_data[last_year_data['Country Code'] == country]
        if len(last_year_data) > 0:
            last_gdp = last_year_data['GDP'].iat[0] / 1000000000
        else:
            last_gdp = float('nan')

        if math.isnan(first_gdp):
            growth = 'n/a'
            delta_color = 'off'
        elif math.isnan(last_gdp):
            growth = 'n/a'
            delta_color = 'off'
        else:
            growth = f'{last_gdp / first_gdp:,.2f}x'
            delta_color = 'normal'

        # Add projection indicator
        is_projected = False
        if show_projections and to_year > 2022:
            projected_data = filtered_gdp_df[
                (filtered_gdp_df['Country Code'] == country) & 
                (filtered_gdp_df['Year'] == to_year) & 
                (filtered_gdp_df['Projected'] == True)
            ]
            is_projected = len(projected_data) > 0

        label = f'{country} GDP'
        if is_projected:
            label += ' (Projected)'

        # Handle display value
        if math.isnan(last_gdp):
            display_value = 'N/A'
        else:
            display_value = f'{last_gdp:,.0f}B'

        st.metric(
            label=label,
            value=display_value,
            delta=growth,
            delta_color=delta_color
        )
