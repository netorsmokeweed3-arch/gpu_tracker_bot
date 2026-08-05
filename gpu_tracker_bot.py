import json
import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
TOKEN = "8984005242:AAFJycoN8PSDgabOytZqAhrtIkuXIL-eplQ"
CHAT_ID = "7873272830"

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code != 200:
            print(f"Помилка Telegram: {r.text}")
    except Exception as e:
        print(f"Помилка надсилання в Telegram: {e}")

CARDS_TO_TRACK = [
    {
        "name": "Palit GeForce RTX 5060 Ti White OC",
        "url": "https://hotline.ua/ua/computer-videokarty/palit-geforce-rtx-5060-ti-white-oc-ne7506tu19t1-gb2061m/",
    },
    {
        "name": "Palit GeForce RTX 5060 Ti Infinity 3 OC",
        "url": "https://hotline.ua/ua/computer-videokarty/palit-geforce-rtx-5060-ti-infinity-3-oc-ne7506ts19t1-gb2061s/",
    },
    {
        "name": "Gigabyte GeForce RTX 5060 TI AERO OC 16G",
        "url": "https://hotline.ua/ua/computer-videokarty/gigabyte-geforce-rtx-5060-ti-aero-oc-16g-gv-n506taero-oc-16gd/",
    },
    {
        "name": "Gigabyte GeForce RTX 5060 TI GAMING OC 16G",
        "url": "https://hotline.ua/ua/computer-videokarty/gigabyte-geforce-rtx-5060-ti-gaming-oc-16g-gv-n506tgaming-oc-16gd/",
    },
    {
        "name": "Gigabyte GeForce RTX 5060 TI EAGLE MAX OC 16G",
        "url": "https://hotline.ua/ua/computer-videokarty/gigabyte-geforce-rtx-5060-ti-eagle-max-oc-16g-gv-n506teaglemax-oc-16gd/",
    },
    {
        "name": "Zotac GAMING GeForce RTX 5060 Ti 16GB Twin Edge OC White",
        "url": "https://hotline.ua/ua/computer-videokarty/zotac-gaming-geforce-rtx-5060-ti-16gb-twin-edge-oc-white-zt-b50620q-10/",
    },
    {
        "name": "INNO3D GeForce RTX 5060 TI 16GB TWIN X2 OC WHITE",
        "url": "https://hotline.ua/ua/computer-videokarty/inno3d-geforce-rtx-5060-ti-16gb-twin-x2-oc-white-n506t2-16d7x-191073w/",
    },
    {
        "name": "MSI GeForce RTX 5060 TI 16G GAMING OC",
        "url": "https://hotline.ua/ua/computer-videokarty/msi-geforce-rtx-5060-ti-16g-gaming-oc/",
    }
]

HISTORY_FILE = "prices_history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_history(data):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_hotline_price_range_with_browser(page, url):
    try:
        print(f"Браузер відкриває сторінку: {url}")
        page.goto(url, timeout=30000)
        page.wait_for_selector(".price, [class*='price'], [class*='cost']", timeout=10000)
        
        price_texts = page.eval_on_selector_all(
            "span, div, a",
            "elements => elements.map(el => el.innerText).filter(text => text && (text.includes('₴') || text.includes('грн') || (text.length < 10 && /\d/.test(text))))"
        )

        found_prices = []
        for text in price_texts:
            digits = "".join(filter(str.isdigit, text))
            if digits and len(digits) >= 4:
                val = int(digits[:5] if len(digits) >= 5 else digits)
                # Беремо все від 30000 до 45000, але суворо виключаємо помилкову 28499
                if 30000 <= val <= 45000 and val != 28499:
                    found_prices.append(val)

        if found_prices:
            unique_prices = sorted(list(set(found_prices)))
            min_p = unique_prices[0]
            max_p = unique_prices[-1]
            print(f"Знайдено діапазон: від {min_p} до {max_p} грн")
            return {"min": min_p, "max": max_p}

    except Exception as e:
        print(f"Помилка завантаження через браузер: {e}")

    return None

def check_and_send_report():
    history = load_history()
    current_data = {}
    
    report_lines = [
        f"📊 *Моніторинг цін на RTX 5060 Ti 16GB*",
        f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
    ]
    
    lowest_prices_summary = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        for card in CARDS_TO_TRACK:
            name = card["name"]
            url = card["url"]
            
            price_range = get_hotline_price_range_with_browser(page, url)
            
            if price_range:
                curr_min = price_range["min"]
                curr_max = price_range["max"]
                current_data[name] = {"min": curr_min, "max": curr_max}
                
                # Додаємо в підсумковий список найнижчих цін
                lowest_prices_summary.append((name, curr_min))
                
                old_range = history.get(name)
                if old_range and isinstance(old_range, dict):
                    old_min = old_range.get("min")
                    old_max = old_range.get("max")
                    
                    if old_min is not None and old_max is not None:
                        diff_min = curr_min - old_min
                        if diff_min > 0:
                            status = f"📈 Подорожчало (мін. ціна +{diff_min} грн)"
                        elif diff_min < 0:
                            status = f"📉 Подешевшало (мін. ціна {diff_min} грн)"
                        else:
                            status = "🟦 Ціна без змін"
                            
                        report_lines.append(
                            f"🔹 *{name}*:\n"
                            f"   Вчора: від {old_min} до {old_max} грн\n"
                            f"   Сьогодні: від {curr_min} до {curr_max} грн\n"
                            f"   Статус: {status}\n"
                        )
                    else:
                        report_lines.append(
                            f"🔹 *{name}*:\n"
                            f"   Сьогодні: від {curr_min} до {curr_max} грн (перший запуск)\n"
                        )
                else:
                    report_lines.append(
                        f"🔹 *{name}*:\n"
                        f"   Сьогодні: від {curr_min} до {curr_max} грн (перший запуск)\n"
                    )
            else:
                report_lines.append(f"🔹 *{name}*:\n   Ціну не знайдено ⚠️ або немає в наявності\n")
                
            report_lines.append("-----------------")
            
        browser.close()
        
    # Блок з найнижчими цінами в кінці звіту
    if lowest_prices_summary:
        report_lines.append("\n🏆 *Найнижчі ціни на всі знайдені карти:*")
        # Сортуємо за мінімальною ціною від найдешевшої до найдорожчої
        lowest_prices_summary.sort(key=lambda x: x[1])
        for card_name, min_price in lowest_prices_summary:
            report_lines.append(f"• {card_name} — від *{min_price} грн*")
            
    save_history(current_data)
    
    full_report = "\n".join(report_lines)
    send_telegram_message(full_report)

if __name__ == "__main__":
    print("Запуск трекера цін...")
    check_and_send_report()
    print("Готово!")