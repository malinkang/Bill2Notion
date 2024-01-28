import argparse
import csv
from datetime import datetime
import os
import re
import pendulum
import requests
from zipfile import ZipFile
from notion_helper import NotionHelper
from utils import (
    get_date,
    get_icon,
    get_number,
    get_relation,
    get_rich_text,
    get_title,
)


def donwload_zip():
    zip_url = None
    if re.search(r"https?://\S+\.zip", body):
        zip_url = re.search(r"https?://\S+\.zip", body).group()
    results = []
    if zip_url:
        # Download the zip file
        headers = {
            "Authorization": f'{os.getenv("GITHUB_TOKEN")}',
            "Accept": "application/octet-stream",
        }
        print(f"zip url = {zip_url}")
        r = requests.get(zip_url, headers=headers)
        zip_path = "downloaded.zip"
        with open(zip_path, "wb") as zip_file:
            zip_file.write(r.content)

        # Unzip the file using the password from secrets
        with ZipFile(zip_path) as zip_ref:
            zip_ref.extractall(pwd=os.getenv("ZIP_PASSWORD").encode())
            # Print the list of file names
            print("Contents of the zip file:")
            for file_info in zip_ref.infolist():
                file_path = os.path.abspath(file_info.filename)
                if file_path.endswith(".csv"):
                    results.extend(parse_csv(file_path))

        print("Zip file downloaded and extracted.")
    else:
        print("No zip file URL found in issue body or comments.")
    return results


encodings = ["utf-8", "gbk"]


def parse_csv(file):
    results = []
    for encoding in encodings:
        try:
            with open(file, encoding=encoding) as csvfile:
                reader = csv.reader(csvfile)
                header = None
                for index, row in enumerate(reader):
                    d = {}
                    if "交易时间" in row:
                        header = row
                        print(header)
                        continue
                    if header != None:
                        for index, column in enumerate(header):
                            d[column] = row[index]
                        results.append(d)

                break
        except UnicodeDecodeError as e:
            print(f"尝试使用编码 {encoding} 读取时出错: {e}")
    return results


def create_page(page_id,date, type, payee, product, amount, price, note, method,no):
    payee = notion_helper.get_relation_id(
        payee,
        notion_helper.payee_database_id,
        "https://www.notion.so/icons/shop_gray.svg",
    )
    method = notion_helper.get_relation_id(
        method,
        notion_helper.method_database_id,
        "https://www.notion.so/icons/credit-card_gray.svg",
    )
    category = notion_helper.get_relation_id(
        type,
        notion_helper.category_database_id,
        "https://www.notion.so/icons/kind_gray.svg",
    )    
    amount = notion_helper.get_relation_id(
        amount,
        notion_helper.income_database_id,
        "https://www.notion.so/icons/kind_gray.svg",
    )
    properties = {
        "日期": get_date(start=date),
        "分类": get_relation([category]),
        "商品": get_title(product),
        "商家": get_relation([payee]),
        "支付方式": get_relation([method]),
        "收/支": get_relation([amount]),
        "金额(元)": get_number(price),
        "备注": get_rich_text(note),
        "交易单号": get_rich_text(no),
        "交易单号": get_rich_text(no),
    }
    notion_helper.get_date_relation(properties,pendulum.parse(date))
    parent = {"database_id": notion_helper.bill_database_id, "type": "database_id"}
    if page_id:
        pass
    else:    
        notion_helper.create_page(
            parent=parent,
            properties=properties,
            icon=get_icon("https://www.notion.so/icons/cash_gray.svg"),
        )

def check(transaction_id):
    filter = { 
        "property": "交易单号",
        "rich_text": {"equals": transaction_id},
    }
    results = notion_helper.query(database_id=notion_helper.bill_database_id,filter=filter)
    if results.get("results"):
        return results["results"][0]["id"]
    else:
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    notion_helper = NotionHelper()
    parser.add_argument("body")
    options = parser.parse_args()
    body = options.body
    results = donwload_zip()
    for result in results:
        amount = result.get("收/支")
        if amount != "收入" and amount != "支出":
            continue
        date = result.get("交易时间")
        type = result.get("交易类型") if result.get("交易类型") else result.get("交易分类")
        product = result.get("商品") if result.get("商品") else result.get("商品说明")
        price = result.get("金额(元)") if result.get("金额(元)") else result.get("金额")
        price = float(price.replace("¥", ""))
        if(amount=="支出"):
            price = 0 - price
        method = result.get("支付方式") if result.get("支付方式") else result.get("收/付款方式")
        payee = result.get("交易对方")
        no = result.get("交易单号") if result.get("交易单号") else result.get("交易订单号")
        no = no.strip()
        note = result.get("备注")
        page_id = check(no)
        print(f"交易单号{no} page_id={page_id}")
        create_page(page_id,date, type, payee, product, amount, price, note, method,no)


