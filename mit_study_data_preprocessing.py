# -*- coding: utf-8 -*-
"""final_mit_users_report.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1dhr4lhnilGWyFDN6fC_Vstl999oIYe_x
"""

# @title Setup: Libraries & GCP
from google.colab import auth
from google.cloud import bigquery
from google.colab import data_table
import pandas as pd
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from google.colab import auth
import pandas_gbq


pd.set_option('display.max_columns', 50)  # Set the maximum number of columns to 50

# GCP settings
project = 'willow-health' # Project ID inserted based on the query results selected to explore
location = 'US' # Location inserted based on the query results selected to explore
client = bigquery.Client(project=project, location=location)
data_table.enable_dataframe_formatter()
auth.authenticate_user()

# @title Data Loader: GCP and Local
# Running this code will display the query used to generate your previous job

# Run the following code to get the latest JOB ID from Cloud Shell Terminal:
# bq ls -j -a --max_results=1 --format=prettyjson | jq '.[0].jobReference.jobId'

LOAD_LOCAL = False # CHANGE THIS TO FALSE TO RUN FROM CLOUD

if LOAD_LOCAL:
  results = pd.read_csv("/content/drive/MyDrive/AI and Mental Health Project/MIT_Pilot_Analysis/RealTime_sleep_survey_stand_raw_latest_05_07_2023.csv")
  results_hr = pd.read_csv("/content/drive/MyDrive/AI and Mental Health Project/MIT_Pilot_Analysis/New_Sample_Users_RealTime_hours_raw_latest_05_07_2023.csv")
else:
  JOB_ID = 'bquxjob_14f7c316_188c9b696e2' # Sleep
  JOB_HR_ID = 'bquxjob_6ccf20b7_188c9b6a1ca'
  JOB_SURVEY_ID = 'bquxjob_32eb413b_188c9b66f36'

  # Running this code will read results from your previous job

  job_realtime_sleep_survey = client.get_job(JOB_ID) # Job ID inserted based on the query results selected to explore
  print(job_realtime_sleep_survey.query)
  results = job_realtime_sleep_survey.to_dataframe()

  job_realtime_hr = client.get_job(JOB_HR_ID)
  print(job_realtime_hr.query)
  results_hr = job_realtime_hr.to_dataframe()

  job_realtime_survey = client.get_job(JOB_SURVEY_ID)
  print(job_realtime_survey.query)
  results_survey = job_realtime_survey.to_dataframe()

# @title Helper Functions: Data Processing

def adjust_date(row):
    if row.hour < 18:
        return (row - pd.Timedelta(days=1)).date()
    else:
        return row.date()

def modify_sleep_dataset(dataset):
    # Clean userid column values from unnesessary ""
    dataset['userid'] = dataset['userid'].str.strip('"')

    # Change column name document_id to date and convert to date format
    dataset.rename(columns={'document_id': 'date'}, inplace=True)

    # Rename start_time and end_time columns
    dataset.rename(columns={'start_time': 'start_time_sleep', 'end_time': 'end_time_sleep'}, inplace=True)

    # When 'date' contains values like "22:00:00" and "7:00:00 am".
    for index, row in dataset.iterrows():
        if row['date'].count(':') > 0:
            # Extract the first part of the "end_time_sleep" value
            corrected_date = row['end_time_sleep'].split()[0]
            # Update the "date" column with the corrected value
            dataset.at[index, 'date'] = corrected_date

    dataset['date'] = pd.to_datetime(dataset['date']).dt.strftime('%Y-%m-%d')

    # New daytime based on 18:00 - 18:00 to capture sleep within one night
    dataset['start_time_sleep'] = pd.to_datetime(dataset['start_time_sleep'])
    dataset['date'] = dataset['start_time_sleep'].apply(adjust_date)

    return dataset

def convert_to_24h(time_str):
    if 'am' in time_str or 'pm' in time_str:
        return datetime.strptime(time_str, '%I:%M:%S %p').strftime('%H:%M:%S')
    else:
        return time_str

def modify_hr_dataset(dataset):
    # replace "None" string with numpy NaN (which is the proper representation for missing values)
    dataset.replace("None", np.nan, inplace=True)

    dataset['hours'] = dataset['hours'].apply(convert_to_24h)
    dataset = dataset.dropna(axis=1, how='all')

    # Convert to numeric, replacing non-numeric values with NaN. I do it below too but honestly I'll just leave it here as it works
    dataset['active_energy_burned'] = pd.to_numeric(dataset['active_energy_burned'], errors='coerce')
    dataset['basal_energy_burned'] = pd.to_numeric(dataset['basal_energy_burned'], errors='coerce')

    # Replace NaN values with 0
    dataset['active_energy_burned'].fillna(0, inplace=True)
    dataset['basal_energy_burned'].fillna(0, inplace=True)

    # Sum up 'active_energy_burned' and 'basal_energy_burned' columns into 'total_energy_burned'
    # Round to 3 decimal places
    dataset['total_energy_burned'] = (dataset['active_energy_burned'] + dataset['basal_energy_burned']).round(3)



    # convert all columns from the 5th onwards (Python is 0-indexed, so column at index 4 is the 5th column)
    # note: this includes the 5th column
    for col in dataset.columns[4:]:
      dataset[col] = pd.to_numeric(dataset[col], errors='coerce')
      dataset = dataset.sort_values(by=['userid', 'date'])


    variables_to_keep = [
        'userid',
        'hours',
        'timestamp',
        'date',
        'heart_rate_avg',
        'heart_rate_min',
        'heart_rate_max',
        'heart_rate_variability_sdnn_avg',
        'active_energy_burned',
        'basal_energy_burned',
        'total_energy_burned',
        'step_count',
        'apple_exercise_time',
        'oxygen_saturation_avg'
    ]

    # Drop rows where the 'date' column values are in the format 'hh:mm:ss'
    dataset = dataset[~dataset['date'].str.match(r'^\d{2}:\d{2}:\d{2}$')]

    dataset = dataset.filter(variables_to_keep)
    dataset = dataset.sort_values(by=['date', 'hours'])

    return dataset

def modify_survey_dataset(dataset):
    dataset.rename(columns={'document_id': 'date'}, inplace=True)
    dataset['date'] = pd.to_datetime(dataset['date']).dt.strftime('%Y-%m-%d')
    dataset = dataset.sort_values(by=['userid', 'date'])

    return dataset

# Data Preprocessing

results_survey = modify_survey_dataset(results_survey)
results_survey.sort_values('date', ascending=False)

results_hr = modify_hr_dataset(results_hr)
results_hr.sort_values('date', ascending=False)

results = modify_sleep_dataset(results)
results.sort_values('date', ascending=False)

# Apply Helper Functions for Data Processing
# Create digital biomarker data by aggregating hourly data into daily granularity data

def aggregate_hr_df(filtered_hr):
    # Aggregate metrics
    aggregated_df = filtered_hr.groupby(['userid', 'date']).agg({
        'heart_rate_avg': ['mean', 'min', 'max'],
        'heart_rate_min': ['mean', 'min', 'max'],
        'heart_rate_max': ['mean', 'min', 'max'],
        'heart_rate_variability_sdnn_avg': ['mean', 'min', 'max'],
        'total_energy_burned': 'sum',
        'apple_exercise_time': 'sum',
        'oxygen_saturation_avg': ['mean', 'min', 'max'],
    }).reset_index()

    aggregated_df.columns = ['_'.join(col).strip() for col in aggregated_df.columns.values]

    # If any of the aggregate is equal to zero, take an average of the past week
    for column in aggregated_df.columns:
        # Skip the 'userid_' and 'date_' columns
        if column not in ['userid_', 'date_']:
            # Loop over each user
            for user in aggregated_df['userid_'].unique():
                # Create a mask for the current user
                mask = aggregated_df['userid_'] == user
                # Replace zeros with NaN
                aggregated_df.loc[mask, column] = aggregated_df.loc[mask, column].replace(0, np.nan)
                # Fill NaN values with the mean of the past 7 days
                aggregated_df.loc[mask, column] = aggregated_df.loc[mask, column].fillna(aggregated_df[mask][column].rolling(7, min_periods=1).mean())

    # Replace 'userid_' and 'date_' with 'userid' and 'date'
    aggregated_df.rename(columns={'userid_': 'userid', 'date_': 'date'}, inplace=True)

    return aggregated_df

def preprocess_merged_df(filtered_survey, aggregated_hr_df, sleep_df, wellbeing_indicators, subset_wellbeing_indicators):
    """
    Function to merge hours, sleep and survey data.

    Args:
    filtered_survey, aggregated_hr_df, sleep_df (pandas.DataFrame): DFs to preprocess and merge.
    wellbeing_indicators (list): A list of survey column names to check for missing values.
    subset_wellbeing_indicators (bool): If True, rows with missing values in the wellbeing indicators will be dropped.

    Returns:
    pandas.DataFrame: merged dataframe.
    """
    # Convert 'date' to datetime in all dataframes
    filtered_survey['date'] = pd.to_datetime(filtered_survey['date'])
    aggregated_hr_df['date'] = pd.to_datetime(aggregated_hr_df['date'])
    sleep_df['date'] = pd.to_datetime(sleep_df['date'])

    # Merge dataframes
    merged_df = pd.merge(filtered_survey, aggregated_hr_df, on=['userid', 'date'], how='outer')
    merged_df = pd.merge(merged_df, sleep_df, on=['userid', 'date'], how='outer')

    # Add 'day_of_week' column
    merged_df['day_of_week'] = merged_df['date'].dt.dayofweek

    # Drop rows with NaN in any of the wellbeing indicators if subset_wellbeing_indicators is True
    if subset_wellbeing_indicators:
        merged_df = merged_df.dropna(subset=wellbeing_indicators)

    return merged_df

aggregated_df = aggregate_hr_df(results_hr)
aggregated_df.describe()

def extract_start_end_times(filtered_df):
    # Convert 'start_time_sleep' and 'end_time_sleep' to datetime type
    filtered_df['start_time_sleep'] = pd.to_datetime(filtered_df['start_time_sleep'])
    filtered_df['end_time_sleep'] = pd.to_datetime(filtered_df['end_time_sleep'])

    sleep_types_to_keep = ['in_bed']
    filtered_df = filtered_df[filtered_df['sleep_type'].isin(sleep_types_to_keep)]

    # Calculate the difference in minutes
    filtered_df['diff'] = (filtered_df['end_time_sleep'] - filtered_df['start_time_sleep']).dt.total_seconds() / 60

    # Group by 'userid', 'date', 'source_type', and 'sleep_type', and find the earliest and latest times
    grouped = filtered_df.groupby(['userid', 'date', 'source_type', 'sleep_type']).agg({
        'start_time_sleep': 'min',
        'end_time_sleep': 'max',
        'diff': 'sum'
    }).reset_index()

    # Calculate the difference in minutes between earliest_start_time and latest_end_time
    grouped['diff_interval'] = (grouped['end_time_sleep'] - grouped['start_time_sleep']).dt.total_seconds() / 60

    # Convert diff_interval from minutes to hours
    grouped['diff_interval_hours'] = grouped['diff_interval'] / 60

    # Column manipulations
    grouped.rename(columns={'start_time_sleep': 'earliest_start_time', 'end_time_sleep': 'latest_end_time', 'diff': 'sleep_duration'}, inplace=True)
    grouped = grouped.drop('sleep_duration', axis=1)

    # Define a custom order for source_type by priority
    source_type_order = {"watch": 1, "other": 2, "iphone": 3}
    grouped['source_type_order'] = grouped['source_type'].map(source_type_order)

    # Sorting by 'userid', 'date' and 'source_type_order'
    grouped = grouped.sort_values(['userid', 'date', 'source_type_order'])

    # Drop duplicate rows based on 'userid' and 'date', keeping only the first row (i.e., the row with the preferred source_type)
    grouped = grouped.drop_duplicates(subset=['userid', 'date'], keep='first')
    grouped = grouped.drop('source_type_order', axis=1)

    return grouped

# Apply to Sleep data
df = extract_start_end_times(results)
dataset = df.sort_values(['userid', 'date'], ascending=[True, False])

# @title Filtering Users (Optional)

# userids = [user1, user2
# ]

# filtered_dataset = dataset[dataset['userid'].isin(userids)]
# filtered_dataset

# results[results['userid'].isin(userids)].sort_values(['userid', 'date'], ascending=[True, False])

wellbeing_indicators = ['Today_I_felt_calm', 'How_stressed_out_are_you_today', 'Today_I_felt_nervous', 'What_time_of_the_day_were_you_the_most_stressed', 'Today_I_was_worried']
dff = preprocess_merged_df(results_survey, aggregated_df, df, wellbeing_indicators, False)

dff = dff.replace([None, 'None'], np.nan)

def compute_means_and_append(df, mean_columns):
    """
    Function to compute means of reported data for sample average and append a new row with these mean values.

    Args:
    df: The df to compute means on.
    mean_columns (list): A list of column names to compute the means.

    Returns: The dataframe with an additional row of mean values.
    """
    # Replace 'inf' and '-inf' (as strings) with NaN in all DataFrame
    df = df.replace(['inf', '-inf'], np.nan)

    # Convert mean_columns to numeric type, errors='coerce' turns invalid values into NaN
    for col in mean_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    subset = df.dropna(subset=mean_columns)
    mean_values = subset[mean_columns].mean()
    mean_row = mean_values.append(pd.Series({'userid': 'population'}))
    df = df.append(mean_row, ignore_index=True)

    return df

# @title Push the data back to BQ

auth.authenticate_user()

pandas_gbq.to_gbq(dff, 'willow-health.mit_analytics.NAME', project_id='willow-health', if_exists='append')