import calendar
import pandas as pd
import syosetsuLib as sl
from datetime import date, datetime


def all_dates_current_month():
    month = datetime.now().month
    year = datetime.now().year
    num_days = calendar.monthrange(year, month)[1]
    return [
        date(year, month, day).strftime("%d/%m/%Y") for day in range(1, num_days + 1)
    ]


"""
TODO First sync
TODO create new daily
! having a csv database is obviously flawed
! dataframe.at is very slow
"""


def main():
    # sync collected daily to "database"
    # yes, this is incredibly slow (and i wont fix that)
    data = sl.read_syosetsu_csv("syosetsu.xz")
    daily = pd.read_csv("daily.csv")
    checkids = set(data.id.values)
    cols = daily.columns[2:].to_list()
    # print(cols)
    for idx, row in daily.iterrows():
        vals = row[2:].to_list()
        lastval = sl.get_last_val(vals)
        lastvalidx = vals.index(lastval)
        if row["id"] in checkids:
            rowdex = data[data["id"] == row["id"]].index[0]
            data.at[rowdex, "overall_points"] = lastval
            data.at[rowdex, "last_update"] = datetime.strptime(
                cols[lastvalidx], "%d/%m/%Y"
            )
        else:
            data.loc[data.shape[0]] = 0
            data.at[data.shape[0] - 1, "id"] = row["id"]
            data.at[data.shape[0] - 1, "title"] = row["title"]
            data.at[data.shape[0] - 1, "overall_points"] = lastval
            data.at[data.shape[0] - 1, "last_update"] = datetime.strptime(
                cols[lastvalidx], "%d/%m/%Y"
            )
    data.to_csv("syosetsu.xz", compression="xz", index=False)

    # create new daily
    # drop all dates besides the last 5
    # collect 100 top novels
    # insert full month into csv
    dropcol = daily.columns[2:][:-5]
    tdaily = daily.drop(labels=dropcol, axis=1)
    tops = sl.get_top_novel_ids(tdaily, topnum=100)
    ndaily = tdaily[tdaily["id"].isin(tops)]
    for col in all_dates_current_month():
        ndaily.insert(len(ndaily.columns), col, 0)
    ndaily.to_csv("ndaily.csv", index=False)


if __name__ == "__main__":
    if datetime.now().day == 1:
        main()
