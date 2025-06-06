import numpy as np
import pandas as pd
import syosetsuLib as sl
import httpx
import time
from bs4 import BeautifulSoup
from datetime import datetime
from tqdm import tqdm

exd = datetime.today().strftime("%d/%m/%Y")
headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36"
}
TIMEOUT = 30
TOPNUM = 100
igno_columns = ["id", "title"]


def calc_diff(b, a):
    if a == 0 or b == 0:
        return 0
    return b - a


def main():
    daily = pd.read_csv("daily.csv")

    calccol = [col for col in daily.columns if col not in igno_columns]
    calccol.reverse()

    diffdb = daily.copy()

    for idx, row in diffdb.iterrows():
        for i in range(len(calccol) - 1):
            diffdb.at[idx, calccol[i]] = calc_diff(row[calccol[i]], row[calccol[i + 1]])
        diffdb.at[idx, calccol[-1]] = 0

    diffdb["sum"] = 0
    i = 0
    for idx, row in diffdb.iterrows():
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

    topids = diffdb.sort_values(by=["sum"], ascending=False)[:TOPNUM].id.to_list()
    topnames = diffdb.sort_values(by=["sum"], ascending=False)[:TOPNUM].title.to_list()

    print("Create Client for Rankings\n")
    client = httpx.Client(headers=headers, timeout=TIMEOUT)
    reqs = list()
    for ts in tqdm(["daily", "weekly", "monthly"], desc="Fetch Rankings"):
        for du in sl.get_ranking_urls(ts):
            reqs.append(client.get(du))
    client.close()
    dailytuples = list()
    for req in reqs:
        soup = BeautifulSoup(req, "lxml")
        for t in soup.find_all("div", class_="ranking_list"):
            # temp = dict()
            # print(t.find("span", class_="ranking_number").get_text())
            # print(t.find("a", class_="tl").get("href"))
            u = t.find("a", class_="tl").get("href").split("/")[-2][1:]
            # print(t.find("a", class_="tl").get_text())
            tl = t.find("a", class_="tl").get_text()
            dailytuples.append((u, tl))
    for u, tl in zip(topids, topnames):
        dailytuples.append((u, tl))
    print("Create Client for Daily\n")
    dailytuples = list(set(dailytuples))
    client = httpx.Client(headers=headers, timeout=TIMEOUT)
    reqs = list()
    for du in tqdm(dailytuples, desc="Fetching Daily Info"):
        result = None
        while result is None:
            try:
                result = client.get(sl.get_info_panel(du[0]))
            except httpx.ConnectTimeout:
                time.sleep(5)

        reqs.append(result)
    client.close()
    if exd not in daily.columns:
        raise IndexError(f"Date not in columns: {exd}")
    for du, req in tqdm(zip(dailytuples, reqs), desc="Extracting Data"):
        if req.status_code != 200:
            print(f"Skipping {du[0]} due to HTTP {req.status_code}")
            continue
        try:
            extr_points = sl.extract_points(req)
        except ValueError:
            try:
                nreq = httpx.get(req.url)
                if nreq.status_code != 200:
                    continue
                extr_points = sl.extract_points(nreq)
            except ValueError:
                continue
        # check if in daily
        if du[0] in daily.id.values:
            idx = daily.index[daily["id"] == du[0]].values[0]
            daily.at[idx, exd] = extr_points
        else:
            daily.loc[daily.shape[0]] = 0
            daily.at[daily.shape[0] - 1, "id"] = du[0]
            daily.at[daily.shape[0] - 1, "title"] = du[1]
            daily.at[daily.shape[0] - 1, exd] = extr_points
    daily.to_csv("daily.csv", index=False)


if __name__ == "__main__":
    main()
