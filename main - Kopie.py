import flet as ft
import pandas as pd
import requests
import io
import traceback
from datetime import datetime

# --- KONFIGURATION ---
FILE_ID = "1SMcO_oBYCnD8-659YDW02wwBv83ikGja"
URL = f"https://docs.google.com/uc?export=download&id={FILE_ID}"

def main(page: ft.Page):
    page.title = "IBKR Portfolio Dashboard"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = ft.Padding(20, 60, 20, 20) 
    page.scroll = ft.ScrollMode.ADAPTIVE

    # UI-Elemente
    exposure_text = ft.Text("$ 0.00", size=32, weight=ft.FontWeight.BOLD, color="#4CAF50")
    # Kombinierte Zeile für Aktien Netto und Cash
    net_info_row = ft.Row([
        ft.Text("Aktien: $ 0.00", size=16, weight=ft.FontWeight.W_500, color="#2196F3"),
        ft.Text("Cash (EUR): 0.00 €", size=16, weight=ft.FontWeight.W_500, color="#FFB74D")
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    
    details_text = ft.Text("Lade Daten...", size=14, color="#AAAAAA")
    progress_bar = ft.ProgressBar(width=400, color="#4CAF50", bgcolor="#FF5252", height=10, value=0)
    ratio_text = ft.Text("", size=12, color="#888888")
    list_view = ft.Column(spacing=12)

    def format_date_info(expiry_val):
        if pd.isna(expiry_val) or str(expiry_val).strip() == "" or str(expiry_val).lower() == "nan" or str(expiry_val) == "0":
            return None, None
        try:
            expiry_clean = str(int(float(expiry_val))).strip()
            date_obj = datetime.strptime(expiry_clean, '%Y%m%d')
            formatted_date = date_obj.strftime('%d.%m.%Y')
            days_left = (date_obj - datetime.now()).days
            return formatted_date, f"{days_left}d"
        except:
            return None, None

    def load_data(e=None):
        exposure_text.value = "Lade..."
        page.update()
        
        try:
            response = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            df = pd.read_csv(io.StringIO(response.text))
            df.columns = [c.strip() for c in df.columns]
            
            def get_col(name):
                for c in df.columns:
                    if c.lower() == name.lower(): return c
                return None

            col_qty = get_col('Quantity')
            col_strike = get_col('Strike')
            col_last = get_col('MarkPrice') or get_col('Last') 
            col_pc = get_col('Put/Call')
            col_exp = get_col('Expiry')
            col_sym = get_col('Symbol')

            if not col_qty or not col_sym:
                exposure_text.value = "Daten-Fehler"
                page.update()
                return

            df[col_qty] = pd.to_numeric(df[col_qty], errors='coerce').fillna(0)
            df[col_strike] = pd.to_numeric(df[col_strike], errors='coerce').fillna(0)
            df[col_last] = pd.to_numeric(df[col_last], errors='coerce').fillna(0)
            
            pc_series = df[col_pc].astype(str).str.strip().str.upper() if col_pc else pd.Series([""] * len(df))
            sym_series = df[col_sym].astype(str).str.upper()

            # --- CASH BESTAND BERECHNEN ---
            # Wir suchen explizit nach EUR.USD um den Cash-Bestand in EUR zu zeigen
            cash_row = df[sym_series.str.contains("EUR.USD", na=False)]
            cash_val = cash_row[col_qty].sum() if not cash_row.empty else 0.0

            # --- FILTERUNG FÜR RISIKO ---
            is_cash = sym_series.str.contains(r"\.USD|\.EUR|\.JPY|\.GBP", na=False)
            
            # 1. SHORT PUTS
            puts = df[(pc_series == 'P') & (df[col_qty] < 0) & (~is_cash)].copy()
            put_exposure = (puts[col_strike] * 100 * puts[col_qty].abs()).sum()
            
            # 2. AKTIEN
            stocks = df[(~pc_series.isin(['P', 'C'])) & (df[col_qty] > 0) & (~is_cash)].copy()
            stock_exposure = (stocks[col_qty] * stocks[col_last]).sum()
            
            total_exposure = put_exposure + stock_exposure
            
            # UI UPDATES
            exposure_text.value = f"$ {total_exposure:,.2f}"
            net_info_row.controls[0].value = f"Aktien: $ {stock_exposure:,.2f}"
            net_info_row.controls[1].value = f"Cash: {cash_val:,.2f} €"
            
            details_text.value = f"Puts: $ {put_exposure:,.0f}  |  Aktien: $ {stock_exposure:,.0f}"
            
            if total_exposure > 0:
                progress_bar.value = stock_exposure / total_exposure
                ratio_text.value = f"Verteilung: {(put_exposure/total_exposure)*100:.1f}% Puts / {(stock_exposure/total_exposure)*100:.1f}% Aktien"
            
            list_view.controls.clear()
            
            if not puts.empty:
                list_view.controls.append(ft.Text("Optionen (Short Puts):", size=16, weight="bold"))
                for _, row in puts.sort_values(by=col_exp if col_exp else col_sym).iterrows():
                    date_p, days_l = format_date_info(row[col_exp])
                    list_view.controls.append(create_card(row[col_sym], f"STK: {row[col_strike]}", days_l, f"Exp: {date_p}", int(row[col_qty]), abs(row[col_strike] * 100 * row[col_qty])))

            if not stocks.empty:
                list_view.controls.append(ft.Divider(height=10, color="transparent"))
                list_view.controls.append(ft.Text("Aktien-Positionen:", size=16, weight="bold"))
                for _, row in stocks.iterrows():
                    list_view.controls.append(create_card(row[col_sym], f"Kurs: {row[col_last]}", None, "Aktie", int(row[col_qty]), (row[col_qty] * row[col_last])))
            
        except Exception as ex:
            exposure_text.value = "Daten-Fehler"
            print(traceback.format_exc())
            
        page.update()

    def create_card(symbol, sub_val, top_right, sub_right, qty, risk):
        return ft.Container(
            content=ft.Column([
                ft.Row([ft.Text(symbol, weight="bold", size=18), ft.Text(top_right or "", color="#FFB74D", weight="bold")], alignment="spaceBetween"),
                ft.Row([ft.Text(sub_val, size=14, color="#AAAAAA"), ft.Text(sub_right or "", color="#AAAAAA", size=14)], alignment="spaceBetween"),
                ft.Row([ft.Text(f"Qty: {qty}", color="#4CAF50" if qty > 0 else "#FF5252", weight="bold"), ft.Text(f"$ {risk:,.0f}", weight="bold")], alignment="spaceBetween"),
            ], spacing=2),
            padding=12, bgcolor="#1E1E1E", border_radius=10, border=ft.border.all(1, "#333333")
        )

    page.add(
        ft.Text("IBKR Portfolio-Analyzer", size=28, weight="bold"),
        ft.Text("Gesamtrisiko (Puts + Aktien):", size=14, color="#AAAAAA"),
        exposure_text,
        ft.Container(content=net_info_row, padding=ft.padding.only(top=5, bottom=5)),
        details_text,
        ft.Container(padding=ft.Padding(0, 10, 0, 5), content=progress_bar),
        ratio_text, 
        ft.Divider(height=30, color="#444444"),
        list_view
    )
    load_data()

if __name__ == "__main__":
    ft.run(main)
