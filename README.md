# Cooler Verification System

Scans and validates cooler tag, serial, and asset number against a master list.

## Setup
1. `python -m venv venv && venv\Scripts\activate`
2. `pip install -r requirements.txt`
3. Create `.env` from the example
4. `python manage.py migrate`
5. `python manage.py runserver`