#!/usr/bin/env python3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import numpy as np
from tkcalendar import DateEntry
from matplotlib.backends.backend_pdf import PdfPages
import datetime
import mplcursors
import seaborn as sns
import os

# Nordic and Light themes
THEMES = {
    "Nordic": {
        "bg": '#2E3440', "axes": '#3B4252', "text": '#D8DEE9',
        "bar": '#A3BE8C', "scatter": '#A3BE8C',
        "line_current": '#EBCB8B', "line_target": '#B48EAD'
    },
    "Light": {
        "bg": 'white', "axes": '#f0f0f0', "text": 'black',
        "bar": '#76c893', "scatter": '#76c893',
        "line_current": '#f9c74f', "line_target": '#f9844a'
    }
}

class TradeAnalyzerApp(tk.Tk):
    def __init__(self, profit_target=400, threshold=0.25):
        super().__init__()
        self.theme_name = "Nordic"
        self.apply_theme()

        self.title("Trade Duration Profit Analyzer")
        self.geometry("1200x800")
        self.profit_target = profit_target
        self.threshold = threshold
        self.df = None

        ctrl_frame = tk.Frame(self, bg=self.colors['bg'])
        ctrl_frame.pack(fill=tk.X, pady=5)

        load_btn = tk.Button(ctrl_frame, text="Load CSV", command=self.load_file,
                             bg=self.colors['bar'], fg=self.colors['bg'])
        load_btn.pack(side=tk.LEFT, padx=5)

        export_chart_btn = tk.Button(ctrl_frame, text="Export Chart (PNG/PDF)", command=self.export_chart,
                                     bg=self.colors['bar'], fg=self.colors['bg'])
        export_chart_btn.pack(side=tk.LEFT, padx=5)

        export_data_btn = tk.Button(ctrl_frame, text="Export Data (CSV/Excel)", command=self.export_data,
                                    bg=self.colors['bar'], fg=self.colors['bg'])
        export_data_btn.pack(side=tk.LEFT, padx=5)

        self.theme_btn = tk.Button(ctrl_frame, text="Toggle Theme", command=self.toggle_theme,
                                   bg=self.colors['bar'], fg=self.colors['bg'])
        self.theme_btn.pack(side=tk.LEFT, padx=5)

        tk.Label(ctrl_frame, text="Filter Symbol:", bg=self.colors['bg'], fg=self.colors['text']).pack(side=tk.LEFT, padx=(10,0))
        self.symbol_var = tk.StringVar()
        self.symbol_cb = ttk.Combobox(ctrl_frame, textvariable=self.symbol_var, state="disabled")
        self.symbol_cb.pack(side=tk.LEFT, padx=5)
        apply_btn = tk.Button(ctrl_frame, text="Apply Filter", command=self.apply_filter,
                              bg=self.colors['bar'], fg=self.colors['bg'], state=tk.DISABLED)
        apply_btn.pack(side=tk.LEFT, padx=5)
        self.apply_btn = apply_btn

        tk.Label(ctrl_frame, text="Target:", bg=self.colors['bg'], fg=self.colors['text']).pack(side=tk.LEFT, padx=(10,0))
        self.target_scale = tk.Scale(ctrl_frame, from_=0, to=1000, orient=tk.HORIZONTAL, length=150,
                                     bg=self.colors['bg'], fg=self.colors['text'], highlightbackground=self.colors['bg'], command=self.update_target)
        self.target_scale.set(self.profit_target)
        self.target_scale.pack(side=tk.LEFT, padx=5)

        self.stats_label = tk.Label(self, text="No data loaded.", bg=self.colors['bg'],
                                    fg=self.colors['text'], justify=tk.LEFT, anchor="w")
        self.stats_label.pack(fill=tk.X, padx=10)

        self.canvas_frame = tk.Frame(self, bg=self.colors['bg'])
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.table_frame = tk.Frame(self, bg=self.colors['bg'])
        self.table_frame.pack(fill=tk.X)

    def apply_theme(self):
        self.colors = THEMES[self.theme_name]
        mpl.rcParams.update({
            'figure.facecolor': self.colors['bg'],
            'axes.facecolor': self.colors['axes'],
            'savefig.facecolor': self.colors['bg'],
            'text.color': self.colors['text'],
            'axes.labelcolor': self.colors['text'],
            'xtick.color': self.colors['text'],
            'ytick.color': self.colors['text']
        })

    def toggle_theme(self):
        self.theme_name = "Light" if self.theme_name == "Nordic" else "Nordic"
        self.apply_theme()
        if self.df is not None:
            self.update_stats_and_plots(self.df)

    def update_target(self, val):
        self.profit_target = int(val)
        if self.df is not None:
            self.update_stats_and_plots(self.df)

    def load_file(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        try:
            df = pd.read_csv(path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {e}")
            return

        df['Open time'] = pd.to_datetime(df['Open time'], errors='coerce')
        df['Close time'] = pd.to_datetime(df['Close time'], errors='coerce')
        df.dropna(subset=['Open time', 'Close time'], inplace=True)
        df['Duration'] = (df['Close time'] - df['Open time']).dt.total_seconds()
        df['Hour'] = df['Open time'].dt.hour
        df['Category'] = df['Duration'].apply(lambda x: 'Quick (≤ 2 min)' if x <= 120 else 'Long (> 2 min)')
        self.df = df

        symbols = ['All'] + sorted(df['Symbol'].unique().tolist())
        self.symbol_cb.config(values=symbols, state="readonly")
        self.symbol_cb.set('All')
        self.apply_btn.config(state=tk.NORMAL)

        self.update_stats_and_plots(df)

    def apply_filter(self):
        if self.df is None:
            return
        sel = self.symbol_var.get()
        if sel and sel != 'All':
            filtered = self.df[self.df['Symbol'] == sel]
        else:
            filtered = self.df
        self.update_stats_and_plots(filtered)

    def update_stats_and_plots(self, df):
        total_profit = df['Profit'].sum()
        quick_profit = df[df['Category'] == 'Quick (≤ 2 min)']['Profit'].sum()
        pct_quick_current = (quick_profit / total_profit * 100) if total_profit else 0
        pct_quick_target = (quick_profit / self.profit_target * 100) if self.profit_target else 0
        avg_duration = df['Duration'].mean() / 60

        stats = (
            f"Total profit: {total_profit:.2f}\n"
            f"Quick profit (≤2 min): {quick_profit:.2f} ({pct_quick_current:.1f}% curr, {pct_quick_target:.1f}% targ)\n"
            f"Avg trade duration: {avg_duration:.2f} min\n"
        )
        stats += "⚠️ Exceeds 25% threshold!" if pct_quick_current > self.threshold*100 else "✅ Within 25% threshold."
        self.stats_label.config(text=stats)

        for widget in self.canvas_frame.winfo_children(): widget.destroy()
        for widget in self.table_frame.winfo_children(): widget.destroy()

        summary = df.groupby('Category')['Profit'].sum().reset_index()
        fig, axes = plt.subplots(1, 3, figsize=(15, 4), facecolor=self.colors['bg'])

        axes[0].bar(summary['Category'], summary['Profit'], color=self.colors['bar'])
        axes[0].axhline(total_profit * self.threshold, color=self.colors['line_current'], linestyle='--', label="25% of current")
        axes[0].axhline(self.profit_target * self.threshold, color=self.colors['line_target'], linestyle=':', label="25% of target")
        axes[0].set_title('Profit by Duration')
        axes[0].legend()

        scatter = axes[1].scatter(df['Duration']/60, df['Profit'], color=self.colors['scatter'], edgecolors='w')
        axes[1].axhline(0, color=self.colors['text'], linewidth=0.5)
        axes[1].set_title('Profit vs Duration')
        mplcursors.cursor(scatter, hover=True).connect("add", lambda sel: sel.annotation.set_text(
            f"Profit: {df.iloc[sel.index]['Profit']}\nDuration: {df.iloc[sel.index]['Duration']/60:.2f} min\nSymbol: {df.iloc[sel.index]['Symbol']}\nSide: {df.iloc[sel.index]['Side']}\nTime: {df.iloc[sel.index]['Open time']}"
        ))

        heat_data = df.groupby('Hour')['Profit'].sum().reindex(range(24), fill_value=0)
        sns.heatmap(pd.DataFrame(heat_data).T, ax=axes[2], cmap='YlGnBu', cbar=True)
        axes[2].set_title('Profit by Hour of Day')

        self.current_fig = fig  # Save for export

        canvas = FigureCanvasTkAgg(fig, master=self.canvas_frame)
        toolbar = NavigationToolbar2Tk(canvas, self.canvas_frame)
        toolbar.update()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        canvas.draw()

        tree = ttk.Treeview(self.table_frame, columns=list(df.columns), show='headings')
        for col in df.columns:
            tree.heading(col, text=col)
            tree.column(col, width=100, anchor='center')
        for _, row in df.iterrows():
            tree.insert('', tk.END, values=list(row))

        vsb = ttk.Scrollbar(self.table_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y')
        tree.pack(fill=tk.X, expand=True)

    def export_chart(self):
        if not hasattr(self, 'current_fig'):
            messagebox.showerror("No chart", "Please load data first.")
            return
        filetypes = [('PNG Image', '*.png'), ('PDF File', '*.pdf')]
        path = filedialog.asksaveasfilename(defaultextension='.png', filetypes=filetypes)
        if path:
            self.current_fig.savefig(path)
            messagebox.showinfo("Saved", f"Chart saved to {path}")

    def export_data(self):
        if self.df is None:
            messagebox.showerror("No data", "Please load data first.")
            return
        filetypes = [('CSV File', '*.csv'), ('Excel File', '*.xlsx')]
        path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=filetypes)
        if path.endswith('.xlsx'):
            self.df.to_excel(path, index=False)
        else:
            self.df.to_csv(path, index=False)
        messagebox.showinfo("Saved", f"Data exported to {path}")

if __name__ == "__main__":
    app = TradeAnalyzerApp()
    app.mainloop()
