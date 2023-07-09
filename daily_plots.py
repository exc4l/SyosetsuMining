import datetime as dt
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import matplotx
import numpy as np
import pandas as pd


TOPNUM = 10
PLOTPATH = Path("plots")
STYLEPATH = PLOTPATH / "TokyoModNight.mplstyle"
fprop = fm.FontProperties(
    fname=PLOTPATH / "NotoSansJP-Regular.otf",
    size=13,
)
igno_columns = ["id", "title"]

data = pd.read_csv("daily.csv")


def calc_diff(b, a):
    if a == 0 or b == 0:
        return 0
    return b - a


def get_first_val(vals):
    for x in vals:
        if x != 0:
            return x


def get_five_ele(lst):
    if len(lst) > 14:
        return lst[:-1][0 : -2 : len(lst) // 5 + 1] + [lst[-1]]
    return lst[:-1][0 : -1 : len(lst) // 5 + 1] + [lst[-1]]


data.columns
calccol = [col for col in data.columns if col not in igno_columns]
calccol.reverse()

diffdb = data.copy()

for idx, row in diffdb.iterrows():
    for i in range(len(calccol) - 1):
        diffdb.at[idx, calccol[i]] = calc_diff(row[calccol[i]], row[calccol[i + 1]])
    diffdb.at[idx, calccol[-1]] = 0

# diffdb["sum"] = diffdb.iloc[:, 2:].sum(axis=1)
diffdb["sum"] = 0
i = 0
for idx, row in diffdb.iterrows():
    # i+=1
    # if i>10:
    #     break
    val = row.iloc[2:].values
    zeros = np.count_nonzero(val == 0) - 1
    valsum = np.sum(val)
    if valsum == 0:
        continue
    try:
        diffdb.at[idx, "sum"] = valsum / (val.shape[0] - zeros - 1)
    except ZeroDivisionError as e:
        print(val)
        print(zeros)
        print(np.sum(val))
        print((val.shape[0] - zeros - 1))
        print(np.sum(val) / (val.shape[0] - zeros - 1))
        print(f"{idx=}")

topids = diffdb.sort_values(by=["sum"], ascending=False)[:TOPNUM].id.to_numpy()

# plt.rcParams["font.family"] = "Noto Sans JP"
with plt.style.context(matplotx.styles.dufte):
    with plt.style.context(STYLEPATH):
        fig, ax1 = plt.subplots(figsize=(10, 6))
        totx = []
        for a in topids:
            # print(data[data["id"] == a].iloc[:,2:].sum(axis=1))
            ax1.grid(zorder=0)
            # y = (
            #     data[data["id"] == a].iloc[:, 2:].values
            #     - data[data["id"] == a].iloc[:, 2].values
            # )
            y = data[data["id"] == a].iloc[:, 2:].values - get_first_val(
                data[data["id"] == a].iloc[:, 2:].values[0]
            )
            y = y.reshape(-1)
            x = data[data["id"] == a].iloc[:, 2:].columns
            xdates = [
                dt.datetime.strptime(k, "%d/%m/%Y")
                for idx, k in enumerate(x)
                if y[idx] >= 0
            ]
            if len(xdates) > len(totx):
                totx = xdates
            y = y[y >= 0]
            ax1.plot(
                xdates, y, label=str(data[data["id"] == a]["title"].values[0])[:12]
            )
        # ax1.set_yscale("log")
        fig.suptitle(
            "Absolute Point Increase",
            fontsize=18,
            fontweight="bold",
        )
        ax1.set_ylim(bottom=0)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m/%Y"))
        ax1.xaxis.set_minor_locator(mdates.DayLocator())
        ax1.set_xticks(get_five_ele(totx))
        ax1.tick_params(which="both", length=10, pad=10)
        ax1.grid(visible=True, which="minor")
        # plt.rcParams["sans-serif"] = fprop.get_name()
        # matplotlib.rc('font', family=fprop.get_name())
        # plt.rcParams["font.family"] = fprop.get_name()
        # dufte.legend()
        matplotx.line_labels(fontproperties=fprop)
        plt.savefig(PLOTPATH / "point_increase.png", bbox_inches="tight")

with plt.style.context(matplotx.styles.dufte):
    with plt.style.context(STYLEPATH):
        fig, ax1 = plt.subplots(figsize=(10, 6))
        for a in topids:
            # print(data[data["id"] == a].iloc[:,2:].sum(axis=1))
            ax1.grid(zorder=0)
            y = data[data["id"] == a].iloc[:, 2:].values
            y = y.reshape(-1)
            y = y.astype(float)
            y[y == 0] = np.nan
            x = data[data["id"] == a].iloc[:, 2:].columns
            xdates = [
                dt.datetime.strptime(k, "%d/%m/%Y")
                for idx, k in enumerate(x)
                if not np.isnan(y[idx])
            ]
            y = y[~np.isnan(y)]
            ax1.plot(
                xdates, y, label=str(data[data["id"] == a]["title"].values[0])[:12]
            )
        # ax1.set_yscale("log")
        fig.suptitle(
            "Total Points",
            fontsize=18,
            fontweight="bold",
        )
        ax1.set_ylim(bottom=0)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m/%Y"))
        ax1.xaxis.set_minor_locator(mdates.DayLocator())
        ax1.set_xticks(get_five_ele(totx))
        ax1.tick_params(which="both", length=10, pad=10)
        ax1.grid(visible=True, which="minor")

        matplotx.line_labels(
            fontproperties=fprop,
        )
        plt.savefig(PLOTPATH / "point_trend.png", bbox_inches="tight")

with open("README.md", "r", encoding="utf-8") as f:
    readmetext = f.read()


def get_ncode_link(nid):
    return f"https://ncode.syosetu.com/n{nid}/"


trendstr = ""
for count, a in enumerate(topids):
    trendstr = (
        trendstr
        + f"{count+1}. [{str(data[data['id'] == a]['title'].values[0])}]({get_ncode_link(a)})\n"
    )
readmetext = (
    readmetext[: readmetext.find("## Trending") + len("## Trending")]
    + "\n\n"
    + trendstr
)

with open("README.md", "w", encoding="utf-8") as wr:
    wr.write(readmetext)
