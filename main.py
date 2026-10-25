# main.py - Hauptprogramm und Agenten-Logik

import os
import json
from google import genai
from google.genai import types
from config import USER_PROFILE, TARGETS
from tools import get_food_nutrition
from visualization import generate_nutrition_chart

SYSTEM_INSTRUCTION = f"""
Du bist "NutriAgent", ein hochspezialisierter KI-Ernährungs- und Fitnessberater.
Deine Aufgabe ist es, die tägliche Nahrungs- und Medikamentenaufnahme des Benutzers zu analysieren und einen detaillierten Bericht auf DEUTSCH zu erstellen.

Benutzerprofil:
{json.dumps(USER_PROFILE, ensure_ascii=False, indent=2)}

Soll-Ziele (Targets):
{json.dumps(TARGETS, ensure_ascii=False, indent=2)}

Richtlinien für deine Antwort:
1. Verwende das Tool `get_food_nutrition`, um genaue Nährwerte für alle genannten Lebensmittel zu berechnen.
2. Berücksichtige Nahrungsergänzungsmittel nur, wenn sie in den Eingabedaten erwähnt werden.
3. Überprüfe nur ausdrücklich im Beispielprofil angegebene Einschränkungen.
4. Schätze Soll- und Ist-Werte und markiere unbekannte Nährwerte als unsicher. Erfinde keine exakten Daten.
5. Gib alltagsnahe allgemeine Hinweise für den nächsten Tag.
6. Antworte ausschließlich auf DEUTSCH in einem professionellen und motivierenden Ton.
"""

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Fehler: Bitte setze die Umgebungsvariable GEMINI_API_KEY.")
        return

    client = genai.Client(api_key=api_key)

    # Fictional CLI demo; this sample is not read from the web UI or its SQLite database.
    user_log = """
    Beispieltag:
    - Frühstück: 60 g Haferflocken und 1 Apfel.
    - Mittagessen: 150 g Reis und 150 g Hähnchenbrust.
    - Getränke: 2 Liter Wasser.
    """

    print("🤖 NutriAgent analysiert die Daten auf Deutsch...\n")

    # Verwende das vom System geforderte Modell gemini-3.8-flash
    chat = client.chats.create(
        model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=[get_food_nutrition],
            temperature=0.2
        )
    )

    response = chat.send_message(f"Tagesbericht des Benutzers:\n{user_log}")

    print("================ 📝 TAGESBERICHT & ANALYSE ================\n")
    print(response.text)

    # DEMO ONLY: fixed, illustrative values, NOT calculated from the AI response.
    # Ist-Werte für das Diagramm
    actual_intake = {
        "calories": 1820,
        "protein": 132.0,
        "carbs": 155.0,
        "fat": 40.0,
        "fiber": 11.5,
        "sugar": 21.0
    }

    generate_nutrition_chart(TARGETS, actual_intake)

if __name__ == "__main__":
    main()