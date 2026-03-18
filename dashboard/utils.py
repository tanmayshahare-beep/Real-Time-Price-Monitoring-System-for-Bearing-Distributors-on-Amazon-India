# Dashboard Utilities

def format_currency(value):
    """Format a value as Indian Rupees."""
    if value is None:
        return "N/A"
    return f"₹{value:,.2f}"

def get_price_stats(df):
    """Calculate basic price statistics from a DataFrame."""
    if df.empty or 'price' not in df.columns:
        return {}
    
    return {
        'min': df['price'].min(),
        'max': df['price'].max(),
        'avg': df['price'].mean(),
        'median': df['price'].median()
    }
