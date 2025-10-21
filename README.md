## Run locally
1. Place your CSVs in data/ with the following names:
campaign_data.csv
product_data.csv
stores_data.csv
event_data.csv
clean_revenue.csv
city_sales.csv
clean all.csv
2. Create a venv and install requirements:
bash
python3 -m venv.venv && source .venv/bin/activate
pip install -r requirements.txt
3. Start Streamlit:
bash
streamlit run app.py
## Notes
- Global filters live in session state and affect charts across pages.
- Map requires `lat` and `lng` in `city_sales.csv`.
- Edit scripts/data_loader.py to change aliases or schemas.