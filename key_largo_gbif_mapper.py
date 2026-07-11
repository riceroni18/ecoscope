# %%
import pandas as pd
import folium as fm
from folium.plugins import TimestampedGeoJson
from pygbif import occurrences as occ

#=======================================================================================================================

print('Grabbing 10 years of Climate Indicator Species data in Key Largo...')

key_largo_area = 'POLYGON((-80.55 25.00, -80.30 25.00, -80.30 25.20, -80.55 25.20, -80.55 25.00))'
date_range = '2016-01-01,2026-12-31'

kl_records = []

target_species = [
    "Sparisoma viride",      # Stoplight Parrotfish
    "Sphyraena barracuda",   # Great Barracuda
    "Rhizophora mangle"      # Red Mangrove
]

for species_name in target_species:
    print(f"Fetching historical data for: {species_name}...")
    offset = 0
    while True:
        response = occ.search(
            scientificName=species_name,
            geometry=key_largo_area,
            eventDate=date_range,
            limit=1000,
            offset=offset
        )
        results = response.get('results', [])
        if not results:
            break
            
        for record in results:
            kl_records.append({
                'Species': record.get('species', species_name), 
                'Latitude': record.get('decimalLatitude', None),
                'Longitude': record.get('decimalLongitude', None), 
                'Date': record.get('eventDate', None),
                'Category': 'Marine' if species_name != "Rhizophora mangle" else 'Coastal/Mangrove'
            })
            
        offset += len(results)
        if offset >= response.get('count', 0):
            break

# Data Cleaning & Setup
df = pd.DataFrame(kl_records)
clean_df = df.dropna(subset=['Species', 'Latitude', 'Longitude']).drop_duplicates()
clean_df['Date'] = pd.to_datetime(clean_df['Date'], errors='coerce')

total_records = len(clean_df)
print(f"\nSuccessfully compiled {len(clean_df)} total historical indicator records!")

print("--- Date Tracking Statistics ---")
print(clean_df['Date'].describe())

# Map Initialization (Centered over Key Largo)
m = fm.Map(location=(25.10, -80.425), zoom_start=11)

# Style configuration for indicators (Hex colors are used for the timeline gems)
species_map_config = {
    "Rhizophora mangle":     {"color": "green", "icon": "tree",    "label": "Red Mangrove (Coastal)", "hex": "#2e7d32"},
    "Sparisoma viride":       {"color": "blue",  "icon": "fish",    "label": "Stoplight Parrotfish (Reef)", "hex": "#0288d1"},
    "Sphyraena barracuda":    {"color": "red",   "icon": "fire",    "label": "Great Barracuda (Apex)", "hex": "#d32f2f"}
}

# Add Florida Keys National Marine Sanctuary overlay
try:
    fm.GeoJson(
        r"fknms_py2\fknms_py.json",
        name="Florida Keys National Marine Sanctuary",
        style_function=lambda x: {'color': '#0077be', 'weight': 2, 'fillOpacity': 0.03}
    ).add_to(m)
except FileNotFoundError:
    print("Warning: FKNMS GeoJSON file not found. Skipping overlay.")

# Convert your Pandas DataFrame into a GeoJSON Feature Collection for the Timeline
geojson_features = []

for index, row in clean_df.iterrows():
    # Skip rows that are missing critical timeline components
    if pd.isnull(row['Date']) or pd.isnull(row['Latitude']) or pd.isnull(row['Longitude']):
        continue
        
    sp_scientific = row['Species']
    sp_simple = sp_scientific.split(' (')[0] if ' (' in sp_scientific else sp_scientific
    config = species_map_config.get(sp_simple, {"color": "gray", "hex": "#757575"})
    
    # Format date to explicit string (YYYY-MM-DD)
    date_str = row['Date'].strftime('%Y-%m-%d')
    
    popup_text = f"<b>Species:</b> {sp_simple}<br><b>Date:</b> {date_str}<br><b>Category:</b> {row['Category']}"
    
    # Construct individual GeoJSON feature geometry
    feature = {
        'type': 'Feature',
        'geometry': {
            'type': 'Point',
            'coordinates': [row['Longitude'], row['Latitude']] # Standard GeoJSON: [Long, Lat]
        },
        'properties': {
            'time': date_str,
            'popup': popup_text,
            'tooltip': f"{sp_simple} sighting",
            'icon': 'circle',  # REQUIRED: Must be 'circle' for iconstyle to render
            'iconstyle': {
                'fillColor': config['hex'],
                'fillOpacity': 0.8,
                'stroke': True,
                'color': '#ffffff',
                'weight': 1,
                'radius': 8
            }
        }
    }
    geojson_features.append(feature)

geojson_data = {
    'type': 'FeatureCollection',
    'features': geojson_features
}

# Inject the Time Slider onto the Folium Map object
TimestampedGeoJson(
    geojson_data,
    period='P1M',               # Animate forward month-by-month
    add_last_point=True,
    auto_play=False,
    loop=False,
    max_speed=1,
    time_slider_drag_update=True,
    duration='P3M'              # Extended to keep dots on-screen for 3 months as it plays
).add_to(m)

# Save the timeline map to an HTML file in your workspace
m.save("key_largo_climate_indicators.html")
print("Timeline map successfully saved! Open 'key_largo_climate_indicators.html' to use the interactive time slider.")