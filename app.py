# app.py

import streamlit as st
import os
import datetime
import pandas as pd
import json
import sqlite3
import hashlib
import hmac
import secrets
from PIL import Image
from google import genai
from google.genai import types
from tools import get_food_nutrition

# 0. DATENBANK INITIALISIEREN (Mit User-System)

def init_db():
    conn = sqlite3.connect("nutriagent.db")
    c = conn.cursor()
    # Tabelle für Benutzer
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password TEXT
                 )''')
    # Tabelle für Logs (angepasst für Multi-User)
    c.execute('''CREATE TABLE IF NOT EXISTS daily_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    date TEXT,
                    meals TEXT,
                    water_ml INTEGER,
                    protein_actual REAL,
                    UNIQUE(username, date)
                 )''')
    conn.commit()
    conn.close()

init_db()

# Hilfsfunktion zum Hashen von Passwörtern
def hash_password(password):
    """Return a salted PBKDF2 password representation for NEW demo accounts."""
    iterations = 600_000
    salt = secrets.token_bytes(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${hashed.hex()}"


def verify_password(password, stored):
    try:
        algorithm, iterations, salt_hex, hash_hex = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(candidate, bytes.fromhex(hash_hex))
    except (ValueError, AttributeError):
        return False


def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY fehlt. Bitte als Umgebungsvariable setzen.")
    return genai.Client(api_key=api_key)


GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

# API keys must never be committed to source control.

# Seitenkonfiguration und Titel
st.set_page_config(page_title="NutriAgent", layout="wide")
st.title("NutriAgent")


# 1. LOGIN & REGISTRIERUNG

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.markdown("### Willkommen! Bitte melde dich an oder registriere dich.")
    login_tab, register_tab = st.tabs(["🔑 Login", "📝 Registrieren"])
    
    with login_tab:
        log_user = st.text_input("Benutzername", key="log_user")
        log_pass = st.text_input("Passwort", type="password", key="log_pass")
        if st.button("Anmelden"):
            conn = sqlite3.connect("nutriagent.db")
            c = conn.cursor()
            c.execute("SELECT password FROM users WHERE username=?", (log_user,))
            result = c.fetchone()
            conn.close()
            
            if result and verify_password(log_pass, result[0]):
                st.session_state.mahlzeiten = []
                st.session_state.wasser_ml = 0
                st.session_state.logged_in = True
                st.session_state.username = log_user
                st.success(f"Erfolgreich angemeldet als {log_user}!")
                st.rerun()
            else:
                st.error("Falscher Benutzername oder Passwort.")
                
    with register_tab:
        reg_user = st.text_input("Neuer Benutzername", key="reg_user")
        reg_pass = st.text_input("Neues Passwort", type="password", key="reg_pass")
        if st.button("Konto erstellen"):
            if reg_user.strip() and len(reg_user.strip()) <= 64 and len(reg_pass) >= 8:
                conn = sqlite3.connect("nutriagent.db")
                c = conn.cursor()
                try:
                    c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (reg_user.strip(), hash_password(reg_pass)))
                    conn.commit()
                    st.success("Konto erstellt! Du kannst dich jetzt anmelden.")
                except sqlite3.IntegrityError:
                    st.error("Dieser Benutzername existiert bereits.")
                finally:
                    conn.close()
            else:
                st.warning("Benutzername (max. 64 Zeichen) und Passwort (mindestens 8 Zeichen) eingeben.")
                
    # App stoppt hier, wenn nicht eingeloggt
    st.stop()


# WENN EINGELOGGT: HAUPTAPPLIKATION

st.markdown(f"#### Willkommen zurück, **{st.session_state.username}**! ")
if st.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.mahlzeiten = []
    st.session_state.wasser_ml = 0
    st.rerun()


# 2. SEITENLEISTE (SIDEBAR) FÜR BENUTZERPROFIL

st.sidebar.header(" Dein Profil")
age = st.sidebar.number_input("Alter", min_value=10, max_value=100, value=25)
weight = st.sidebar.number_input("Gewicht (kg)", min_value=30.0, max_value=200.0, value=72.0)
height = st.sidebar.number_input("Größe (cm)", min_value=100, max_value=250, value=171)
gender = st.sidebar.selectbox("Geschlecht", ["Männlich", "Weiblich"])
goal = st.sidebar.selectbox("Ziel", ["Muskelaufbau", "Fettabbau (Abnehmen)", "Gewicht halten"])

bmi = weight / ((height / 100) ** 2)
bmi_status = "Untergewicht" if bmi < 18.5 else "Normalgewicht" if bmi < 24.9 else "Übergewicht" if bmi < 29.9 else "Adipositas"
st.sidebar.info(f"**Dein BMI:** {bmi:.1f} ({bmi_status})")

if gender == "Männlich":
    bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
else:
    bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161

if goal == "Fettabbau (Abnehmen)":
    target_calories, target_protein, target_fat, target_sugar = bmr * 1.3 - 500, weight * 2.0, weight * 0.8, 20.0
elif goal == "Muskelaufbau":
    target_calories, target_protein, target_fat, target_sugar = bmr * 1.5 + 300, weight * 2.2, weight * 1.0, 35.0
else:
    target_calories, target_protein, target_fat, target_sugar = bmr * 1.4, weight * 1.8, weight * 1.0, 30.0

target_carbs = (target_calories - (target_protein * 4) - (target_fat * 9)) / 4
target_water = round(weight * 35)

DYNAMIC_TARGETS = {
    "calories": round(target_calories),
    "protein": round(target_protein),
    "carbs": round(target_carbs),
    "fat": round(target_fat),
    "sugar": target_sugar,
    "water_ml": target_water
}

st.sidebar.success(f"🎯 Tagesziel:\n{DYNAMIC_TARGETS['calories']} kcal | {DYNAMIC_TARGETS['protein']}g Protein\n💧 {target_water/1000:.1f} Liter Wasser")


# TABS FÜR ANSICHTEN ERSTELLEN

tab1, tab2 = st.tabs(["📅 Heutiger Tag", "📈 Historie & Fortschritt"])


# TAB 1: HEUTIGER TAG

with tab1:
    if "mahlzeiten" not in st.session_state:
        st.session_state.mahlzeiten = []
    if "wasser_ml" not in st.session_state:
        st.session_state.wasser_ml = 0

    col1, col2 = st.columns(2)
    with col1:
        today_date = st.date_input("📅 Datum", datetime.date.today())
    with col2:
        workout_time = st.text_input(" Heutiges Training (Dauer/Art)", placeholder="z.B. 60 Min Krafttraining oder 'Kein Training'")

    st.divider()

    st.write("### 💧 Wasser-Tracker")
    w_col1, w_col2, w_col3, w_col4 = st.columns(4)
    with w_col1:
        if st.button("+ 250 ml "): st.session_state.wasser_ml += 250
    with w_col2:
        if st.button("+ 500 ml "): st.session_state.wasser_ml += 500
    with w_col3:
        if st.button("+ 1000 ml "): st.session_state.wasser_ml += 1000
    with w_col4:
        if st.button("Reset "): st.session_state.wasser_ml = 0

    st.progress(min(st.session_state.wasser_ml / target_water, 1.0))
    st.write(f"**Getrunken:** {st.session_state.wasser_ml} ml / {target_water} ml")
    st.divider()

    st.write("###  Mahlzeiten eintragen")
    neue_mahlzeit = st.text_input("Text eingeben", placeholder="z.B. 2 Eier und 100g Reis")
    if st.button("Text-Mahlzeit speichern 💾"):
        if neue_mahlzeit.strip():
            st.session_state.mahlzeiten.append(neue_mahlzeit)
            st.success(f"Mahlzeit gespeichert!")

    st.write("**Oder Foto hochladen:**")
    uploaded_file = st.file_uploader("Bild auswählen", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None and st.button("Bild analysieren 📸"):
        with st.spinner(" KI analysiert dein Bild..."):
            try:
                img = Image.open(uploaded_file)
                client = get_gemini_client()
                response_vision = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=[img, "Kurze Antwort auf Deutsch: Was für ein Essen/Supplement ist das und wie viel? (z.B. 1 Banane)"]
                )
                st.session_state.mahlzeiten.append(response_vision.text.strip())
                st.success(f" Erkannt: {response_vision.text.strip()}")
            except Exception:
                st.error("Die KI-Anfrage ist fehlgeschlagen. Prüfe den API-Schlüssel, das Modell und die Verbindung.")

    if st.session_state.mahlzeiten:
        st.write("---")
        for m in st.session_state.mahlzeiten:
            st.write(f"- {m}")
        if st.button("Liste löschen "):
            st.session_state.mahlzeiten = []
            st.rerun()
    st.divider()

    if st.button("Tagesanalyse starten "):
        if not st.session_state.mahlzeiten and st.session_state.wasser_ml == 0:
            st.warning("⚠️ Bitte speichere zuerst Daten.")
        else:
            with st.spinner(" Bericht wird erstellt..."):
                try:
                    client = get_gemini_client()
                    gesamte_ernaehrung = "\n".join(st.session_state.mahlzeiten) if st.session_state.mahlzeiten else "Keine"
                    
                    sys_inst = f"""Du bist NutriAgent. Schätze Nährwerte vorsichtig und kennzeichne Unsicherheit. Unbekannte Lebensmittel dürfen keine erfundenen exakten Werte erhalten.
                    BENUTZER: {weight}kg, Ziel: {goal}, Training: {workout_time}.
                    ANTWORTE NUR ALS JSON: {{"tagesbericht": "...", "ist_werte": {{"protein": 20, "carbs": 10, "fat": 5, "sugar": 2}}}}"""
                    
                    chat = client.chats.create(model=GEMINI_MODEL, config=types.GenerateContentConfig(system_instruction=sys_inst, tools=[get_food_nutrition], temperature=0.2, response_mime_type="application/json"))
                    response = chat.send_message(f"Essen:\n{gesamte_ernaehrung}\nWasser: {st.session_state.wasser_ml} ml")
                    daten = json.loads(response.text)
                    
                    st.subheader("📝 Tagesbericht")
                    st.write(daten.get("tagesbericht", ""))
                    
                    ist_werte = daten.get("ist_werte", {})
                    if not isinstance(ist_werte, dict):
                        raise ValueError("Invalid AI nutrition response")
                    ist_werte = {
                        k: float(ist_werte.get(k, 0) or 0)
                        for k in ("protein", "carbs", "fat", "sugar")
                    }
                    chart_data = pd.DataFrame({
                        "Soll": [DYNAMIC_TARGETS["protein"], DYNAMIC_TARGETS["carbs"], DYNAMIC_TARGETS["fat"], DYNAMIC_TARGETS["sugar"]],
                        "Ist": [ist_werte["protein"], ist_werte["carbs"], ist_werte["fat"], ist_werte["sugar"]] 
                    }, index=["Protein (g)", "Kohlenhydrate (g)", "Fett (g)", "Zucker (g)"])
                    st.bar_chart(chart_data)
                    
                    # Speichern in DB MIT Username!
                    conn = sqlite3.connect("nutriagent.db")
                    c = conn.cursor()
                    c.execute('''INSERT OR REPLACE INTO daily_logs (username, date, meals, water_ml, protein_actual)
                                 VALUES (?, ?, ?, ?, ?)''', 
                              (st.session_state.username, str(today_date), gesamte_ernaehrung, st.session_state.wasser_ml, ist_werte["protein"]))
                    conn.commit()
                    conn.close()
                    st.success("💾 Daten für dich gesichert!")
                except Exception:
                    st.error("Die KI-Anfrage ist fehlgeschlagen. Prüfe den API-Schlüssel, das Modell und die Verbindung.")

# TAB 2: HISTORIE

with tab2:
    st.write("###  Dein Fortschritt")
    conn = sqlite3.connect("nutriagent.db")
    # Lade NUR die Daten des eingeloggten Users
    df_history = pd.read_sql_query(
        "SELECT date, meals, water_ml, protein_actual FROM daily_logs WHERE username = ? ORDER BY date ASC",
        conn,
        params=(st.session_state.username,),
    )
    conn.close()
    
    if df_history.empty:
        st.info("Noch keine Daten für dich vorhanden.")
    else:
        st.dataframe(df_history, use_container_width=True)
        df_history.set_index("date", inplace=True)
        st.write("**Protein & Wasser Verlauf**")
        st.line_chart(df_history["protein_actual"], color="#ff4b4b") 
        st.bar_chart(df_history["water_ml"], color="#2196f3")
