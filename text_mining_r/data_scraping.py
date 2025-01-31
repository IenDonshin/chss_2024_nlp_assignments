# 江戸川乱歩のページのリンク：　https://www.aozora.gr.jp/index_pages/person1779.html#sakuhin_list_1
# 作者のページに目標とする『公開中の作品』のデータの例：赤いカブトムシ　（新字新仮名、作品ID：57105）
# 『赤いカブトムシ』のリンク：　https://www.aozora.gr.jp/cards/001779/card57105.html 
#　本のページに目標とする『ファイルのダウンロード』データの例：　の「テキストファイル(ルビあり」　https://www.aozora.gr.jp/cards/001779/files/57105_ruby_59617.zip

# libraryをimportする
import os
import re
import zipfile
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import pandas as pd

def clean_and_extract_publication_year(text):
    # 出版した時間を抽出する
    cleaned_text = re.sub(r"（[^）]*）", "", text)
    pattern = r"(\d{4})"
    match = re.search(pattern, cleaned_text)
    if match:
        return match.group(1)
    return "未知"

def extract_download_links(soup, base_url):
    # Webからすべての .zip download linkを抽出する
    download_links = []
    download_table = soup.find('table', class_='download')
    if download_table:
        download_rows = download_table.find_all('tr', bgcolor='white')
        for row in download_rows:
            link_tag = row.find('a', href=True)
            if link_tag and link_tag['href'].endswith('.zip'):
                full_url = urljoin(base_url, link_tag['href'])
                download_links.append(full_url)
    return download_links

def download_file(url, save_folder):
    # URLに従ってfileをdownloadし、指定されたfolderに保存する
    response = requests.get(url)
    response.raise_for_status()
    filename = url.split('/')[-1]
    save_path = os.path.join(save_folder, filename)
    os.makedirs(save_folder, exist_ok=True)
    with open(save_path, 'wb') as file:
        file.write(response.content)
    return save_path

def extract_zip(zip_path, extract_folder):
    # .zip fileを目的のfolderに解凍する
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_folder)
        return zip_ref.namelist() 

def rename_and_move_files(extracted_files, year, save_folder):
    # 解凍したfileの名前を変更して移動する
    renamed_files = []
    for file in extracted_files:
        old_path = os.path.join(save_folder, file)
        new_filename = f"{year}_{file}"
        new_path = os.path.join(save_folder, new_filename)
        os.rename(old_path, new_path)
        renamed_files.append(new_path)
    return renamed_files

def process_download_and_extract(url, save_folder, year):
    # .zipのfileをdownloadし、解凍して名前を変更する
    zip_path = download_file(url, save_folder)
    extracted_files = extract_zip(zip_path, save_folder)
    renamed_files = rename_and_move_files(extracted_files, year, save_folder)
    os.remove(zip_path)
    return renamed_files

def process_books(book_dict, save_folder):
    # すべてのprocessを統合する
    for book_id, book_info in book_dict.items():
        book_name, book_url = book_info[:2]  # 作品名とURLを取得
        
        # ウェブページのHTMLを取得して解析する
        response = requests.get(book_url)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 初出年份を抽出する
        try:
            initial_publication = soup.find('td', class_='header', string='初出：').find_next('td').get_text(strip=True)
            publication_year = clean_and_extract_publication_year(initial_publication)
        except AttributeError:
            publication_year = "未知"
        
        # download linkを抽出する
        download_links = extract_download_links(soup, os.path.dirname(book_url) + '/')
        
        # fileをdownloadし、解凍して名前を変更する
        renamed_files = []
        for link in download_links:
            renamed_files.extend(process_download_and_extract(link, save_folder, publication_year))
        
        # 取得した情報を更新する
        book_dict[book_id].extend([publication_year] + renamed_files)

    # 画像ファイル (.png) を除外する
    for book_id in book_dict:
        book_dict[book_id] = [info for info in book_dict[book_id] if not info.endswith('.png')]


def save_books_to_csv(books, output_file):
    # list を CSV 形式に変換して保存する
    data = []
    
    for book_id, book_info in books.items():
        book_name = book_info[0]
        book_url = book_info[1]
        publication_year = book_info[2] if len(book_info) > 2 else "未知"
        extracted_files = book_info[3:] if len(book_info) > 3 else []
        extracted_files_str = "; ".join(extracted_files)
            
        data.append([book_id, book_name, book_url, publication_year, extracted_files_str])
    
    df = pd.DataFrame(data, columns=["Book ID", "Book Name", "Download Link", "Publication Year", "File Save Path"])
    df["Text"] = ""
    df.to_csv(output_file, index=False, encoding="shift_jis")