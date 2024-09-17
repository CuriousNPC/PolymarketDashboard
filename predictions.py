import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import requests
from datetime import datetime, timedelta
import time
import io
import base64

# Polymarket API endpoint
POLYMARKET_API_URL = "https://clob.polymarket.com/query"

# Predefined list of categories
CATEGORIES = [
    "Politics",
    "Crypto",
    "Sports",
    "Entertainment",
    "Science",
    "Economics",
    "Other"
]

# Function to fetch data from Polymarket
def fetch_polymarket_data(category=None):
    query = """
    query GetMarkets($category: String) {
      markets(where: { category: $category }, orderBy: volume, orderDirection: desc) {
        id
        question
        category
        volume
        outcomes {
          price
          totalVolumeYes
          totalVolumeNo
        }
        endDate
      }
    }
    """
    variables = {"category": category} if category != "All" else {}
    response = requests.post(POLYMARKET_API_URL, json={"query": query, "variables": variables})
    return response.json()["data"]["markets"]

# Function to process the fetched data
def process_data(markets):
    df = pd.DataFrame([
        {
            'id': m['id'],
            'question': m['question'],
            'category': m['category'],
            'volume': float(m['volume']),
            'yes_price': float(m['outcomes'][0]['price']),
            'no_price': float(m['outcomes'][1]['price']),
            'yes_volume': float(m['outcomes'][0]['totalVolumeYes']),
            'no_volume': float(m['outcomes'][1]['totalVolumeNo']),
            'end_date': datetime.fromtimestamp(int(m['endDate']))
        }
        for m in markets
    ])
    
    df['total_volume'] = df['yes_volume'] + df['no_volume']
    df['days_to_end'] = (df['end_date'] - datetime.now()).dt.days
    
    return df

# Function to create a download link for the dataframe
def get_table_download_link(df):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="polymarket_data.csv">Download CSV file</a>'
    return href

# Function to create a download link for a plot
def get_plot_download_link(fig, filename):
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    b64 = base64.b64encode(buf.getvalue()).decode()
    href = f'<a href="data:image/png;base64,{b64}" download="{filename}">Download Plot</a>'
    return href

# Streamlit app
def main():
    st.title("Polymarket Analysis Dashboard")

    # Sidebar for filters and settings
    st.sidebar.header("Filters and Settings")
    
    # Category selection
    selected_categories = st.sidebar.multiselect(
        "Select Categories",
        CATEGORIES,
        default=["Politics", "Crypto"]  # Default selections
    )
    
    if not selected_categories:
        st.warning("Please select at least one category.")
        return

    # Add "All" option
    category = st.sidebar.radio("Choose category view", ["All"] + selected_categories)
    
    # Auto-refresh settings
    auto_refresh = st.sidebar.checkbox("Auto-refresh data")
    refresh_interval = st.sidebar.slider("Refresh interval (seconds)", 60, 600, 300)

    while True:
        # Fetch and process data
        raw_data = fetch_polymarket_data(category)
        df = process_data(raw_data)

        # Filter data based on selected categories
        if category == "All":
            df = df[df['category'].isin(selected_categories)]

        # Display basic stats
        st.header("Market Overview")
        st.write(f"Total Markets: {len(df)}")
        st.write(f"Total Volume: ${df['volume'].sum():,.2f}")

        # Top markets by volume
        st.header("Top Markets by Volume")
        top_markets = df.nlargest(10, 'volume')
        fig, ax = plt.subplots(figsize=(12, 6))
        sns.barplot(x='volume', y='question', data=top_markets, ax=ax)
        ax.set_title("Top 10 Markets by Volume")
        ax.set_xlabel("Volume")
        ax.set_ylabel("Question")
        st.pyplot(fig)
        st.markdown(get_plot_download_link(fig, "top_markets.png"), unsafe_allow_html=True)

        # Volume vs Probability scatter plot
        st.header("Volume vs Probability")
        fig, ax = plt.subplots(figsize=(12, 6))
        sns.scatterplot(x='yes_price', y='volume', data=df, ax=ax)
        ax.set_title("Volume vs Yes Price")
        ax.set_xlabel("Yes Price (Implied Probability)")
        ax.set_ylabel("Volume")
        st.pyplot(fig)
        st.markdown(get_plot_download_link(fig, "volume_vs_probability.png"), unsafe_allow_html=True)

        # Category distribution
        st.header("Distribution of Markets by Category")
        fig, ax = plt.subplots(figsize=(12, 6))
        sns.countplot(y='category', data=df, order=df['category'].value_counts().index, ax=ax)
        ax.set_title("Distribution of Markets by Category")
        ax.set_xlabel("Number of Markets")
        ax.set_ylabel("Category")
        st.pyplot(fig)
        st.markdown(get_plot_download_link(fig, "category_distribution.png"), unsafe_allow_html=True)

        # Market details
        st.header("Market Details")
        selected_market = st.selectbox("Select a market", df['question'])
        market_data = df[df['question'] == selected_market].iloc[0]
        st.write(f"Category: {market_data['category']}")
        st.write(f"Volume: ${market_data['volume']:,.2f}")
        st.write(f"Yes Price: {market_data['yes_price']:.2f}")
        st.write(f"No Price: {market_data['no_price']:.2f}")
        st.write(f"Days to End: {market_data['days_to_end']}")

        # Data table
        st.header("All Markets Data")
        st.dataframe(df)
        st.markdown(get_table_download_link(df), unsafe_allow_html=True)

        # Display last update time
        st.sidebar.write(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Auto-refresh logic
        if auto_refresh:
            time.sleep(refresh_interval)
            st.experimental_rerun()
        else:
            break

if __name__ == "__main__":
    main()
