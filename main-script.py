import os
import json
import numpy as np
import tkinter as tk
import matplotlib.pyplot as plt
import matplotlib.colors as mplc
from datetime import datetime, date, timedelta
from tkinter import ttk, messagebox, simpledialog
from matplotlib.patches import Rectangle
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.colors import LinearSegmentedColormap
from collections import defaultdict

# ========== Constants ==========
DATA_FILE = "sleep_data.json"

# ========== Load or Initialize Sleep Data ==========
if not os.path.exists(DATA_FILE) or os.stat(DATA_FILE).st_size == 0:
    sleep_data = {}
    with open(DATA_FILE, "w") as f:
        json.dump(sleep_data, f, indent=2)
else:
    with open(DATA_FILE, "r") as f:
        sleep_data = json.load(f)

today_key = date.today().isoformat()
if today_key not in sleep_data:
    root = tk.Tk()
    root.withdraw()
    try:
        hrs = simpledialog.askfloat(
            "Sleep Entry",
            f"How many hours did you sleep on {today_key}?",
            minvalue=0.0, maxvalue=24.0
        )
        sleep_data[today_key] = hrs
    except Exception as e:
        messagebox.showerror("Error", f"Failed to record sleep: {e}")
    finally:
        with open(DATA_FILE, "w") as f:
            json.dump(sleep_data, f, indent=2)
        root.destroy()

# ========== Helper Functions ==========
def hex_to_rgb(hx):
    hx = hx.lstrip("#")
    return tuple(int(hx[i:i+2], 16) for i in (0, 2, 4))

def get_sleep_color(hours):
    if hours is None:
        return "#DDDDDD"
    color1, color2, color3 = map(hex_to_rgb, ("1cdce8", "bb77ed", "f34a62"))
    h = max(2, min(11, hours))
    t = (h - 2) / 9
    if t < 0.5:
        t2 = t * 2
        c = [(1 - t2) * c1 + t2 * c2 for c1, c2 in zip(color1, color2)]
    else:
        t2 = (t - 0.5) * 2
        c = [(1 - t2) * c2 + t2 * c3 for c2, c3 in zip(color2, color3)]
    return "#{:02X}{:02X}{:02X}".format(*map(int, c))

# ========== Build UI ==========
root = tk.Tk()
root.title("🛌 Sleep Dashboard")
nb = ttk.Notebook(root)
nb.pack(fill="both", expand=True)

# ========== Calendar Tab ==========
cal_fig, cal_ax = plt.subplots(figsize=(8, 6))
cal_ax.axis('off')
today = date.today()
months = list("JFMAMJJASOND")
days = list(range(1, 32))

cal_ax.set_xlim(0, len(months))
cal_ax.set_ylim(0, len(days))
cal_ax.set_aspect('equal')

recorded = [datetime.strptime(d, "%Y-%m-%d").date() for d, v in sleep_data.items() if v is not None]
first_date = min(recorded) if recorded else today
click_patches = []

for i, day in enumerate(days):
    for j in range(len(months)):
        try:
            dt = date(today.year, j + 1, day)
        except ValueError:
            continue

        x, y = j, len(days) - i - 1
        key = dt.isoformat()

        if key in sleep_data and sleep_data[key] is not None:
            fill = get_sleep_color(sleep_data[key])
        elif first_date <= dt < today:
            fill = "#DDDDDD"
        else:
            fill = "white"

        rect = Rectangle((x, y), 1, 1, edgecolor="black", facecolor=fill, linewidth=1.2)
        cal_ax.add_patch(rect)
        click_patches.append((rect, key))

        if key in sleep_data and sleep_data[key] is not None:
            rgb = mplc.hex2color(fill)
            bright = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
            txtc = "white" if bright < 0.5 else "black"
            cal_ax.text(x + 0.5, y + 0.5, f"{sleep_data[key]:.1f}",
                        ha='center', va='center', fontsize=6, color=txtc)

for idx, m in enumerate(months):
    cal_ax.text(idx + 0.5, len(days) + 0.5, m, ha='center', va='bottom', weight='bold')
for idx, d in enumerate(days):
    cal_ax.text(-0.2, len(days) - idx - 0.5, str(d), ha='right', va='center', fontsize=6)

cal_fig.tight_layout()

# ========== Calendar Click Handler ==========
def on_cal_click(event):
    inv = cal_ax.transData.inverted()
    xdata, ydata = inv.transform((event.x, event.y))
    for rect, key in click_patches:
        x0, y0 = rect.get_xy()
        if x0 <= xdata < x0 + 1 and y0 <= ydata < y0 + 1:
            dt = datetime.strptime(key, "%Y-%m-%d").date()
            weekday = dt.strftime("%A")
            hrs = sleep_data.get(key)
            sleep_line = f"You slept {hrs:.1f} hours." if hrs is not None else "No sleep recorded."

            streak = 0
            check_day = dt
            while True:
                h = sleep_data.get(check_day.isoformat())
                if h is None or h < 7:
                    break
                streak += 1
                check_day -= timedelta(days=1)

            streak_line = f"💪 Sleep streak: {streak} day{'s' if streak > 1 else ''} ≥ 7h" if hrs else ""

            best_streak = 0
            sorted_dates = sorted(sleep_data.keys())
            i = 0
            while i < len(sorted_dates):
                cur_streak = 0
                while i < len(sorted_dates):
                    d = datetime.strptime(sorted_dates[i], "%Y-%m-%d").date()
                    h = sleep_data.get(sorted_dates[i])
                    if h is not None and h >= 4:
                        cur_streak += 1
                        i += 1
                    else:
                        break
                best_streak = max(best_streak, cur_streak)
                i += 1

            msg = f"{key} → {weekday}\n\n{sleep_line}\n{streak_line}\n\U0001F3C6 Best streak ever: {best_streak} day{'s' if best_streak != 1 else ''}"
            messagebox.showinfo("Sleep Detail", msg)
            break

cal_fig.canvas.mpl_connect('button_press_event', on_cal_click)

cmap = LinearSegmentedColormap.from_list("grad", ["#1cdce8", "#bb77ed", "#f34a62"], N=256)
cax = cal_fig.add_axes([0.92, 0.1, 0.02, 0.8])
cb = plt.colorbar(plt.cm.ScalarMappable(cmap=cmap), cax=cax)
cb.set_ticks([0, 1]); cb.set_ticklabels(["2h", "11h"]); cb.set_label("Sleep (h)", rotation=90)
cal_fig.tight_layout()

cal_frame = ttk.Frame(nb)
canvas1 = FigureCanvasTkAgg(cal_fig, master=cal_frame)
canvas1.draw(); canvas1.get_tk_widget().pack(fill="both", expand=True)
nb.add(cal_frame, text="🗕 Calendar")

# ========== Pie Chart Tab ==========
bins = list(range(1, 12))
counts = [0] * len(bins)
bin_dates = [[] for _ in bins]
for d, v in sleep_data.items():
    if v is None:
        continue
    placed = False
    for i in range(len(bins) - 1):
        if bins[i] <= v < bins[i + 1]:
            counts[i] += 1
            bin_dates[i].append(d)
            placed = True
            break
    if not placed and v >= bins[-1]:
        counts[-1] += 1
        bin_dates[-1].append(d)

labels = [f"{bins[i]}–{bins[i+1]}h" for i in range(len(bins) - 1)] + ["11h+"]
data = [(c, l, ds) for c, l, ds in zip(counts, labels, bin_dates) if c > 0]
counts, labels, bin_dates = zip(*data)

pie_fig, pie_ax = plt.subplots(figsize=(6, 6))
colors = plt.cm.viridis(np.linspace(0, 1, len(counts)))
wedges, _, _ = pie_ax.pie(counts, labels=labels, autopct='%1.1f%%', colors=colors,
                          startangle=90, counterclock=False, textprops={'fontsize': 8})
pie_ax.set_title("Distribution", weight='bold')

def show_popup(title, msg):
    messagebox.showinfo(title, msg)

def on_click(event):
    for i, w in enumerate(wedges):
        if w.contains_point([event.x, event.y]):
            lines = [f"{dstr} → {datetime.strptime(dstr, '%Y-%m-%d').strftime('%A')}" for dstr in bin_dates[i]]
            msg = f"Range: {labels[i]}\nDays: {counts[i]}\n\n" + "\n".join(lines)
            show_popup("Slice Info", msg)
            break

pie_fig.canvas.mpl_connect('button_press_event', on_click)
pie_fig.tight_layout()

pie_frame = ttk.Frame(nb)
canvas2 = FigureCanvasTkAgg(pie_fig, master=pie_frame)
canvas2.draw(); canvas2.get_tk_widget().pack(fill="both", expand=True)
nb.add(pie_frame, text="🍕 Pie Chart")

# ========== Line Chart Tab ==========
entries = sorted((datetime.strptime(d, "%Y-%m-%d"), h) for d, h in sleep_data.items() if h is not None)
monthly = defaultdict(list)
for dt, h in entries:
    monthly[dt.strftime("%Y-%m")].append((dt, h))

latest = max(monthly)
dates, hours = zip(*sorted(monthly[latest]))
avg = sum(hours) / len(hours)
mi, ma = min(hours), max(hours)
i_min, i_max = hours.index(mi), hours.index(ma)

line_fig, line_ax = plt.subplots(figsize=(7, 4))
line_ax.plot(dates, hours, '-o', label="Sleep")
line_ax.axhline(avg, ls='--', label=f"Avg {avg:.1f}h")
line_ax.plot(dates[i_min], mi, 'v', label=f"Min {mi:.1f}h")
line_ax.plot(dates[i_max], ma, '^', label=f"Max {ma:.1f}h")
line_ax.set_title(f"Trend {latest}", weight='bold')
line_ax.set_ylabel("Hours")
line_ax.set_xlabel("Date")
line_ax.grid(ls=':', alpha=0.5)
line_ax.legend()
line_fig.autofmt_xdate(); line_fig.tight_layout()

line_frame = ttk.Frame(nb)
canvas3 = FigureCanvasTkAgg(line_fig, master=line_frame)
canvas3.draw(); canvas3.get_tk_widget().pack(fill="both", expand=True)
nb.add(line_frame, text="📈 Monthly Trend")

# ========== Run App ==========
root.mainloop()