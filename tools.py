# tools.py - Nährwert-Datenbank Tool für Gemini Agent

def get_food_nutrition(food_name: str, quantity_g: float) -> dict:
    """
    Sucht Nährwertangaben für ein bestimmtes Lebensmittel und Gewicht in Gramm.
    
    Args:
        food_name: Name des Lebensmittels (z. B. 'Hähnchenbrust', 'Ei', 'Getrocknete Feige').
        quantity_g: Die verzehrte Menge in Gramm.
    """
    # Referenz-Datenbank (Nährwerte pro 100g)
    nutrition_db = {
        "hähnchenbrust": {"protein": 31.0, "carbs": 0.0, "fat": 3.6, "fiber": 0.0, "sugar": 0.0, "calories": 165},
        "ei": {"protein": 13.0, "carbs": 1.1, "fat": 11.0, "fiber": 0.0, "sugar": 1.1, "calories": 155},
        "eier": {"protein": 13.0, "carbs": 1.1, "fat": 11.0, "fiber": 0.0, "sugar": 1.1, "calories": 155},
        "getrocknete feige": {"protein": 3.3, "carbs": 64.0, "fat": 0.9, "fiber": 9.8, "sugar": 48.0, "calories": 249},
        "getrocknete feigen": {"protein": 3.3, "carbs": 64.0, "fat": 0.9, "fiber": 9.8, "sugar": 48.0, "calories": 249},
        "walnuss": {"protein": 15.0, "carbs": 14.0, "fat": 65.0, "fiber": 6.7, "sugar": 2.6, "calories": 654},
        "walnüsse": {"protein": 15.0, "carbs": 14.0, "fat": 65.0, "fiber": 6.7, "sugar": 2.6, "calories": 654},
        "joghurt": {"protein": 10.0, "carbs": 3.6, "fat": 0.4, "fiber": 0.0, "sugar": 3.2, "calories": 59},
        "gainer": {"protein": 25.0, "carbs": 65.0, "fat": 3.0, "fiber": 2.0, "sugar": 10.0, "calories": 380},
        "haferflocken": {"protein": 13.5, "carbs": 58.7, "fat": 7.0, "fiber": 10.0, "sugar": 1.0, "calories": 372}
    }

    food_key = food_name.lower().strip()
    if quantity_g <= 0:
        return {"food": food_name, "error": "Menge muss positiv sein."}
    data = nutrition_db.get(food_key)
    if data is None:
        return {"food": food_name, "weight_g": quantity_g,
                "error": "Keine Referenzdaten vorhanden; bitte keine Nährwerte erfinden."}

    factor = quantity_g / 100.0
    return {
        "food": food_name,
        "weight_g": quantity_g,
        "protein": round(data["protein"] * factor, 1),
        "carbs": round(data["carbs"] * factor, 1),
        "fat": round(data["fat"] * factor, 1),
        "fiber": round(data["fiber"] * factor, 1),
        "sugar": round(data["sugar"] * factor, 1),
        "calories": round(data["calories"] * factor, 1)
    }