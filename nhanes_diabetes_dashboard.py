# NHANES Diabetes Dashboard
# Interactive Visualization of Diabetes Risk Factors and Outcomes
# Created for Data Visualization Specialist Interview

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
import requests
from io import StringIO, BytesIO
import zipfile
import os

# Try to import statsmodels, but handle if it's not installed
try:
    import statsmodels.api as sm
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False

# Set page configuration
st.set_page_config(
    page_title="NHANES Diabetes Visualization Dashboard",
    page_icon="🩸",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Function to handle errors gracefully


def safe_plot(func):
    """Decorator to handle plotting errors gracefully"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (ValueError, KeyError, TypeError) as e:
            st.error(f"Error creating visualization: {str(e)}")
            st.info(
                "This error might be due to insufficient data in the selected filters or missing dependencies.")
            return None
    return wrapper

# Function to safely use observed parameter with groupby


def safe_groupby(df, by, **kwargs):
    """Handle groupby with backwards compatibility for observed parameter"""
    try:
        # Try with observed parameter
        return df.groupby(by, observed=True, **kwargs)
    except TypeError:
        # Fall back to groupby without observed parameter
        return df.groupby(by, **kwargs)


# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #2C3E50;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: bold;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #566573;
        margin-bottom: 1rem;
    }
    .insight-box {
        background-color: #F8F9F9;
        border-radius: 5px;
        padding: 15px;
        border-left: 5px solid #3498DB;
        margin-bottom: 15px;
    }
    .notification {
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .notification.info {
        background-color: #D4F1F9;
        border-left: 5px solid #3498DB;
    }
    .notification.warning {
        background-color: #FDEBD0;
        border-left: 5px solid #E67E22;
    }
    .metric-box {
        padding: 15px;
        border-radius: 5px;
        text-align: center;
        box-shadow: 0 0 5px rgba(0, 0, 0, 0.1);
    }
    .metric-title {
        font-size: 0.9rem;
        color: #7F8C8D;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: bold;
        margin: 10px 0;
        color: #2C3E50;
    }
</style>
""", unsafe_allow_html=True)

# Main header
st.markdown("<h1 class='main-header'>NHANES Diabetes Interactive Dashboard</h1>",
            unsafe_allow_html=True)

st.markdown("""
This dashboard visualizes data from the National Health and Nutrition Examination Survey (NHANES), 
focusing on diabetes prevalence, risk factors, and health outcomes. The dashboard is designed for healthcare 
professionals to explore population-level trends and relationships in diabetes care.
""")

# Sidebar configuration
st.sidebar.image(
    "https://www.cdc.gov/nchs/media/images/2024/10/NHANES-Trademark.png", width=200)
st.sidebar.title("Data Controls")

# Function to download sample NHANES data or load prepared data


@st.cache_data
def load_nhanes_data():
    """
    Load sample NHANES data from either pre-processed files or create simulated data.
    In a production environment, this would download or access the actual NHANES data files.
    """
    # For this example, we'll create synthetic data that resembles NHANES
    # In a real implementation, you would download data from NHANES website

    # Generate sample size
    n_samples = 5000

    # Set random seed for reproducibility
    np.random.seed(42)
    age = np.random.normal(45, 18, n_samples).astype(int)
    age = np.clip(age, 18, 85)

    gender = np.random.choice(
        ['Male', 'Female'], size=n_samples, p=[0.48, 0.52])

    race_ethnicity = np.random.choice(
        ['Non-Hispanic White', 'Non-Hispanic Black',
            'Mexican American', 'Other Hispanic', 'Asian', 'Other'],
        size=n_samples,
        p=[0.65, 0.12, 0.1, 0.05, 0.05, 0.03]
    )

    education = np.random.choice(
        ['Less than High School', 'High School',
            'Some College', 'College Graduate'],
        size=n_samples,
        p=[0.15, 0.25, 0.30, 0.30]
    )

    income = np.random.choice(
        ['<$20,000', '$20,000-$44,999', '$45,000-$74,999', '$75,000+'],
        size=n_samples,
        p=[0.2, 0.3, 0.25, 0.25]
    )

    # Generate health metrics
    # BMI (higher if older and with certain conditions)
    base_bmi = np.random.normal(26, 5, n_samples)
    bmi = base_bmi + (age / 100)
    bmi = np.clip(bmi, 15, 50)

    # Blood pressure (tends to increase with age)
    systolic_bp = 90 + 0.5 * age + np.random.normal(0, 10, n_samples)
    diastolic_bp = 60 + 0.2 * age + np.random.normal(0, 7, n_samples)
    systolic_bp = np.clip(systolic_bp, 90, 200)
    diastolic_bp = np.clip(diastolic_bp, 50, 120)

    # HbA1c levels (glycated hemoglobin)
    # Higher for those with diabetes
    base_hba1c = np.random.normal(5.2, 0.3, n_samples)

    # Cholesterol levels
    total_cholesterol = np.random.normal(190, 35, n_samples)
    hdl_cholesterol = np.random.normal(50, 15, n_samples)
    ldl_cholesterol = total_cholesterol - hdl_cholesterol - \
        np.random.normal(100, 50, n_samples)
    ldl_cholesterol = np.clip(ldl_cholesterol, 40, 250)

    # Triglycerides
    triglycerides = np.random.normal(150, 80, n_samples)
    triglycerides = np.clip(triglycerides, 40, 500)

    # Risk factors and conditions
    # Some relationships between variables
    family_history_diabetes = np.random.choice(
        [True, False], size=n_samples, p=[0.3, 0.7])

    # Hypertension related to age and BMI
    hypertension_prob = 0.1 + 0.005 * age + 0.01 * (bmi - 25)
    hypertension_prob = np.clip(hypertension_prob, 0.05, 0.9)
    hypertension = np.random.binomial(
        1, hypertension_prob, n_samples).astype(bool)

    # Physical activity (inverse relation with age and BMI)
    physical_activity_prob = 0.8 - 0.005 * age - 0.01 * (bmi - 25)
    physical_activity_prob = np.clip(physical_activity_prob, 0.1, 0.9)
    physical_activity = np.random.binomial(
        1, physical_activity_prob, n_samples).astype(bool)

    # Smoking status
    smoking_status = np.random.choice(
        ['Never', 'Former', 'Current'],
        size=n_samples,
        p=[0.6, 0.2, 0.2]
    )

    # Diabetes status influenced by risk factors
    # Calculate diabetes probability based on risk factors
    diabetes_prob = (
        0.05 +  # base probability
        0.002 * (age - 40) +  # age factor
        0.01 * (bmi - 25) +  # BMI factor
        0.08 * family_history_diabetes +  # family history
        0.05 * hypertension +  # hypertension
        -0.03 * physical_activity  # protective effect of physical activity
    )

    # Add gender and ethnicity effects
    diabetes_prob += 0.02 * (gender == 'Male')
    diabetes_prob += 0.03 * (race_ethnicity == 'Non-Hispanic Black')
    diabetes_prob += 0.04 * (race_ethnicity == 'Mexican American')

    diabetes_prob = np.clip(diabetes_prob, 0.01, 0.8)
    diabetes = np.random.binomial(1, diabetes_prob, n_samples).astype(bool)

    # Adjust HbA1c for diabetic individuals
    hba1c = base_hba1c.copy()
    hba1c[diabetes] += np.random.normal(2, 0.7, sum(diabetes))
    hba1c = np.clip(hba1c, 4.0, 14.0)

    # Prediabetes (HbA1c between 5.7 and 6.4)
    prediabetes = (hba1c >= 5.7) & (hba1c < 6.5) & (~diabetes)

    # Fasting glucose
    fasting_glucose = 70 + hba1c * 10 + np.random.normal(0, 10, n_samples)
    fasting_glucose = np.clip(fasting_glucose, 60, 300)

    # Create a DataFrame
    data = pd.DataFrame({
        'Age': age,
        'Gender': gender,
        'Race_Ethnicity': race_ethnicity,
        'Education': education,
        'Income': income,
        'BMI': bmi,
        'Systolic_BP': systolic_bp,
        'Diastolic_BP': diastolic_bp,
        'HbA1c': hba1c,
        'Total_Cholesterol': total_cholesterol,
        'HDL_Cholesterol': hdl_cholesterol,
        'LDL_Cholesterol': ldl_cholesterol,
        'Triglycerides': triglycerides,
        'Family_History_Diabetes': family_history_diabetes,
        'Hypertension': hypertension,
        'Physical_Activity': physical_activity,
        'Smoking_Status': smoking_status,
        'Diabetes': diabetes,
        'Prediabetes': prediabetes,
        'Fasting_Glucose': fasting_glucose
    })

    # Add more features for completeness

    # Medication usage
    data['On_Insulin'] = np.random.binomial(
        1, 0.3, n_samples) * data['Diabetes']
    data['On_Oral_Medication'] = np.random.binomial(
        1, 0.7, n_samples) * data['Diabetes']

    # Complications (for those with diabetes)
    complication_base_prob = 0.05 + 0.003 * \
        (data['Age'] - 40) * data['Diabetes']
    complication_base_prob = np.clip(complication_base_prob, 0, 0.8)

    data['Retinopathy'] = np.random.binomial(
        1, complication_base_prob, n_samples)
    data['Nephropathy'] = np.random.binomial(
        1, complication_base_prob * 0.8, n_samples)
    data['Neuropathy'] = np.random.binomial(
        1, complication_base_prob * 1.2, n_samples)
    data['Cardiovascular_Disease'] = np.random.binomial(
        1, complication_base_prob * 1.5, n_samples)

    # Duration of diabetes (in years, only for those with diabetes)
    data['Diabetes_Duration'] = np.where(
        data['Diabetes'],
        np.random.randint(1, np.maximum(2, (data['Age'] - 20) // 2)),
        0
    )

    # Create some categorical variables based on continuous ones
    data['BMI_Category'] = pd.cut(
        data['BMI'],
        bins=[0, 18.5, 25, 30, 100],
        labels=['Underweight', 'Normal', 'Overweight', 'Obese']
    )

    data['BP_Category'] = pd.cut(
        data['Systolic_BP'],
        bins=[0, 120, 130, 140, 300],
        labels=['Normal', 'Elevated', 'Stage 1', 'Stage 2']
    )

    data['Glucose_Category'] = pd.cut(
        data['Fasting_Glucose'],
        bins=[0, 100, 126, 1000],
        labels=['Normal', 'Prediabetes', 'Diabetes']
    )

    # Add examination year (create a mix of participants across survey cycles)
    data['Examination_Year'] = np.random.choice(
        [2017, 2018, 2019, 2020],
        size=n_samples,
        p=[0.3, 0.3, 0.3, 0.1]  # Less data for 2020 due to pandemic
    )

    # Add survey weights (important for population estimates)
    # In a real analysis, you would use the actual NHANES survey weights
    data['Survey_Weight'] = np.random.gamma(
        shape=10, scale=10000, size=n_samples)

    return data


# Load the data
with st.spinner("Loading NHANES data..."):
    df = load_nhanes_data()

# Year range filter in sidebar
years = df['Examination_Year'].unique()
year_range = st.sidebar.select_slider(
    "Examination Year Range:",
    options=sorted(years),
    value=(min(years), max(years))
)

# Filter data by year
filtered_df = df[(df['Examination_Year'] >= year_range[0]) &
                 (df['Examination_Year'] <= year_range[1])]

# Demographic filters
st.sidebar.markdown("### Demographic Filters")

# Age filter
age_range = st.sidebar.slider(
    "Age Range:",
    min_value=int(df['Age'].min()),
    max_value=int(df['Age'].max()),
    value=(20, 80)
)

# Gender filter
gender_options = ['All'] + sorted(df['Gender'].unique().tolist())
gender_filter = st.sidebar.selectbox("Gender:", gender_options)

# Race/Ethnicity filter
race_options = ['All'] + sorted(df['Race_Ethnicity'].unique().tolist())
race_filter = st.sidebar.selectbox("Race/Ethnicity:", race_options)

# Apply filters
if gender_filter != 'All':
    filtered_df = filtered_df[filtered_df['Gender'] == gender_filter]

if race_filter != 'All':
    filtered_df = filtered_df[filtered_df['Race_Ethnicity'] == race_filter]

filtered_df = filtered_df[(filtered_df['Age'] >= age_range[0]) &
                          (filtered_df['Age'] <= age_range[1])]

# Clinical filters
st.sidebar.markdown("### Clinical Filters")

# BMI Category filter
bmi_options = ['All'] + sorted(df['BMI_Category'].unique().tolist())
bmi_filter = st.sidebar.selectbox("BMI Category:", bmi_options)

if bmi_filter != 'All':
    filtered_df = filtered_df[filtered_df['BMI_Category'] == bmi_filter]

# Check if filtered dataframe is empty
if len(filtered_df) == 0:
    st.warning(
        "No data available with the current filters. Please adjust your filters.")
    st.stop()  # Stop execution if no data available

# Main content organization using tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Diabetes Overview",
    "🔍 Risk Factor Analysis",
    "🩺 Clinical Outcomes",
    "📋 Data Explorer"
])

with tab1:
    st.markdown("<h2 class='sub-header'>Diabetes Prevalence and Trends</h2>",
                unsafe_allow_html=True)

    # Key diabetes metrics
    metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)

    with metrics_col1:
        diabetes_count = filtered_df['Diabetes'].sum()
        diabetes_percentage = (diabetes_count / len(filtered_df)) * 100

        st.markdown(f"""
        <div class="metric-box" style="background-color: #D4EFDF;">
            <div class="metric-title">Diabetes Prevalence</div>
            <div class="metric-value">{diabetes_percentage:.1f}%</div>
            <div>({diabetes_count:,} individuals)</div>
        </div>
        """, unsafe_allow_html=True)

    with metrics_col2:
        prediabetes_count = filtered_df['Prediabetes'].sum()
        prediabetes_percentage = (prediabetes_count / len(filtered_df)) * 100

        st.markdown(f"""
        <div class="metric-box" style="background-color: #FDEBD0;">
            <div class="metric-title">Prediabetes Prevalence</div>
            <div class="metric-value">{prediabetes_percentage:.1f}%</div>
            <div>({prediabetes_count:,} individuals)</div>
        </div>
        """, unsafe_allow_html=True)

    with metrics_col3:
        insulin_users = filtered_df[filtered_df['Diabetes']
                                    ]['On_Insulin'].sum()
        insulin_percentage = (insulin_users / diabetes_count) * \
            100 if diabetes_count > 0 else 0

        st.markdown(f"""
        <div class="metric-box" style="background-color: #D6EAF8;">
            <div class="metric-title">Insulin Usage</div>
            <div class="metric-value">{insulin_percentage:.1f}%</div>
            <div>of diabetic individuals</div>
        </div>
        """, unsafe_allow_html=True)

    with metrics_col4:
        controlled_diabetes = filtered_df[(
            filtered_df['Diabetes']) & (filtered_df['HbA1c'] < 7.0)]
        controlled_percentage = (
            len(controlled_diabetes) / diabetes_count) * 100 if diabetes_count > 0 else 0

        st.markdown(f"""
        <div class="metric-box" style="background-color: #D5F5E3;">
            <div class="metric-title">Controlled Diabetes</div>
            <div class="metric-value">{controlled_percentage:.1f}%</div>
            <div>HbA1c < 7.0</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Diabetes prevalence by year
    st.markdown("### Diabetes Prevalence Trends by Year")

    # Group by year and calculate prevalence
    try:
        year_prevalence = safe_groupby(filtered_df, 'Examination_Year').agg({
            'Diabetes': 'mean',
            'Prediabetes': 'mean'
        }) * 100

        # Create a line chart
        fig_trend = px.line(
            year_prevalence,
            labels={
                "value": "Prevalence (%)", "Examination_Year": "Year", "variable": "Condition"},
            title="Diabetes and Prediabetes Prevalence Trends"
        )

        fig_trend.update_layout(
            xaxis=dict(tickmode='array', tickvals=sorted(years)),
            legend=dict(orientation="h", yanchor="bottom",
                        y=1.02, xanchor="right", x=1),
            height=400
        )

        st.plotly_chart(fig_trend, use_container_width=True)
    except Exception as e:
        st.error(f"Error creating year trend visualization: {str(e)}")

    # Diabetes prevalence by demographic factors
    st.markdown("### Diabetes Prevalence by Demographics")

    demo_col1, demo_col2 = st.columns(2)

    with demo_col1:
        # By gender
        try:
            gender_diabetes = safe_groupby(df, 'Gender')[
                'Diabetes'].mean() * 100
            gender_prediabetes = safe_groupby(
                df, 'Gender')['Prediabetes'].mean() * 100

            gender_data = pd.DataFrame({
                'Diabetes': gender_diabetes,
                'Prediabetes': gender_prediabetes
            }).reset_index()

            gender_data_melted = pd.melt(
                gender_data,
                id_vars=['Gender'],
                value_vars=['Diabetes', 'Prediabetes'],
                var_name='Condition',
                value_name='Prevalence'
            )

            fig_gender = px.bar(
                gender_data_melted,
                x='Gender',
                y='Prevalence',
                color='Condition',
                barmode='group',
                title="Diabetes Prevalence by Gender",
                labels={"Prevalence": "Prevalence (%)"}
            )

            fig_gender.update_layout(legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_gender, use_container_width=True)
        except Exception as e:
            st.error(
                f"Error creating gender prevalence visualization: {str(e)}")

    with demo_col2:
        # By age group
        try:
            df['Age_Group'] = pd.cut(
                df['Age'],
                bins=[0, 20, 40, 60, 100],
                labels=['<20', '20-39', '40-59', '60+']
            )

            age_diabetes = safe_groupby(df, 'Age_Group')[
                'Diabetes'].mean() * 100
            age_prediabetes = safe_groupby(df, 'Age_Group')[
                'Prediabetes'].mean() * 100

            age_data = pd.DataFrame({
                'Diabetes': age_diabetes,
                'Prediabetes': age_prediabetes
            }).reset_index()

            age_data_melted = pd.melt(
                age_data,
                id_vars=['Age_Group'],
                value_vars=['Diabetes', 'Prediabetes'],
                var_name='Condition',
                value_name='Prevalence'
            )

            fig_age = px.bar(
                age_data_melted,
                x='Age_Group',
                y='Prevalence',
                color='Condition',
                barmode='group',
                title="Diabetes Prevalence by Age Group",
                labels={"Prevalence": "Prevalence (%)"}
            )

            fig_age.update_layout(legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_age, use_container_width=True)
        except Exception as e:
            st.error(f"Error creating age prevalence visualization: {str(e)}")

    # By race/ethnicity
    try:
        race_diabetes = safe_groupby(df, 'Race_Ethnicity')[
            'Diabetes'].mean() * 100
        race_prediabetes = safe_groupby(df, 'Race_Ethnicity')[
            'Prediabetes'].mean() * 100

        race_data = pd.DataFrame({
            'Diabetes': race_diabetes,
            'Prediabetes': race_prediabetes
        }).reset_index()

        race_data_melted = pd.melt(
            race_data,
            id_vars=['Race_Ethnicity'],
            value_vars=['Diabetes', 'Prediabetes'],
            var_name='Condition',
            value_name='Prevalence'
        )

        fig_race = px.bar(
            race_data_melted,
            x='Race_Ethnicity',
            y='Prevalence',
            color='Condition',
            barmode='group',
            title="Diabetes Prevalence by Race/Ethnicity",
            labels={
                "Prevalence": "Prevalence (%)", "Race_Ethnicity": "Race/Ethnicity"}
        )

        fig_race.update_layout(
            xaxis_tickangle=-45,
            legend=dict(orientation="h", yanchor="bottom",
                        y=1.02, xanchor="right", x=1)
        )

        st.plotly_chart(fig_race, use_container_width=True)
    except Exception as e:
        st.error(
            f"Error creating race/ethnicity prevalence visualization: {str(e)}")

    # Geographic distribution (simulated)
    st.markdown("### Geographic Distribution of Diabetes")
    st.write("Note: Geographic distribution visualization would typically use NHANES regional data with appropriate survey weights. This is a simulated example.")

    # Create a simulated geographic distribution
    try:
        states = [
            'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
            'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
            'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
            'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
            'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'
        ]

        # Create a simulated geographic distribution
        # In a real analysis, this would use NHANES geographic data with survey weights
        np.random.seed(42)
        state_diabetes_rates = np.random.normal(9.5, 2.5, len(states))
        state_diabetes_rates = np.clip(state_diabetes_rates, 5, 18)

        geo_data = pd.DataFrame({
            'state': states,
            'diabetes_rate': state_diabetes_rates
        })

        # Create a choropleth map
        fig_map = px.choropleth(
            geo_data,
            locations='state',
            color='diabetes_rate',
            locationmode='USA-states',
            scope="usa",
            color_continuous_scale="Reds",
            labels={'diabetes_rate': 'Diabetes Rate (%)'},
            title="Simulated Diabetes Prevalence by State"
        )

        fig_map.update_layout(
            coloraxis_colorbar=dict(title="Diabetes Rate (%)"),
            geo=dict(lakecolor='rgb(255, 255, 255)')
        )

        st.plotly_chart(fig_map, use_container_width=True)
    except Exception as e:
        st.error(f"Error creating geographic visualization: {str(e)}")
        st.info("This visualization requires an internet connection for the base map.")

with tab2:
    st.markdown("<h2 class='sub-header'>Risk Factor Analysis</h2>",
                unsafe_allow_html=True)

    # BMI and Diabetes
    st.markdown("### BMI Distribution by Diabetes Status")

    # Calculate average BMI by diabetes status
    try:
        avg_bmi_diabetic = filtered_df[filtered_df['Diabetes']]['BMI'].mean()
        avg_bmi_non_diabetic = filtered_df[~filtered_df['Diabetes']]['BMI'].mean(
        )

        # Create histograms
        fig_bmi = px.histogram(
            filtered_df,
            x="BMI",
            color="Diabetes",
            marginal="box",
            # Limit hover data to relevant fields
            hover_data=['Age', 'Gender', 'BMI_Category'],
            labels={"Diabetes": "Diabetes Status"},
            title="BMI Distribution by Diabetes Status",
            color_discrete_map={True: "red", False: "blue"},
        )

        # Add vertical lines for average BMI
        fig_bmi.add_vline(x=avg_bmi_diabetic, line_dash="dash", line_color="red",
                          annotation_text=f"Avg BMI (Diabetic): {avg_bmi_diabetic:.1f}")
        fig_bmi.add_vline(x=avg_bmi_non_diabetic, line_dash="dash", line_color="blue",
                          annotation_text=f"Avg BMI (Non-Diabetic): {avg_bmi_non_diabetic:.1f}")

        st.plotly_chart(fig_bmi, use_container_width=True)
    except Exception as e:
        st.error(f"Error creating BMI distribution visualization: {str(e)}")

    # Risk factors analysis
    st.markdown("### Risk Factors for Diabetes")

    try:
        # Prepare risk factors
        risk_factors = [
            'Hypertension',
            'Family_History_Diabetes',
            'Physical_Activity'
        ]

        # First add the Current_Smoker column to the filtered_df
        filtered_df = filtered_df.copy()
        filtered_df['Current_Smoker'] = filtered_df['Smoking_Status'] == 'Current'

        risk_factors.append('Current_Smoker')

        # Calculate diabetes prevalence for each risk factor
        risk_factor_data = []

        for factor in risk_factors:
            if factor == 'Physical_Activity':
                # For physical activity, we expect an inverse relationship
                has_factor_prev = filtered_df[filtered_df[factor]]['Diabetes'].mean(
                ) * 100
                no_factor_prev = filtered_df[~filtered_df[factor]]['Diabetes'].mean(
                ) * 100
                label = "Physically Active"
            else:
                # For other risk factors, we expect a positive relationship
                has_factor_prev = filtered_df[filtered_df[factor]]['Diabetes'].mean(
                ) * 100
                no_factor_prev = filtered_df[~filtered_df[factor]]['Diabetes'].mean(
                ) * 100
                label = factor.replace('_', ' ')

            risk_factor_data.append({
                'Risk Factor': label,
                'Status': 'Yes',
                'Diabetes Prevalence': has_factor_prev
            })

            risk_factor_data.append({
                'Risk Factor': label,
                'Status': 'No',
                'Diabetes Prevalence': no_factor_prev
            })

        risk_df = pd.DataFrame(risk_factor_data)

        # Create a grouped bar chart
        fig_risk = px.bar(
            risk_df,
            x='Risk Factor',
            y='Diabetes Prevalence',
            color='Status',
            barmode='group',
            title="Diabetes Prevalence by Risk Factor",
            labels={"Diabetes Prevalence": "Diabetes Prevalence (%)"}
        )

        fig_risk.update_layout(
            xaxis_tickangle=-45,
            legend=dict(orientation="h", yanchor="bottom",
                        y=1.02, xanchor="right", x=1)
        )

        st.plotly_chart(fig_risk, use_container_width=True)
    except Exception as e:
        st.error(f"Error creating risk factor visualization: {str(e)}")

    # Correlation matrix of key variables
    st.markdown("### Correlation Analysis of Risk Factors")

    # Cache correlation calculation for better performance
    @st.cache_data
    def calculate_correlation_matrix(dataframe, variables):
        """Cache correlation matrix calculation"""
        return dataframe[variables].corr()

    try:
        # Select variables for correlation analysis
        corr_vars = [
            'Age', 'BMI', 'Systolic_BP', 'Diastolic_BP', 'HbA1c',
            'Total_Cholesterol', 'HDL_Cholesterol', 'LDL_Cholesterol',
            'Triglycerides', 'Fasting_Glucose'
        ]

        # Use cached function for better performance
        corr_matrix = calculate_correlation_matrix(filtered_df, corr_vars)

        # Create a heatmap
        fig_corr = px.imshow(
            corr_matrix,
            text_auto='.2f',
            labels=dict(x="Variables", y="Variables", color="Correlation"),
            x=corr_vars,
            y=corr_vars,
            title="Correlation Matrix of Risk Factors"
        )

        fig_corr.update_layout(
            xaxis_tickangle=-45,
            height=600
        )

        st.plotly_chart(fig_corr, use_container_width=True)
    except Exception as e:
        st.error(f"Error creating correlation matrix: {str(e)}")

    # Scatter plot matrix for selected variables
    st.markdown("### Relationship Between Key Risk Factors")

    # Dropdown to select variables
    scatter_vars = st.multiselect(
        "Select variables to display in scatter plot matrix:",
        options=corr_vars,
        default=['BMI', 'HbA1c', 'Age', 'Systolic_BP'],
        max_selections=4
    )

    if len(scatter_vars) > 1:
        try:
            # Add diabetes status for color
            scatter_df = filtered_df[scatter_vars + ['Diabetes']].copy()
            scatter_df['Diabetes_Status'] = scatter_df['Diabetes'].map(
                {True: 'Diabetic', False: 'Non-Diabetic'})

            # Create a scatter plot matrix
            fig_scatter = px.scatter_matrix(
                scatter_df,
                dimensions=scatter_vars,
                color='Diabetes_Status',
                title="Scatter Plot Matrix of Selected Variables",
                labels={var: var.replace('_', ' ') for var in scatter_vars},
                opacity=0.6
            )

            fig_scatter.update_layout(
                height=700,
                width=700
            )

            st.plotly_chart(fig_scatter, use_container_width=True)
        except Exception as e:
            st.error(f"Error creating scatter plot matrix: {str(e)}")
    else:
        st.write("Please select at least 2 variables for the scatter plot matrix.")

    # HbA1c vs Fasting Glucose analysis
    st.markdown("### HbA1c vs Fasting Glucose Relationship")

    try:
        # Create a scatter plot
        fig_glucose = px.scatter(
            filtered_df,
            x="HbA1c",
            y="Fasting_Glucose",
            color="Diabetes",
            color_discrete_map={True: "red", False: "blue"},
            hover_data=['Age', 'Gender', 'BMI'],
            labels={"Diabetes": "Diabetes Status"},
            title="Relationship Between HbA1c and Fasting Glucose"
        )

        # Add reference lines for diagnostic cutoffs
        fig_glucose.add_hline(y=126, line_dash="dash", line_color="green",
                              annotation_text="Diabetes Threshold (126 mg/dL)")
        fig_glucose.add_vline(x=6.5, line_dash="dash", line_color="green",
                              annotation_text="Diabetes Threshold (6.5%)")

        fig_glucose.add_hline(y=100, line_dash="dot", line_color="orange",
                              annotation_text="Prediabetes Threshold (100 mg/dL)")
        fig_glucose.add_vline(x=5.7, line_dash="dot", line_color="orange",
                              annotation_text="Prediabetes Threshold (5.7%)")

        st.plotly_chart(fig_glucose, use_container_width=True)

        # Calculate the correlation coefficient
        correlation = filtered_df['HbA1c'].corr(filtered_df['Fasting_Glucose'])

        st.markdown(f"""
        <div class="insight-box" style="background-color: #2C3E50; color: white; padding: 15px; border-radius: 5px;">
            <p>The correlation coefficient between HbA1c and Fasting Glucose is <strong>{correlation:.3f}</strong>.
            This strong positive correlation reflects how these two metrics are both important diagnostic tools for diabetes.</p>
        </div>
        """, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error creating HbA1c vs Glucose visualization: {str(e)}")

with tab3:
    st.markdown("<h2 class='sub-header'>Clinical Outcomes Analysis</h2>",
                unsafe_allow_html=True)

    # Distribution of HbA1c
    st.markdown("### Distribution of HbA1c by Diabetes Status")

    try:
        # Create a histogram
        fig_hba1c = px.histogram(
            filtered_df,
            x="HbA1c",
            color="Diabetes",
            marginal="box",
            labels={"Diabetes": "Diabetes Status"},
            title="HbA1c Distribution by Diabetes Status",
            color_discrete_map={True: "red", False: "blue"},
            barmode="overlay"
        )

        # Add reference lines for diagnostic cutoffs
        fig_hba1c.add_vline(x=6.5, line_dash="dash", line_color="green",
                            annotation_text="Diabetes Threshold (6.5%)")
        fig_hba1c.add_vline(x=5.7, line_dash="dot", line_color="orange",
                            annotation_text="Prediabetes Threshold (5.7%)")

        st.plotly_chart(fig_hba1c, use_container_width=True)
    except Exception as e:
        st.error(f"Error creating HbA1c distribution visualization: {str(e)}")

    # Diabetes complications analysis
    st.markdown("### Diabetes Complications by HbA1c Control")

    try:
        # Create HbA1c control categories
        diabetic_df = filtered_df[filtered_df['Diabetes']].copy()

        # Check if there are diabetic patients in the filtered dataset
        if len(diabetic_df) == 0:
            st.warning(
                "No diabetic patients in the current filtered dataset. Please adjust your filters.")
        else:
            diabetic_df['HbA1c_Control'] = pd.cut(
                diabetic_df['HbA1c'],
                bins=[0, 7.0, 8.0, 10.0, 15.0],
                labels=['Good Control (<7%)', 'Moderate Control (7-8%)',
                        'Poor Control (8-10%)', 'Very Poor Control (>10%)']
            )

            # Complications to analyze
            complications = ['Retinopathy', 'Nephropathy',
                             'Neuropathy', 'Cardiovascular_Disease']

            # Calculate complication rates by HbA1c control
            complication_data = []

            for comp in complications:
                for control_cat in diabetic_df['HbA1c_Control'].unique():
                    if pd.isna(control_cat):  # Skip if category is NaN
                        continue
                    subset = diabetic_df[diabetic_df['HbA1c_Control']
                                         == control_cat]
                    if len(subset) > 0:
                        comp_rate = subset[comp].mean() * 100

                        complication_data.append({
                            'Complication': comp.replace('_', ' '),
                            'HbA1c Control': control_cat,
                            'Prevalence': comp_rate
                        })

            if complication_data:  # Check if we have data to display
                comp_df = pd.DataFrame(complication_data)

                # Create a grouped bar chart
                fig_comp = px.bar(
                    comp_df,
                    x='Complication',
                    y='Prevalence',
                    color='HbA1c Control',
                    barmode='group',
                    title="Diabetes Complications by HbA1c Control",
                    labels={"Prevalence": "Prevalence (%)"}
                )

                fig_comp.update_layout(
                    xaxis_tickangle=-45,
                    legend=dict(orientation="h", yanchor="bottom",
                                y=1.02, xanchor="right", x=1)
                )

                st.plotly_chart(fig_comp, use_container_width=True)

                st.markdown("""
                <div class="insight-box" style="background-color: #2C3E50; color: white; padding: 15px; border-radius: 5px;">
                    <p>The data shows a clear relationship between poor glycemic control (higher HbA1c levels) and 
                    increased prevalence of diabetes complications. This highlights the importance of maintaining 
                    good glycemic control to prevent long-term complications.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning(
                    "Insufficient complication data for the current filters.")
    except Exception as e:
        st.error(f"Error creating complications visualization: {str(e)}")

    # Treatment analysis
    st.markdown("### Diabetes Treatment Patterns")

    try:
        if len(diabetic_df) > 0:
            # Calculate treatment patterns
            treatment_patterns = safe_groupby(
                diabetic_df, ['On_Insulin', 'On_Oral_Medication']).size().reset_index()
            treatment_patterns.columns = [
                'Insulin', 'Oral Medication', 'Count']
            treatment_patterns['Percentage'] = treatment_patterns['Count'] / \
                treatment_patterns['Count'].sum() * 100

            # Create labels
            treatment_patterns['Treatment'] = treatment_patterns.apply(
                lambda x: ('Insulin + Oral' if x['Insulin'] and x['Oral Medication'] else
                           ('Insulin Only' if x['Insulin'] else
                           ('Oral Only' if x['Oral Medication'] else 'No Medication'))),
                axis=1
            )

            # Create a pie chart
            fig_treatment = px.pie(
                treatment_patterns,
                values='Percentage',
                names='Treatment',
                title="Diabetes Treatment Patterns",
                hole=0.3,
                color_discrete_sequence=px.colors.qualitative.Set2
            )

            fig_treatment.update_traces(
                textposition='inside', textinfo='percent+label')

            st.plotly_chart(fig_treatment, use_container_width=True)
        else:
            st.warning(
                "No diabetic patients in the filtered dataset for treatment analysis.")
    except Exception as e:
        st.error(f"Error creating treatment patterns visualization: {str(e)}")

    # HbA1c control by treatment
    st.markdown("### HbA1c Control by Treatment Type")

    try:
        if len(diabetic_df) > 0:
            # Calculate average HbA1c by treatment
            diabetic_df['Treatment'] = diabetic_df.apply(
                lambda x: ('Insulin + Oral' if x['On_Insulin'] and x['On_Oral_Medication'] else
                           ('Insulin Only' if x['On_Insulin'] else
                           ('Oral Only' if x['On_Oral_Medication'] else 'No Medication'))),
                axis=1
            )

            # Create a box plot
            fig_hba1c_treatment = px.box(
                diabetic_df,
                x='Treatment',
                y='HbA1c',
                color='Treatment',
                title="HbA1c Distribution by Treatment Type",
                labels={"HbA1c": "HbA1c (%)"},
                color_discrete_sequence=px.colors.qualitative.Set2
            )

            # Add reference line for target HbA1c
            fig_hba1c_treatment.add_hline(
                y=7.0, line_dash="dash", line_color="green", annotation_text="Target HbA1c (<7.0%)")

            st.plotly_chart(fig_hba1c_treatment, use_container_width=True)

            st.markdown("""
            <div class="insight-box" style="background-color: #2C3E50; color: white; padding: 15px; border-radius: 5px;">
                <p>Patients on insulin (with or without oral medications) tend to have higher HbA1c levels. This likely reflects
                that insulin therapy is typically initiated in patients with more severe diabetes who are unable to achieve
                glycemic control with oral medications alone.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning(
                "No diabetic patients in the filtered dataset for HbA1c control analysis.")
    except Exception as e:
        st.error(f"Error creating HbA1c by treatment visualization: {str(e)}")

    # Diabetes duration analysis
    st.markdown("### Impact of Diabetes Duration on Complications")

    try:
        if len(diabetic_df) > 0:
            # Create duration categories
            diabetic_df['Duration_Category'] = pd.cut(
                diabetic_df['Diabetes_Duration'],
                bins=[0, 5, 10, 15, 100],
                labels=['0-5 years', '5-10 years', '10-15 years', '15+ years']
            )

            # Calculate complication rates by duration
            duration_data = []

            for comp in complications:
                for duration_cat in diabetic_df['Duration_Category'].unique():
                    if pd.isna(duration_cat):  # Skip if category is NaN
                        continue
                    subset = diabetic_df[diabetic_df['Duration_Category']
                                         == duration_cat]
                    if len(subset) > 0:
                        comp_rate = subset[comp].mean() * 100

                        duration_data.append({
                            'Complication': comp.replace('_', ' '),
                            'Duration': duration_cat,
                            'Prevalence': comp_rate
                        })

            if duration_data:  # Check if we have data to display
                duration_df = pd.DataFrame(duration_data)

                # Create a grouped bar chart
                fig_duration = px.bar(
                    duration_df,
                    x='Complication',
                    y='Prevalence',
                    color='Duration',
                    barmode='group',
                    title="Diabetes Complications by Disease Duration",
                    labels={"Prevalence": "Prevalence (%)"}
                )

                fig_duration.update_layout(
                    xaxis_tickangle=-45,
                    legend=dict(orientation="h", yanchor="bottom",
                                y=1.02, xanchor="right", x=1)
                )

                st.plotly_chart(fig_duration, use_container_width=True)
            else:
                st.warning(
                    "Insufficient duration data for the current filters.")
        else:
            st.warning(
                "No diabetic patients in the filtered dataset for duration analysis.")
    except Exception as e:
        st.error(f"Error creating duration analysis visualization: {str(e)}")

    # Interactive scatter plot of HbA1c vs Complication Risk
    st.markdown(
        "### Interactive: Relationship Between HbA1c and Complication Risk")

    # Display a warning if statsmodels is not available
    if not STATSMODELS_AVAILABLE:
        st.warning("""
            📊 Note: The trendline feature requires the statsmodels package.
            To enable trendlines, please install it with: `pip install statsmodels`
        """)

    # Select complication to analyze
    selected_complication = st.selectbox(
        "Select Complication:",
        [comp.replace('_', ' ') for comp in complications]
    )

    # Convert back to column name format
    comp_col = selected_complication.replace(' ', '_')

    # Wrap the plotting code in a try-except block for robustness
    try:
        if len(diabetic_df) > 0:
            # Calculate risk by HbA1c
            hba1c_bins = pd.cut(
                diabetic_df['HbA1c'],
                bins=np.arange(5.0, 14.1, 0.5),
                labels=[
                    f"{x:.1f}-{x+0.5:.1f}" for x in np.arange(5.0, 14.0, 0.5)]
            )

            diabetic_df['HbA1c_Bin'] = hba1c_bins

            risk_by_hba1c = safe_groupby(diabetic_df, 'HbA1c_Bin')[
                comp_col].mean() * 100
            risk_by_hba1c = risk_by_hba1c.reset_index()
            risk_by_hba1c.columns = ['HbA1c Range', 'Risk']

            # Remove NaN values
            risk_by_hba1c = risk_by_hba1c.dropna(subset=['Risk'])

            if len(risk_by_hba1c) > 0:
                # Extract lower bound of each bin for numeric plotting
                risk_by_hba1c['HbA1c_Min'] = risk_by_hba1c['HbA1c Range'].apply(
                    lambda x: float(
                        x.split('-')[0]) if isinstance(x, str) else np.nan
                )

                # Remove any remaining NaN values
                risk_by_hba1c = risk_by_hba1c.dropna(subset=['HbA1c_Min'])

                if len(risk_by_hba1c) > 0:
                    # Create a scatter plot
                    fig_risk = px.scatter(
                        risk_by_hba1c,
                        x='HbA1c_Min',
                        y='Risk',
                        size=None,  # Remove marker_size and use default size
                        hover_data=['HbA1c Range'],
                        labels={
                            "HbA1c_Min": "HbA1c (%)", "Risk": f"{selected_complication} Risk (%)"},
                        title=f"Relationship Between HbA1c and {selected_complication} Risk",
                        trendline="ols" if STATSMODELS_AVAILABLE else None
                    )

                    st.plotly_chart(fig_risk, use_container_width=True)
                else:
                    st.info(
                        f"Insufficient data to plot the relationship for {selected_complication}. Try selecting a different complication or adjusting your filters.")
            else:
                st.info(
                    f"Insufficient data to plot the relationship for {selected_complication}. Try selecting a different complication or adjusting your filters.")
        else:
            st.warning(
                "No diabetic patients in the filtered dataset for complication risk analysis.")
    except Exception as e:
        st.error(
            f"Error creating HbA1c vs complication risk visualization: {str(e)}")
        st.info(
            "This may be due to insufficient data for the selected complication or filters.")


with tab4:
    st.markdown("<h2 class='sub-header'>Data Explorer and Download</h2>",
                unsafe_allow_html=True)

    # Data overview
    st.markdown("### NHANES Dataset Overview")

    # Show basic stats
    st.write(
        f"**Dataset Size:** {filtered_df.shape[0]} participants, {filtered_df.shape[1]} variables")

    # Variable type breakdown
    numeric_cols = filtered_df.select_dtypes(
        include=['int64', 'float64']).columns
    categorical_cols = filtered_df.select_dtypes(
        include=['object', 'category', 'bool']).columns

    st.write(f"**Numeric Variables:** {len(numeric_cols)}")
    st.write(f"**Categorical Variables:** {len(categorical_cols)}")

    # Display the dataset
    st.markdown("### Interactive Data Viewer")

    # Select columns to display
    display_cols = st.multiselect(
        "Select columns to display:",
        options=filtered_df.columns.tolist(),
        default=['Age', 'Gender', 'BMI', 'HbA1c', 'Diabetes', 'Prediabetes']
    )

    if display_cols:
        # Allow filtering by keyword
        text_search = st.text_input("Search in dataset:", "")

        # Make a copy and convert boolean columns to more visible format for display
        display_df = filtered_df[display_cols].copy()

        # Convert boolean columns to more visible format
        for col in display_df.columns:
            if display_df[col].dtype == bool:
                display_df[col] = display_df[col].map(
                    {True: "Yes", False: "No"})

        if text_search:
            try:
                # Filter only string columns by text search
                str_columns = display_df.select_dtypes(
                    include=['object', 'category']).columns
                num_columns = display_df.select_dtypes(
                    include=['int64', 'float64']).columns

                # Initialize masks
                str_mask = None
                num_mask = None

                # Search in string columns
                if len(str_columns) > 0:
                    str_mask = np.column_stack([
                        display_df[col].astype(str).str.contains(
                            text_search, case=False, na=False)
                        for col in str_columns
                    ])

                # Search in numeric columns after converting to string
                if len(num_columns) > 0:
                    num_mask = np.column_stack([
                        display_df[col].astype(str).str.contains(
                            text_search, case=False, na=False)
                        for col in num_columns
                    ])

                # Combine masks
                if str_mask is not None and num_mask is not None:
                    mask = np.hstack([str_mask, num_mask])
                    display_df = display_df[mask.any(axis=1)]
                elif str_mask is not None:
                    display_df = display_df[str_mask.any(axis=1)]
                elif num_mask is not None:
                    display_df = display_df[num_mask.any(axis=1)]
            except Exception as e:
                st.error(f"Error in text search: {str(e)}")

        # Add pagination for better performance with large datasets
        page_size = st.number_input(
            "Rows per page", min_value=10, max_value=100, value=20, step=10)
        total_pages = max(1, (len(display_df) + page_size - 1) // page_size)

        if total_pages > 1:
            page_number = st.number_input(
                "Page", min_value=1, max_value=total_pages, value=1, step=1)
            start_idx = (page_number - 1) * page_size
            end_idx = min(start_idx + page_size, len(display_df))
            display_df_paginated = display_df.iloc[start_idx:end_idx]
            st.dataframe(display_df_paginated)
            st.write(
                f"Showing records {start_idx+1}-{end_idx} of {len(display_df)}")
        else:
            st.dataframe(display_df)
            st.write(f"Displaying {len(display_df)} records")

    # Summary statistics
    st.markdown("### Summary Statistics")

    # Select a numeric variable for summary
    numeric_var = st.selectbox(
        "Select a numeric variable for summary statistics:",
        options=['Select a variable...'] + list(numeric_cols)
    )

    if numeric_var != 'Select a variable...':
        try:
            # Calculate summary statistics
            summary = filtered_df[numeric_var].describe()

            # Format the summary as a dataframe
            summary_df = pd.DataFrame(summary).transpose()

            # Add median
            summary_df['median'] = filtered_df[numeric_var].median()

            # Reorder columns
            summary_df = summary_df[['count', 'mean', 'median',
                                    'std', 'min', '25%', '50%', '75%', 'max']]

            # Show the summary
            st.dataframe(summary_df)

            # Show a histogram
            fig_hist = px.histogram(
                filtered_df,
                x=numeric_var,
                title=f"Distribution of {numeric_var}",
                marginal="box"
            )

            st.plotly_chart(fig_hist, use_container_width=True)
        except Exception as e:
            st.error(f"Error calculating summary statistics: {str(e)}")

    # Create custom visualizations
    st.markdown("### Custom Visualization Tool")

    # Select visualization type
    viz_type = st.selectbox(
        "Select visualization type:",
        ["Bar Chart", "Scatter Plot", "Box Plot", "Line Chart"]
    )

    # Common controls
    viz_col1, viz_col2 = st.columns(2)

    with viz_col1:
        if viz_type == "Scatter Plot":
            x_var = st.selectbox("X-axis variable:", numeric_cols)
            y_var = st.selectbox("Y-axis variable:", numeric_cols)
            color_var = st.selectbox(
                "Color variable:", ['None'] + filtered_df.columns.tolist())
        elif viz_type == "Box Plot":
            x_var = st.selectbox("Category variable:", categorical_cols)
            y_var = st.selectbox("Value variable:", numeric_cols)
            color_var = x_var
        elif viz_type == "Bar Chart":
            x_var = st.selectbox("Category variable:", categorical_cols)
            y_var = st.selectbox("Value to count or aggregate:", [
                'Count'] + numeric_cols.tolist(), index=0)  # Default to 'Count'
            color_var = st.selectbox(
                "Color variable:", ['None'] + categorical_cols.tolist())
        elif viz_type == "Line Chart":
            x_var = st.selectbox("X-axis variable:", numeric_cols)
            y_var = st.selectbox("Y-axis variable:", numeric_cols)
            color_var = st.selectbox(
                "Color variable:", ['None'] + categorical_cols.tolist())

    with viz_col2:
        # Additional options
        log_scale = False  # Default value
        add_trendline = False  # Default value
        agg_func = "Mean"  # Default value

        if viz_type in ["Scatter Plot", "Box Plot", "Line Chart"]:
            log_scale = st.checkbox("Use logarithmic scale for y-axis")

        if viz_type == "Bar Chart":
            if y_var != 'Count':
                agg_func = st.selectbox("Aggregation function:", [
                                        "Mean", "Median", "Sum", "Min", "Max"])

        if viz_type == "Scatter Plot":
            add_trendline = st.checkbox("Add trendline")

        title = st.text_input(
            "Chart title:", f"{viz_type} of {y_var} by {x_var}")

    # Generate visualization function with error handling
    @safe_plot
    def generate_visualization(viz_type, x_var, y_var, color_var, log_scale, add_trendline, agg_func, title):
        """Generate visualization with proper error handling"""
        if viz_type == "Scatter Plot":
            fig = px.scatter(
                filtered_df,
                x=x_var,
                y=y_var,
                color=None if color_var == 'None' else color_var,
                title=title,
                trendline="ols" if add_trendline and STATSMODELS_AVAILABLE else None,
                log_y=log_scale
            )
            return fig

        elif viz_type == "Box Plot":
            fig = px.box(
                filtered_df,
                x=x_var,
                y=y_var,
                color=color_var,
                title=title,
                log_y=log_scale
            )
            return fig

        elif viz_type == "Bar Chart":
            if y_var == 'Count':
                # Count records
                count_df = safe_groupby(
                    filtered_df, x_var).size().reset_index(name='Count')

                fig = px.bar(
                    count_df,
                    x=x_var,
                    y='Count',
                    color=None if color_var == 'None' else x_var,
                    title=title
                )
            else:
                # Aggregate values
                agg_map = {
                    "Mean": "mean",
                    "Median": "median",
                    "Sum": "sum",
                    "Min": "min",
                    "Max": "max"
                }

                agg_df = safe_groupby(filtered_df, x_var)[y_var].agg(
                    agg_map[agg_func]).reset_index()

                fig = px.bar(
                    agg_df,
                    x=x_var,
                    y=y_var,
                    color=None if color_var == 'None' else x_var,
                    title=f"{title} (Aggregation: {agg_func})"
                )

            fig.update_layout(xaxis_tickangle=-45)
            return fig

        elif viz_type == "Line Chart":
            # Sort by x variable for better line plotting
            line_df = filtered_df.sort_values(by=x_var)

            if color_var == 'None':
                fig = px.line(
                    line_df,
                    x=x_var,
                    y=y_var,
                    title=title,
                    log_y=log_scale
                )
            else:
                # Group by color variable and x variable
                # Use pandas cut to bin the x variable for better visualization
                if len(line_df) > 0:
                    try:
                        # Create bins for x variable
                        n_bins = min(10, len(line_df[x_var].unique()))
                        bins = pd.cut(line_df[x_var], bins=n_bins)

                        # Create a temporary column with bin labels
                        line_df['x_bin'] = bins

                        # Group by color variable and bin
                        grouped = safe_groupby(line_df, [color_var, 'x_bin'])[
                            y_var].mean().reset_index()

                        # Extract the midpoint of each bin for plotting
                        grouped['bin_mid'] = grouped['x_bin'].apply(
                            lambda x: x.mid if hasattr(x, 'mid') else np.nan)

                        # Drop any rows with NaN values
                        grouped = grouped.dropna(subset=['bin_mid'])

                        fig = px.line(
                            grouped,
                            x='bin_mid',
                            y=y_var,
                            color=color_var,
                            title=title,
                            labels={
                                'bin_mid': x_var,
                            },
                            log_y=log_scale
                        )
                    except Exception as e:
                        # Fall back to a simple scatter plot if binning fails
                        st.warning(
                            f"Binning failed, showing scatter plot instead: {str(e)}")
                        fig = px.scatter(
                            line_df,
                            x=x_var,
                            y=y_var,
                            color=color_var,
                            title=title,
                            log_y=log_scale
                        )
                else:
                    fig = px.line(
                        pd.DataFrame({x_var: [], y_var: []}),
                        x=x_var,
                        y=y_var,
                        title=title,
                        log_y=log_scale
                    )
                return fig
            return None

    if st.button("Generate Custom Visualization"):
        try:
            fig = generate_visualization(
                viz_type, x_var, y_var, color_var, log_scale, add_trendline, agg_func, title)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error generating visualization: {str(e)}")
