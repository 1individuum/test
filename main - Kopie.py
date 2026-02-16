import flet as ft
import pandas as pd
import requests
import io
import traceback

# --- KONFIGURATION ---
FILE_ID = "1SMcO_oBYCnD8-659YDW02wwBv83ikGja"
URL = f"https://docs.google.com/uc?export=download&id={FILE_ID}"

def main(page: ft.Page):
    page.title = "IBKR Portfolio Dashboard"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.scroll = ft.ScrollMode.ADAPTIVE

    # UI-Elemente
    exposure_text = ft.Text("$ 0.00", size=32, weight=ft.FontWeight.BOLD, color="#4CAF50")
    count_text = ft.Text("0 Positionen", size=18, color="#AAAAAA", weight=ft.FontWeight.W_500)
    list_view = ft.Column(spacing=10)

    def load_data(e=None):
        exposure_text.value = "Lade..."
        page.update()
        
        headers = {"User-Agent": "Mozilla/5.0"}
        
        try:
            response = requests.get(URL, headers=headers, timeout=15)
            if response.status_code == 200:
                df = pd.read_csv(io.StringIO(response.text))
                
                # Datentypen korrigieren
                df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce')
                df['Strike'] = pd.to_numeric(df['Strike'], errors='coerce')
                
                # Filter für Short Puts
                puts = df[(df['Put/Call'] == 'P') & (df['Quantity'] < 0)].copy()
                
                # BERECHNUNGEN
                exposure = (puts['Strike'] * 100 * puts['Quantity'].abs()).sum()
                anzahl = len(puts)
                
                # UI UPDATES
                exposure_text.value = f"$ {exposure:,.2f}"
                count_text.value = f"{anzahl} offene Positionen"
                
                list_view.controls.clear()
                for _, row in puts.iterrows():
                    list_view.controls.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Text(f"{row['Symbol']}", weight="bold", size=16),
                                ft.Text(f"STK: {row['Strike']}"),
                                ft.Text(f"Qty: {int(row['Quantity'])}", color="#FF5252"),
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            padding=15, 
                            bgcolor="#222222",
                            border_radius=10,
                            border=ft.border.all(1, "#444444")
                        )
                    )
            else:
                exposure_text.value = "Fehler"
                count_text.value = f"Status: {response.status_code}"
        except Exception:
            exposure_text.value = "Fehler"
            print(traceback.format_exc())
            
        page.update()

    refresh_button = ft.Button(
        content=ft.Row(
            [ft.Icon("refresh"), ft.Text("Aktualisieren")],
            alignment=ft.MainAxisAlignment.CENTER,
            tight=True
        ),
        on_click=load_data,
        height=50,
        width=250
    )

    page.add(
        ft.Text("IBKR Put-Analyzer", size=28, weight=ft.FontWeight.W_800),
        ft.Divider(height=20, color="transparent"),
        ft.Row([refresh_button], alignment=ft.MainAxisAlignment.CENTER),
        ft.Divider(height=30),
        ft.Text("Gesamtrisiko (Short Puts):", size=14, color="#AAAAAA"),
        exposure_text,
        count_text, # Die neue Summenanzeige
        ft.Divider(height=20),
        ft.Text("Positionen im Detail:", size=16, weight="bold"),
        list_view
    )
    
    load_data()

if __name__ == "__main__":
    ft.run(main)