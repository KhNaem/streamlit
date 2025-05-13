
import pandas as pd
import numpy as np

# Function to determine final rate
def determine_final_rate(previous_rates, new_rate, min_required=5, threshold=0.15):
    # Filter out previous rates that are NaN or non-positive
    previous_rates = [r for r in previous_rates if pd.notna(r) and r > 0]
    
    # If there are enough previous rates
    if len(previous_rates) >= min_required:
        avg_rate = sum(previous_rates) / len(previous_rates)  # Calculate average of previous rates
        
        # Calculate percentage difference between new rate and average rate
        percent_diff = abs(new_rate - avg_rate) / avg_rate
        
        # If difference is less than threshold (5%), consider it stable (fixed rate)
        if percent_diff <= threshold:
            return round(avg_rate, 6), True  # Fixed rate
        else:
            return round(new_rate, 6), False  # Use the new rate if difference is greater than 5%

    # If not enough previous rates, use the new rate
    combined = previous_rates + [new_rate] if new_rate > 0 else previous_rates
    final_avg = sum(combined) / len(combined) if combined else 0
    return round(final_avg, 6), False  # Not fixed yet

# Function to calculate average with flag for stable rates
def calc_avg_with_flag(rates_dict, rate_fixed_set):
    df = pd.DataFrame.from_dict(rates_dict, orient='index').fillna(0)
    avg_col = []
    for i, row in df.iterrows():
        values = row[row > 0].tolist()
        if len(values) >= 6:  # Must have at least 6 values to calculate stable rate
            prev = values[:-1]
            new = values[-1]
            avg, fixed = determine_final_rate(prev, new)
            avg_col.append(avg)
            if fixed:
                rate_fixed_set.add(i)  # Mark the brush number as fixed
        else:
            avg_col.append(np.mean(values))  # Use mean if not enough data
    return df, avg_col

# Function to highlight fixed rate rows in table (for Streamlit display)
def highlight_fixed_rate_row(row, column_name, fixed_set):
    styles = []
    for col in row.index:
        if col == column_name:
            if row.name in fixed_set:
                styles.append("background-color: green; color: black; font-weight: bold")  # Green if fixed
            else:
                styles.append("color: red; font-weight: bold")  # Red if not fixed
        else:
            styles.append("")
    return styles

# Example: Process data with these functions
brush_numbers = list(range(1, 33))
upper_rates = {n: {f"Sheet{i}": np.random.random() for i in range(1, 8)} for n in brush_numbers}
lower_rates = {n: {f"Sheet{i}": np.random.random() for i in range(1, 8)} for n in brush_numbers}

rate_fixed_upper = set()
rate_fixed_lower = set()

upper_df, upper_avg = calc_avg_with_flag(upper_rates, rate_fixed_upper)
lower_df, lower_avg = calc_avg_with_flag(lower_rates, rate_fixed_lower)

# Display tables with styles (this would be part of a Streamlit display or any UI)
print(upper_df.style.apply(lambda row: highlight_fixed_rate_row(row, "Avg Rate (Upper)", rate_fixed_upper), axis=1).format("{:.6f}"))
print(lower_df.style.apply(lambda row: highlight_fixed_rate_row(row, "Avg Rate (Lower)", rate_fixed_lower), axis=1).format("{:.6f}"))
