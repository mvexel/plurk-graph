import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import datetime
import numpy as np


def create_combined_plot(colormap_name="tab20", scale_factor=2.0):
    """
    Create a monthly stacked bar chart of combined plurk and reply activity.

    Args:
        colormap_name: Name of matplotlib colormap (default: 'tab20')
        scale_factor: Scaling factor for output size/resolution (default: 2.0)
    
    Outputs:
        Saves PNG file named 'combined_activity_{colormap_name}.png' showing:
        - Monthly activity grouped by user
        - Stacked bars showing relative contributions
        - Automatic time axis handling
        - Properly scaled for readability
    """
    # Connect to your SQLite database
    conn = sqlite3.connect("plurks.db")

    # Query for combined plurks and replies data
    query_combined = """
    -- Get plurk counts by month and user
    SELECT 
        strftime('%Y-%m', datetime(plurks.posted, 'unixepoch')) AS month,
        users.display_name AS username,
        COUNT(*) AS count,
        'plurk' AS type
    FROM plurks
    JOIN users ON plurks.owner_id = users.id
    GROUP BY month, username

    UNION ALL

    -- Get reply counts by month and user
    SELECT 
        strftime('%Y-%m', datetime(replies.posted, 'unixepoch')) AS month,
        users.display_name AS username,
        COUNT(*) AS count,
        'reply' AS type
    FROM replies
    JOIN users ON replies.user_id = users.id
    GROUP BY month, username;
    """

    # Execute query and load into DataFrame
    df_combined = pd.read_sql_query(query_combined, conn)
    conn.close()

    # If no data, create empty plot and exit
    if df_combined.empty:
        plt.figure(figsize=(16 * scale_factor, 8 * scale_factor))
        plt.title(
            "Meten is Weten",
            fontsize=16 * scale_factor / 2,
        )
        plt.xlabel("Maand", fontsize=14 * scale_factor / 2)
        plt.ylabel("Plurks + Antwoorden", fontsize=14 * scale_factor / 2)
        plt.savefig(
            f"combined_activity_{colormap_name}.png",
            format="png",
            dpi=100 * scale_factor,
        )
        plt.close()
        return

    # Group by month and username, summing the counts
    df_aggregated = (
        df_combined.groupby(["month", "username"])["count"].sum().reset_index()
    )

    # Pivot data so each username becomes its own column
    pivot_combined = df_aggregated.pivot(
        index="month", columns="username", values="count"
    ).fillna(0)

    # Convert index to datetime to sort and pad missing months
    pivot_combined.index = pd.to_datetime(pivot_combined.index, format="%Y-%m")
    current_date = datetime.datetime.now()

    # Ensure data extends to current month
    all_months = pd.date_range(
        start=pivot_combined.index.min(), end=current_date.strftime("%Y-%m"), freq="MS"
    )
    pivot_combined = pivot_combined.reindex(all_months, fill_value=0)
    pivot_combined.index = pivot_combined.index.strftime("%Y-%m")
    month_labels = pivot_combined.index.tolist()

    # Prepare colormap for unique user colors
    num_users = len(pivot_combined.columns)

    # Choose colormap based on input
    if colormap_name in [
        "viridis",
        "plasma",
        "inferno",
        "magma",
        "cividis",
        "Spectral",
    ]:
        # For sequential colormaps, use linspace
        colors = plt.get_cmap(colormap_name)(np.linspace(0, 1, num_users))
    else:
        # For qualitative colormaps, use range
        cmap = plt.get_cmap(colormap_name)
        colors = [cmap(i % cmap.N) for i in range(num_users)]

    # Create figure with scaled size
    plt.figure(figsize=(16 * scale_factor, 8 * scale_factor))

    # Create the plot
    ax = pivot_combined.plot(
        kind="bar", stacked=True, width=0.8, color=colors, ax=plt.gca()
    )

    # Set ticks explicitly before setting labels
    tick_positions = range(len(month_labels))
    # Show every 4th tick for readability
    ax.set_xticks(tick_positions[::4])
    ax.set_xticklabels(
        [month_labels[i] for i in range(0, len(month_labels), 4)],
        rotation=45,
        ha="right",
        fontsize=12 * scale_factor / 2,
    )

    # Scale font sizes proportionally
    plt.xlabel("Maand", fontsize=14 * scale_factor / 2)
    plt.ylabel("Plurks + Antwoorden", fontsize=14 * scale_factor / 2)
    plt.title(
        f"Meten is Weten",
        fontsize=16 * scale_factor / 2,
    )
    plt.yticks(fontsize=12 * scale_factor / 2)

    # Scale legend font sizes
    plt.legend(
        title="User",
        bbox_to_anchor=(1.05, 1),
        loc="upper left",
        fontsize=12 * scale_factor / 2,
        title_fontsize=12 * scale_factor / 2,
    )

    plt.tight_layout()

    # Save with higher DPI to maintain quality
    plt.savefig(
        f"combined_activity_{colormap_name}.png",
        format="png",
        dpi=100 * scale_factor / 2,
    )
    plt.close()


# Create a plot with the default colormap at twice the size
create_combined_plot("tab20", scale_factor=2.0)

# Uncomment below to generate all colormaps
"""
colormaps_to_try = [
    'tab20',      # Default, good for up to 20 categories
    'Set1',       # Vibrant and distinct
    'Pastel1',    # Soft pastel colors
    'Dark2',      # Dark, rich colors
    'Paired',     # Paired colors
    'Spectral',   # Rainbow-like gradient
    'viridis',    # Perceptually uniform, colorblind-friendly
    'plasma',     # Vibrant, perceptually uniform
    'tab10'       # Professional-looking palette
]

# Generate a plot for each colormap
for cmap in colormaps_to_try:
    create_combined_plot(cmap, scale_factor=2.0)
"""
