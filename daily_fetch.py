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


def get_ranking_urls(timespan):
    return [
        f"https://yomou.syosetu.com/rank/genrelist/type/{timespan}_101/",
        f"https://yomou.syosetu.com/rank/genrelist/type/{timespan}_102/",
        f"https://yomou.syosetu.com/rank/genrelist/type/{timespan}_201/",
        f"https://yomou.syosetu.com/rank/genrelist/type/{timespan}_202/",
        f"https://yomou.syosetu.com/rank/genrelist/type/{timespan}_301/",
        f"https://yomou.syosetu.com/rank/genrelist/type/{timespan}_302/",
        f"https://yomou.syosetu.com/rank/genrelist/type/{timespan}_303/",
        f"https://yomou.syosetu.com/rank/genrelist/type/{timespan}_304/",
        f"https://yomou.syosetu.com/rank/genrelist/type/{timespan}_305/",
        f"https://yomou.syosetu.com/rank/genrelist/type/{timespan}_306/",
        f"https://yomou.syosetu.com/rank/genrelist/type/{timespan}_307/",
        f"https://yomou.syosetu.com/rank/genrelist/type/{timespan}_401/",
        f"https://yomou.syosetu.com/rank/genrelist/type/{timespan}_402/",
        f"https://yomou.syosetu.com/rank/genrelist/type/{timespan}_403/",
        f"https://yomou.syosetu.com/rank/genrelist/type/{timespan}_404/",
        f"https://yomou.syosetu.com/rank/genrelist/type/{timespan}_9901/",
        f"https://yomou.syosetu.com/rank/genrelist/type/{timespan}_9902/",
        f"https://yomou.syosetu.com/rank/genrelist/type/{timespan}_9903/",
        f"https://yomou.syosetu.com/rank/genrelist/type/{timespan}_9999/",
    ]


def main():
    data = pd.read_csv("daily.csv")
    client = httpx.Client(headers=headers, timeout=TIMEOUT)
    reqs = list()
    for ts in ["daily", "weekly", "monthly"]:
        for du in get_ranking_urls(ts):
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
    if exd not in data.columns:
        raise IndexError("Date not in columns")
    for du, req in zip(dailytuples, reqs):
        # check if fin data
        if du[0] in data.id.values:
            idx = data.index[data["id"] == du[0]].values[0]
            data.at[idx, exd] = sl.extract_points(req)
        else:
            data.loc[data.shape[0]] = 0
            data.at[data.shape[0] - 1, "id"] = du[0]
            data.at[data.shape[0] - 1, "title"] = du[1]
            try:
                data.at[data.shape[0] - 1, exd] = sl.extract_points(req)
            except ValueError as e:
                nreq = httpx.get(req.url)
                data.at[data.shape[0] - 1, exd] = sl.extract_points(nreq)
    data.to_csv("daily.csv", index=False)


if __name__ == "__main__":
    main()
