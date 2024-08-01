import pandas as pd
import streamlit as st
from io import StringIO
import zipfile
import plotly.express as px

# Local path to the zip file
zip_file_path = "data.zip"

# Streamlit UI components
st.title("Price Evolution Analysis")
st.write("Select the period of interest, time range, and sources:")


# Load data
@st.cache_data
def load_data(zip_file_path, chunk_size=10000):
    chunks = []

    # Open the local zip file
    with zipfile.ZipFile(zip_file_path, "r") as zip_file:
        # Extract the CSV file from the zip
        with zip_file.open("data.csv") as csv_file:
            csv_content = StringIO(csv_file.read().decode("utf-8"))

            for chunk in pd.read_csv(csv_content, chunksize=chunk_size):
                # Convert the Block Timestamp to datetime format
                chunk["Block Timestamp"] = pd.to_datetime(chunk["Block Timestamp"])
                chunk["Price"] = chunk["Price"] / 100000000

                # Convert Volume to numeric, replacing non-numeric values with NaN
                chunk["Volume"] = pd.to_numeric(chunk["Volume"], errors="coerce")

                # Filter to keep only timestamps with at least 5 sources
                chunk = chunk.groupby("Block Timestamp").filter(lambda x: len(x) >= 5)

                chunks.append(chunk)

    data = pd.concat(chunks, ignore_index=True)

    median_data = data.groupby("Block Timestamp")["Price"].median().reset_index()
    median_data["Source"] = "Median"

    data = pd.concat([data, median_data], ignore_index=True)

    return data


data = load_data(zip_file_path)

# Select date range
start_date = st.date_input("Start date", data["Block Timestamp"].min().date())
end_date = st.date_input("End date", data["Block Timestamp"].max().date())

# Select hourly range
start_hour = st.slider("Start hour", 0, 23, 0)
end_hour = st.slider("End hour", 0, 23, 23)

# Select sources
all_sources = data["Source"].unique()
selected_sources = st.multiselect("Select sources", all_sources, default=all_sources)

if start_date > end_date:
    st.error("Error: End date must fall after start date.")
else:
    # Filter data by date, hour, and selected sources
    filtered_data = data[
        (data["Block Timestamp"].dt.date >= start_date)
        & (data["Block Timestamp"].dt.date <= end_date)
        & (data["Block Timestamp"].dt.hour >= start_hour)
        & (data["Block Timestamp"].dt.hour <= end_hour)
        & (data["Source"].isin(selected_sources))
    ]

    # Plotting using Plotly
    fig = px.line(
        filtered_data,
        x="Block Timestamp",
        y="Price",
        color="Source",
        title="Price Evolution by Source",
    )
    fig.update_layout(
        xaxis_title="Timestamp", yaxis_title="Price (Divided by 100,000,000)"
    )

    # Display the plot using Streamlit
    st.plotly_chart(fig, use_container_width=True)

    # Add a data table below the chart
    st.write("### Data Table")
    st.dataframe(filtered_data)

    # Add download button for CSV
    csv = filtered_data.to_csv(index=False)
    st.download_button(
        label="Download data as CSV",
        data=csv,
        file_name="price_evolution_data.csv",
        mime="text/csv",
    )
