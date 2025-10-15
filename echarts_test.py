import streamlit as st
import plotly.express as px
import pandas as pd
import json
import database_utils as db_utils
import streamlit_shadcn_ui as ui

st.title("🌍 Applications by Country")

def load_country_code_map():
    """Map country name to ISO code"""
    with open("iso_codes.txt", "r") as file:
        return json.load(file)

def get_map_data(user_id):
    jobs_df = db_utils.get_user_jobs(user_id)
    location_list = jobs_df["location"].unique().tolist()
    countries_dict = {}

    for loc in location_list:
        last_part = loc.split(", ")[-1]  # get the last element
        if loc not in countries_dict:    # avoid duplicates
            countries_dict[loc] = last_part

    country_df = pd.DataFrame(jobs_df, columns=["id", "location"])
    country_df["country"] = country_df["location"].map(countries_dict)

    return country_df[["id","country"]].value_counts("country")

# Get data
country_counts = get_map_data(10)

# Convert to DataFrame with ISO codes
df = pd.DataFrame({
    "name": country_counts.index,
    "value": country_counts.values
})
df["code"] = df["name"].map(load_country_code_map())

# Drop rows without valid ISO codes
df = df.dropna(subset=["code"])

# Create choropleth map
fig = px.choropleth(
    df,
    locations="code",
    color="value",
    hover_name="name",
    hover_data={"code": False, "value": True},
    color_continuous_scale="Inferno_r",
    labels={"value": "Applications"},
    title="Job Applications by Country"
)

fig.update_layout(
    geo=dict(
        showframe=False,
        showcoastlines=True,
        projection_type='natural earth'
    ),
    height=600
)

# Use shadcn card component
with ui.card(key="map_card"):
    st.plotly_chart(fig, use_container_width=True)