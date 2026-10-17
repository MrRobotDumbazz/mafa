import re
import unicodedata
import zipfile
import xml.etree.ElementTree as ET

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def norm_name(s):
    s = unicodedata.normalize("NFKC", str(s or "")).strip().upper()
    return s.replace("Х", "X").replace(" ", "")


def parse_t(s):
    if not s:
        return None
    s = str(s).lower()
    total = 0
    for m in re.finditer(r"(\d+)\s*(мин\w*|сек\w*)", s):
        v, u = int(m.group(1)), m.group(2)
        total += v * 60 if u.startswith("мин") else v
    return total or None


def _sheet_rows(path):
    z = zipfile.ZipFile(path)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall(f"{NS}si"):
            shared.append("".join(t.text or "" for t in si.iter(f"{NS}t")))
    root = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    for row in root.iter(f"{NS}row"):
        vals = []
        for c in row.iter(f"{NS}c"):
            v = c.find(f"{NS}v")
            vals.append(shared[int(v.text)] if v is not None and c.get("t") == "s" else (v.text if v is not None else ""))
        yield vals


def load_labels(path):
    out = {}
    rows = list(_sheet_rows(path))
    for row in rows[1:]:
        r = list(row) + ["", "", "", ""]
        if not r[0]:
            continue
        name = norm_name(r[0])
        if not name:
            continue
        verdict_raw = str(r[2] or "").strip().lower()
        out[name] = {
            "verdict": "violation" if "нарушен" in verdict_raw and "без нарушен" not in verdict_raw else "clean",
            "t": parse_t(r[1]),
            "hyp": str(r[3]).strip() if r[3] else "",
        }
    return out


GT_TYPE_MAP = {
    "Вернула сдачу, не посчитав деньги в аппарате": "ISSUE_NO_RECOUNT",
    "Не Показал удостоверение личности": "ISSUE_NO_ID",
    "Деньги должны быть отложены в недоступное для клиента место": "RECV_FUNDS_ACCESSIBLE",
    "Не закрыли кабинет": "ROOM_DOOR_OPEN",
    "Сложить деньги вместе": "CASH_MIXED_WORN",
    "Совместили деньги": "CASH_MIXED_WORN",
    "Свет не включили": "ROOM_LOW_LIGHT",
    "Отдал ушел без удостоверение": "ISSUE_NO_ID",
    "Заходит другой человек": "ROOM_THIRD_PARTY",
    "Не закрыли сейф": "ROOM_SAFE_OPEN",
    "Ключ не забрали от сейфа": "ROOM_KEY_ABANDONED",
    "Не проверили закрыт ли сейф или нет": "ROOM_SAFE_OPEN",
    "Оставили деньги на столе": "ROOM_MONEY_ON_TABLE",
    "Дверь не закрыта": "ROOM_DOOR_OPEN",
    "Ушел человек не получив ничего": "ANOM_CLIENT_LEFT_EMPTY",
    "Лишние вещи на столе": "ROOM_PERSONAL_ITEMS",
}
