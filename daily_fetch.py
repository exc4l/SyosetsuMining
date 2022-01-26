import pandas as pd
import syosetsuLib as sl
import httpx
from bs4 import BeautifulSoup
from datetime import datetime


exd = datetime.today().strftime("%d/%m/%Y")
headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36"
}
TIMEOUT = 30


def main():
    daily = pd.read_csv("daily.csv")
    client = httpx.Client(headers=headers, timeout=TIMEOUT)
    reqs = list()
    for ts in ["daily", "weekly", "monthly"]:
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
    dailytuples = list(set(dailytuples))
    client = httpx.Client(headers=headers, timeout=TIMEOUT)
    reqs = list()
    for du in dailytuples:
        reqs.append(client.get(sl.get_info_panel(du[0])))
    client.close()
    if exd not in daily.columns:
        raise IndexError(f"Date not in columns: {exd}")
    for du, req in zip(dailytuples, reqs):
        try:
            extr_points = sl.extract_points(req)
        except ValueError as e:
            nreq = httpx.get(req.url)
            try:
                extr_points = sl.extract_points(nreq)
            except ValueError as e:
                continue
        # check if fin daily
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
