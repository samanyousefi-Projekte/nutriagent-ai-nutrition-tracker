# visualization.py - Erstellung von Vergleichsdiagrammen

import matplotlib.pyplot as plt
import numpy as np

def generate_nutrition_chart(targets: dict, actuals: dict, filename: str = "tagesbericht.png"):
    """
    Erstellt ein Balkendiagramm zum Vergleich von Ziel- und Ist-Nährwertaufnahme.
    """
    labels = ['Protein (g)', 'Kohlenhydrate (g)', 'Fett (g)', 'Ballaststoffe (g)', 'Zucker (g)']
    
    target_values = [targets['protein'], targets['carbs'], targets['fat'], targets['fiber'], targets['sugar']]
    actual_values = [actuals['protein'], actuals['carbs'], actuals['fat'], actuals['fiber'], actuals['sugar']]

    x = np.arange(len(labels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(11, 6))
    
    rects1 = ax.bar(x - width/2, target_values, width, label='Soll-Wert (Target)', color='#1f77b4')
    rects2 = ax.bar(x + width/2, actual_values, width, label='Ist-Wert (Actual)', color='#2ca02c')

    ax.set_ylabel('Menge in Gramm (g)')
    ax.set_title('Täglicher Nährwertvergleich: Soll vs. Ist', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15)
    ax.legend()
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    ax.bar_label(rects1, padding=3)
    ax.bar_label(rects2, padding=3)

    fig.tight_layout()
    plt.savefig(filename, dpi=300)
    print(f"\n📊 Diagramm gespeichert unter: {filename}")