from pathlib import Path
import httpx
import asyncio
import bs4
from bs4 import BeautifulSoup
import numpy as np
import re

import functools
import json
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import pandas as pd


SYOSETSU = "https://ncode.syosetu.com"
SYOSETSU_INFO = "https://ncode.syosetu.com/novelview/infotop/ncode"


def get_info_panel(nid):
    return f"{SYOSETSU_INFO}/n{nid}/"


def read_syosetsu_csv(filename):
    db = pd.read_csv(
        filename,
        parse_dates=["initial_release", "last_update"],
        converters={"title": str, "author": str},
        dtype={
            "thoughts_num": "int64",
            "review_num": "int64",
            "bookmark_num": "int64",
            "overall_points": "int64",
            "eval_points": "int64",
            "char_count": "int64",
        },
    )
    return db


def calc_diff(b, a):
    if a == 0 or b == 0:
        return 0
    return b - a


def get_first_val(vals):
    for x in vals:
        if x != 0:
            return x


def get_last_val(lst):
    lst.reverse()
    for x in lst:
        if x != 0:
            return x


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


def get_top_novel_ids(data, topnum=10):
    diffdb = get_point_diff_dataframe(data)
    return diffdb.sort_values(by=["sum"], ascending=False)[:topnum].id.to_numpy()


def get_point_diff_dataframe(data, igno_columns=["id", "title"]):
    calccol = [col for col in data.columns if col not in igno_columns]
    calccol.reverse()
    diffdb = data.copy()
    for idx, row in diffdb.iterrows():
        for i in range(len(calccol) - 1):
            diffdb.at[idx, calccol[i]] = calc_diff(row[calccol[i]], row[calccol[i + 1]])
        diffdb.at[idx, calccol[-1]] = 0
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
            raise ValueError("Why is there a zerodivision?")
    return diffdb


def make_int(x):
    if isinstance(x, int):
        return x
    x = x.replace(",", "").replace(".", "")
    try:
        out = int(x)
    except ValueError as e:
        if x == "※非":
            out = -1
        else:
            raise e
    return out


class notab:
    def __init__(self):
        pass

    def find(self, *args, **kwargs):
        return None


def extract_points(req):
    if req.status_code == 404:
        print(req)
        print(req.status_code)
        print(req.url)
        raise ValueError("HTTP ERROR")
    soup = BeautifulSoup(req, "lxml")
    if soup.find("table", id="noveltable2"):
        tab2 = soup.find("table", id="noveltable2")
    else:
        tab2 = notab()
    if tab2.find(text="総合評価"):
        overall_points = (
            tab2.find(text="総合評価").parent.parent.find("td").get_text().split()[0][:-2]
        )
    else:
        overall_points = "0"
    return make_int(overall_points)


def parse_novel_info(req):
    if req.status_code == 404:
        raise ValueError
    soup = BeautifulSoup(req, "lxml")
    if soup.find("table", id="noveltable1"):
        tab = soup.find("table", id="noveltable1")
    else:
        tab = notab()
    if soup.find("table", id="noveltable2"):
        tab2 = soup.find("table", id="noveltable2")
    else:
        tab2 = notab()
    if tab.find(text="あらすじ"):
        desc = tab.find(text="あらすじ").parent.parent.find("td").get_text().strip()
    else:
        desc = "0"
    title = soup.find("h1").get_text()
    if tab.find(text="作者名"):
        author = (
            tab.find(text="作者名")
            .parent.parent.find("td")
            .get_text()
            .split("：")[-1]
            .strip()
        )
    else:
        author = "0"

    if tab.find(text="キーワード"):
        tags = tab.find(text="キーワード").parent.parent.find("td").get_text().split()
    else:
        tags = "0"

    if tab.find(text="ジャンル"):
        gerne = tab.find(text="ジャンル").parent.parent.find("td").get_text()
    else:
        gerne = "0"
    initial_release = tab2.find(text="掲載日").parent.parent.find("td").get_text()
    if tab2.find(text="最終部分掲載日"):
        last_update = tab2.find(text="最終部分掲載日").parent.parent.find("td").get_text()
    elif tab2.find(text="最終更新日"):
        last_update = tab2.find(text="最終更新日").parent.parent.find("td").get_text()
    elif tab2.find(text="最新部分掲載日"):
        last_update = tab2.find(text="最新部分掲載日").parent.parent.find("td").get_text()
    else:
        last_update = "0"
    char_count = tab2.find(text="文字数").parent.parent.find("td").get_text()[:-2]

    if tab2.find(text="感想"):
        thoughts_num = (
            tab2.find(text="感想").parent.parent.find("td").get_text().split()[0][:-1]
        )
    else:
        thoughts_num = "0"

    if tab2.find(text="レビュー"):
        review_num = (
            tab2.find(text="レビュー").parent.parent.find("td").get_text().split()[0][:-1]
        )
    else:
        review_num = "0"

    if tab2.find(text="ブックマーク登録"):
        bookmark_num = (
            tab2.find(text="ブックマーク登録").parent.parent.find("td").get_text()[:-1]
        )
    else:
        bookmark_num = "0"

    if tab2.find(text="総合評価"):
        overall_points = (
            tab2.find(text="総合評価").parent.parent.find("td").get_text().split()[0][:-2]
        )
    else:
        overall_points = "0"
    if tab2.find(text="評価ポイント"):
        eval_points = (
            tab2.find(text="評価ポイント").parent.parent.find("td").get_text().split()[0][:-2]
        )
    else:
        eval_points = "0"
    return (
        title,
        author,
        gerne,
        pd.to_datetime(initial_release, format="%Y年 %m月%d日 %H時%M分"),
        pd.to_datetime(
            last_update.strip(), format="%Y年 %m月%d日 %H時%M分", errors="coerce"
        ),
        make_int(thoughts_num),
        make_int(review_num),
        make_int(bookmark_num),
        make_int(overall_points),
        make_int(eval_points),
        make_int(char_count),
        tags,
        desc,
    )


def get_bing_url(query):
    return f"http://www.bing.com/images/search?q={query}&qft=+filterui:aspect-tall&FORM=HDRSC2"


async def bing_image(client, search):
    query = search
    # resp = await client.get(get_bing_url(query))
    # resp.raise_for_status()
    resp = await fetch(client, get_bing_url(query))
    ressoup = BeautifulSoup(resp, "lxml")
    image_result_raw = ressoup.find("a", {"class": "iusc"})
    m = json.loads(image_result_raw["m"])
    murl, turl = m["murl"], m["turl"]
    return murl


async def fetch(client, url):
    resp = await client.get(url)
    # resp.raise_for_status()
    return resp


def draw_shadow_text(image, x, y, text, font, maincolor, shadowcolor, thickness=1):
    tdraw = ImageDraw.Draw(image)
    # thicker border
    for i in range(1, thickness + 1):
        tdraw.text((x - i, y - i), text, font=font, fill=shadowcolor)
        tdraw.text((x + i, y - i), text, font=font, fill=shadowcolor)
        tdraw.text((x - i, y + i), text, font=font, fill=shadowcolor)
        tdraw.text((x + i, y + i), text, font=font, fill=shadowcolor)

    tdraw.text((x, y), text, font=font, fill=maincolor)


def get_japanese_number(num):
    num = str(num)
    num_dict = {
        "0": "０",
        "1": "１",
        "2": "２",
        "3": "３",
        "4": "４",
        "5": "５",
        "6": "６",
        "7": "７",
        "8": "８",
        "9": "９",
    }
    num = "".join(num_dict[c] for c in num)
    return num


def build_page(content, url):
    page = BeautifulSoup(content, "lxml")
    subtitle = page.find("p", class_="novel_subtitle").get_text()
    content = page.find("div", id="novel_honbun", class_="novel_view")
    content = content.prettify()
    append = page.find("div", id="novel_a", class_="novel_view")
    if append is not None:
        append = append.prettify()
        append = "<hr>" + append
    else:
        append = ""
    html = f"<html>\n<head>\n<title>{subtitle}</title>\n</head>\n<body>\n<div>\n<h1>{subtitle}</h1>\n{content}{append}</div>\n</body>\n</html>"
    name = url.split("/")[-2]
    built_page = epub.EpubHtml(
        title=subtitle, file_name=name + ".xhtml", content=html, lang="ja"
    )
    return name, built_page, subtitle


def build_section(sec):
    head = epub.Section(sec[0])
    main = tuple(sec[1:])
    return head, main


def get_valid_filename(name):
    """
    Taken from https://github.com/django/django/blob/main/django/utils/text.py#L225
    Modified by me.
    Return the given string converted to a string that can be used for a clean
    filename. Remove leading and trailing spaces; convert other spaces to
    underscores; and remove anything that is not an alphanumeric, dash,
    underscore, or dot.
    >>> get_valid_filename("john's portrait in 2004.jpg")
    'johns_portrait_in_2004.jpg'
    """
    s = str(name).strip()  # replace("【", "[").replace("】","]")
    s = re.sub(r"[-_\s]+", "_", s).strip("-_")
    s = re.sub(r"(?u)[^[]-\w.]", "", s)
    if s in {"", ".", ".."}:
        raise ValueError("Could not derive file name from '%s'" % name)
    return s
