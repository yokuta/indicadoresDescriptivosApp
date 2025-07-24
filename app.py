import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox

# -------------------- LOAD DATASETS --------------------
try:
    df = pd.read_parquet("structured_population.parquet")
    df.columns = df.columns.astype(str)
    df_censo = pd.read_parquet("structured_censo.parquet")
except Exception as e:
    messagebox.showerror("Error", f"No se pudieron cargar los archivos Parquet:\n{e}")
    exit()

YEARS = ["2024", "2023", "2022", "2021"]
age_65_plus = ["65_69", "70_74", "75_79", "80_84", "85_89", "90_94", "95_99", "100"]
age_85_plus = ["85_89", "90_94", "95_99", "100"]
ages_0_14 = ["0_4", "5_9", "10_14"]
ages_15_64 = ["15_19", "20_24", "25_29", "30_34", "35_39", "40_44", "45_49", "50_54", "55_59", "60_64"]

# -------------------- AUTOCOMPLETE ENTRY WIDGET --------------------
class AutocompleteEntry(tk.Entry):
    def __init__(self, suggestion_list, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.suggestion_list = sorted(suggestion_list, key=str.lower)
        self.listbox = None
        self.bind("<KeyRelease>", self.check_key)
        self.bind("<Down>", self.move_down)
        self.bind("<Up>", self.move_up)
        self.bind("<Return>", self.select_from_listbox)
        self.bind("<FocusOut>", lambda e: self.after(100, self.hide_listbox))
        self.cur_index = -1

    def check_key(self, event):
        if event.keysym in ("Up", "Down", "Return"):
            return  # handled elsewhere

        value = self.get().lower()
        if value == '':
            self.hide_listbox()
            return

        matches = [item for item in self.suggestion_list if value in item.lower()]
        if matches:
            self.show_listbox(matches)
        else:
            self.hide_listbox()

    def show_listbox(self, matches):
        if self.listbox:
            self.listbox.destroy()

        self.listbox = tk.Listbox(self.master, height=min(10, len(matches)))
        self.listbox.place(x=self.winfo_x(), y=self.winfo_y() + self.winfo_height(), width=self.winfo_width())
        for match in matches:
            self.listbox.insert(tk.END, match)

        self.listbox.bind("<<ListboxSelect>>", self.on_click_select)
        self.cur_index = -1

    def hide_listbox(self):
        if self.listbox:
            self.listbox.destroy()
            self.listbox = None

    def on_click_select(self, event):
        self.select_from_listbox()

    def move_down(self, event=None):
        if not self.listbox:
            return
        self.cur_index = (self.cur_index + 1) % self.listbox.size()
        self.listbox.select_clear(0, tk.END)
        self.listbox.select_set(self.cur_index)
        self.listbox.activate(self.cur_index)

    def move_up(self, event=None):
        if not self.listbox:
            return
        self.cur_index = (self.cur_index - 1) % self.listbox.size()
        self.listbox.select_clear(0, tk.END)
        self.listbox.select_set(self.cur_index)
        self.listbox.activate(self.cur_index)

    def select_from_listbox(self, event=None):
        if not self.listbox:
            return
        try:
            index = self.listbox.curselection()[0]
            selected = self.listbox.get(index)
            self.delete(0, tk.END)
            self.insert(0, selected)
        except IndexError:
            pass
        self.hide_listbox()


# -------------------- GUI SETUP --------------------
root = tk.Tk()
root.title("📊 Indicadores INE por Municipio")
root.geometry("1000x500")

label = tk.Label(root, text="Selecciona un municipio:", font=("Arial", 12))
label.pack(pady=5)

# Municipality list
municipalities = sorted(df["municipio"].dropna().unique(), key=str.lower)
selected_muni = tk.StringVar()
entry = AutocompleteEntry(municipalities, root, textvariable=selected_muni, font=("Arial", 11), width=50)
entry.pack(pady=5)

# -------------------- Tree and Button --------------------
tree = ttk.Treeview(root, show="headings")
tree.pack(expand=True, fill="both", padx=10, pady=10)

def calculate_indicators():
    for i in tree.get_children():
        tree.delete(i)

    muni = selected_muni.get()
    pop_df = df[df["municipio"] == muni]
    if pop_df.empty:
        messagebox.showerror("Error", "No se encontraron datos para el municipio seleccionado.")
        return

    muni_code = muni.split()[0]
    censo_df = df_censo[df_censo["Municipio de residencia"].str.startswith(muni_code)]

    results = []

    for year in YEARS:
        total = pop_df.get(f"total_total_total_{year}", pd.Series([0])).values[0]
        over_65 = pop_df[[f"total_{age}_total_{year}" for age in age_65_plus if f"total_{age}_total_{year}" in pop_df.columns]].sum(axis=1).values[0]
        over_85 = pop_df[[f"total_{age}_total_{year}" for age in age_85_plus if f"total_{age}_total_{year}" in pop_df.columns]].sum(axis=1).values[0]
        foreign = pop_df.get(f"total_total_EX_{year}", pd.Series([0])).values[0]
        pop_0_14 = pop_df[[f"total_{age}_total_{year}" for age in ages_0_14 if f"total_{age}_total_{year}" in pop_df.columns]].sum(axis=1).values[0]
        pop_15_64 = pop_df[[f"total_{age}_total_{year}" for age in ages_15_64 if f"total_{age}_total_{year}" in pop_df.columns]].sum(axis=1).values[0]

        row = {
            "Año": year,
            "D.22.a. Envejecimiento (%)": round(over_65 / total * 100, 2) if total else "",
            "D.22.b. Senectud (%)": round(over_85 / over_65 * 100, 2) if over_65 else "",
            "Población extranjera (%)": round(foreign / total * 100, 2) if total else "",
            "D.24.a. Dependencia total (%)": round((pop_0_14 + over_65) / pop_15_64 * 100, 2) if pop_15_64 else "",
            "D.24.b. Dependencia infantil (%)": round(pop_0_14 / pop_15_64 * 100, 2) if pop_15_64 else "",
            "D.24.c. Dependencia mayores (%)": round(over_65 / pop_15_64 * 100, 2) if pop_15_64 else "",
            "%Vivienda secundaria": "",
            "D.25 Viviendas por persona": ""
        }

        if year == "2021":
            try:
                v_total = censo_df["viviendasT"].values[0]
                v_nop = censo_df["viviendasNoP"].values[0]
                pop_2021 = pop_df["total_total_total_2021"].values[0]
                row["%Vivienda secundaria"] = round((v_nop / v_total) * 100, 2)
                row["D.25 Viviendas por persona"] = round((v_total / pop_2021) * 1000, 4)
            except:
                pass

        results.append(row)

    # Setup table columns
    columns = list(results[0].keys())
    tree.config(columns=columns)
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, anchor="center", width=130)

    # Fill rows
    for row in results:
        tree.insert("", "end", values=list(row.values()))

# Button
btn = tk.Button(root, text="Calcular indicadores", command=calculate_indicators, font=("Arial", 11))
btn.pack(pady=5)

root.mainloop()
