import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from apify_client import ApifyClient

def scrape_kompas():
    url = "https://www.kompas.tv/section/more_json?sort_by=&limit=20&offset=0&id=&api_url=&tag=&search=&type=category_news&jsonPath=category_1_18_19_46_1"
    response = requests.get(url)
    if response.status_code != 200:
        st.error("Gagal mengambil data dari Kompas TV.")
        return pd.DataFrame()

    soup = BeautifulSoup(response.text, "html.parser")

    headlines = []
    for h2 in soup.find_all("h2", class_="title-news"):
        a_tag = h2.find("a")
        if a_tag and a_tag.text.strip():
            headlines.append({
                "judul": a_tag.text.strip(),
            })

    return pd.DataFrame(headlines)

def scrape_cnn(max_page=3):
    headlines = []
    base_url = "https://www.cnnindonesia.com/nasional/indeks/3?page="

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    for page in range(1, max_page + 1):
        url = base_url + str(page)
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            st.warning(f"Gagal mengambil halaman {page} | Status: {response.status_code}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")

        for h2 in soup.find_all("h2", class_=lambda c: c and "text-cnn_black_light" in c):
            text = h2.get_text(strip=True)
            if text:
                headlines.append({
                    "judul": text,
                })

    return pd.DataFrame(headlines)

def scrape_instagram_comments(post_url, limit=15):
    client = ApifyClient(st.secrets["APIFY_TOKEN"])

    run_input = {
        "directUrls": [post_url],
        "resultsLimit": limit,
        "isNewestComments": True,
        "includeNestedComments": False,
    }

    try:
        run = client.actor("SbK00X0JYCPblD2wp").call(run_input=run_input)
        comments = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            text = item.get("text", "")
            username = item.get("ownerUsername", "")
            comments.append({"username": username, "text": text})
        return pd.DataFrame(comments)
    except Exception as e:
        st.error(f"Terjadi kesalahan saat mengambil komentar: {e}")
        return pd.DataFrame()

st.title("Scraper App (Berita & Instagram)")

st.write("Pilih sumber data yang ingin diambil:")

source = st.radio("Pilih sumber:", ["Kompas TV", "CNN Indonesia", "Instagram Comments"])

if source == "CNN Indonesia":
    max_page = st.slider("Jumlah halaman CNN yang ingin diambil", 1, 10, 3)
elif source == "Instagram Comments":
    post_url = st.text_input("Masukkan URL postingan Instagram:")
    limit = st.slider("Jumlah komentar yang ingin diambil", 5, 100, 15)
else:
    max_page = None

if st.button("Mulai Scraping"):
    with st.spinner("Sedang mengambil data..."):
        if source == "Kompas TV":
            data = scrape_kompas()
        elif source == "CNN Indonesia":
            data = scrape_cnn(max_page)
        else:
            if not post_url:
                st.error("Harap masukkan URL postingan Instagram terlebih dahulu.")
                st.stop()
            data = scrape_instagram_comments(post_url, limit)

    if not data.empty:
        st.success(f"Berhasil mengambil {len(data)} data dari {source}")
        st.dataframe(data)
        csv = data.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Simpan ke CSV",
            data=csv,
            file_name=f"{source.lower().replace(' ', '_')}_data.csv",
            mime="text/csv"
        )
    else:
        st.error("Tidak ada data yang berhasil diambil.")