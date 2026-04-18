import time

import folium
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
import pycountry
import requests
from dotenv import dotenv_values

input_csv = dotenv_values('.env')['INPUT_CSV']
metadata_csv = dotenv_values('.env')['INPUT_METADATA_CSV']
token = dotenv_values('.env')['IPINFO_TOKEN']

def visualisoi_top_maat():
    try:
        traffic_df = pd.read_csv(input_csv)
        meta_df = pd.read_csv(metadata_csv)
    except FileNotFoundError as e:
        print(f"Virhe: Tiedostoa ei löytynyt. Varmista että '{input_csv}' ja '{metadata_csv}' ovat olemassa.")
        print(f"Yksityiskohdat: {e}")
        return

    meta_df = meta_df.rename(columns={'IP': 'Lähde_IP', 'Maa_Alpha2': 'Alpha2'})
    merged_df = pd.merge(traffic_df, meta_df[['Lähde_IP', 'Alpha2']], on='Lähde_IP', how='left')

    def hae_maan_nimi(alpha2):
        if pd.isna(alpha2) or alpha2 == '??':
            return 'Tuntematon'
        try:
            maa = pycountry.countries.get(alpha_2=alpha2)
            return maa.name if maa else alpha2
        except:
            return alpha2

    merged_df['Maan_nimi'] = merged_df['Alpha2'].apply(hae_maan_nimi)
    top_maat = merged_df['Maan_nimi'].value_counts().head(15).reset_index()
    top_maat.columns = ['Maa', 'Estot']

    top_maat = top_maat.sort_values(by='Estot', ascending=True)

    plt.figure(figsize=(14, 8))
    plt.barh(top_maat['Maa'], top_maat['Estot'], color='steelblue', edgecolor='black', alpha=0.8)

    for index, value in enumerate(top_maat['Estot']):
        plt.text(value + (max(top_maat['Estot']) * 0.01), index, f'{value:,}'.replace(',', ' '), va='center', fontsize=11)

    plt.xlabel('Estettyjen yhteyksien määrä', fontsize=12)
    plt.ylabel('Maa', fontsize=12)
    plt.title('TOP 15 Hyökkäysten alkuperämaat', fontsize=16, fontweight='bold')

    plt.grid(axis='x', linestyle='--', alpha=0.5)

    plt.xlim(0, max(top_maat['Estot']) * 1.15)

    plt.tight_layout()
    plt.savefig('top_maat_palkkidiagrammi.png', dpi=300)
    print("Kaavio tallennettu: top_maat_palkkidiagrammi.png")

def yleisimmat_osoitteet_maittain():

    df = pd.read_csv(input_csv)

    top_ips = df['Lähde_IP'].value_counts().head(20).reset_index()
    top_ips.columns = ['IP', 'Määrä']

    maiden_nimet = {}

    print(f"Haetaan tiedot {len(top_ips)} IP-osoitteelle...")

    with requests.Session() as session:
        for ip in top_ips['IP']:
            try:
                url = f"https://ipinfo.io/{ip}?token={token}"
                response = session.get(url, timeout=5)

                if response.status_code == 200:
                    data = response.json()
                    country_code = data.get('country', '??')
                    maiden_nimet[ip] = country_code
                    print(f"IP: {ip} -> Maa: {country_code}")
                elif response.status_code == 429:
                    print(f"Virhe: Rate limit ylittyi (429).")
                    maiden_nimet[ip] = 'Limit'
                else:
                    print(f"Virhe: IP {ip} status {response.status_code}")
                    maiden_nimet[ip] = f"Err {response.status_code}"

                time.sleep(0.2)

            except Exception as e:
                print(f"Virhe haettaessa IP:tä {ip}: {e}")
                maiden_nimet[ip] = 'Fail'

    top_ips['Maa'] = top_ips['IP'].map(maiden_nimet)
    top_ips['Label'] = top_ips['IP'] + " (" + top_ips['Maa'] + ")"


    plt.figure(figsize=(12, 8))
    plt.barh(top_ips['Label'], top_ips['Määrä'].to_numpy(), color='teal')

    plt.xlabel('Blokkauksien määrä')
    plt.title('Top 20 estetyt IP-osoitteet ja maat')
    plt.gca().invert_yaxis()
    plt.grid(axis='x', linestyle='--', alpha=0.5)
    plt.tight_layout()

    plt.savefig('ip_maat_analyysi.png')
    print("Kaavio tallennettu: ip_maat_analyysi.png")

def hae_alpha3(alpha2_koodi):
    if pd.isna(alpha2_koodi) or alpha2_koodi == '??':
        return None

    try:
        maa = pycountry.countries.get(alpha_2=alpha2_koodi)
        return maa.alpha_3 if maa else None
    except Exception:
        return None

def luo_maa_heatmap():
    try:
        traffic_df = pd.read_csv(input_csv)
        meta_df = pd.read_csv(metadata_csv)

    except FileNotFoundError as e:
        print(f"Virhe: Tiedostoa ei löytynyt. Varmista että '{input_csv}' ja '{metadata_csv}' ovat olemassa.")
        print(f"Yksityiskohdat: {e}")
        return

    meta_df = meta_df.rename(columns={'IP': 'Lähde_IP', 'Maa_Alpha2': 'Alpha2'})

    merged_df = pd.merge(traffic_df, meta_df[['Lähde_IP', 'Alpha2']], on='Lähde_IP', how='left')

    merged_df['Maa_koodi'] = merged_df['Alpha2'].apply(hae_alpha3)

    country_data_df = merged_df.dropna(subset=['Maa_koodi'])

    country_counts = country_data_df.groupby('Maa_koodi').size().reset_index(name='Count')

    country_counts['Log_Count'] = np.log10(country_counts['Count'])

    m = folium.Map(location=[20, 0], zoom_start=2, tiles='CartoDB positron')
    geo_url = "https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json"

    folium.Choropleth(
        geo_data=geo_url,
        name="choropleth",
        data=country_counts,
        columns=["Maa_koodi", "Log_Count"],
        key_on="feature.id",
        fill_color="YlOrRd",
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name="Hyökkäysten määrä (Log: 1=10 kpl, 2=100 kpl, 3=1000 kpl, 4=10000 kpl)",
        nan_fill_opacity=0.0
    ).add_to(m)

    folium.LayerControl().add_to(m)

    output_map_name = 'hyokkays_kartta_paikallinen_metadata.html'
    m.save(output_map_name)
    print(f"Kartta tallennettu: {output_map_name}")

def visualisoi_hyokkaykset_ajassa():
    df = pd.read_csv(input_csv)
    date_col = 'Päivämäärä' if 'Päivämäärä' in df.columns else 'Paivamaara'
    df['Timestamp'] = pd.to_datetime(df[date_col] + ' ' + df['Kellonaika'])
    df.set_index('Timestamp', inplace=True)

    attacks_over_time = df.resample('10min').size()

    # Tilastolliset tunnusluvut
    keskiarvo = attacks_over_time.mean()
    keskihajonta = attacks_over_time.std()

    # Määritetään tilastollinen poikkeamaraja (Keskiarvo + 3 x keskihajonta)
    poikkeamaraja = keskiarvo + (3 * keskihajonta)

    plt.figure(figsize=(15, 7))

    # Piirretään alkuperäinen data
    plt.plot(attacks_over_time.index, attacks_over_time.values,
             color='firebrick', linewidth=1.5, label='Blokkaukset (10min välein)')

    # Piirretään keskiarvoviiva
    plt.axhline(y=keskiarvo, color='blue', linestyle='--', linewidth=1.5,
                label=f'Keskiarvo ({keskiarvo:.0f} kpl)')

    # Piirretään tilastollinen poikkeamaraja
    plt.axhline(y=poikkeamaraja, color='orange', linestyle='-', linewidth=2,
                label=f'Poikkeamaraja (3σ): {poikkeamaraja:.0f} kpl')

    # Etsitään ja korostetaan punaisilla pisteillä kriittiset piikit
    poikkeamat = attacks_over_time[attacks_over_time > poikkeamaraja]

    plt.scatter(poikkeamat.index, poikkeamat.values, color='red', s=60, zorder=5,
                edgecolors='black', label=f'Kriittiset piikit ({len(poikkeamat)} kpl)')

    # Logaritminen asteikko ja muotoilu
    plt.yscale('log')
    plt.gca().yaxis.set_major_formatter(ticker.ScalarFormatter())
    plt.gca().yaxis.set_minor_formatter(ticker.NullFormatter())
    plt.ticklabel_format(style='plain', axis='y')

    plt.title('Estetyt hyökkäykset ja tilastolliset poikkeamat (Log-asteikko)', fontsize=14)
    plt.xlabel('Aika', fontsize=12)
    plt.ylabel('Blokkauksien määrä per 10 min', fontsize=12)

    plt.grid(True, which="both", linestyle='--', alpha=0.4)
    plt.legend()

    plt.tight_layout()
    plt.savefig('hyokkaykset_poikkeamarajalla.png', dpi=300)
    print("Kaavio tallennettu: hyokkaykset_poikkeamarajalla.png")

def visualisoi_hyokkayskohteet():
    df = pd.read_csv(input_csv)

    portti_kartta = {
        '80': 'HTTP (Web)',
        '8080': 'HTTP Alt / Proxy',
        '443': 'HTTPS (Web)',
        '23': 'Telnet (IoT/Reitittimet)',
        '22': 'SSH (Etähallinta)',
        '-': 'Ei porttia (esim. Ping)',
        '3389': 'RDP (Windows Etätyöpöytä)',
        '8728': 'MikroTik API',
        '5060': 'SIP/VoIP (Puhelin)',
        '2222': 'SSH Alt',
        '3000': 'Web-sovelluskehykset',
        '445': 'SMB (Windows tiedostonjako)',
        '81': 'HTTP Alt (Valvontakamerat)',
        '1433': 'MS SQL Server (Tietokanta)',
        '8443': 'HTTPS Alt'
    }

    top_ports = df['Kohde_portti'].astype(str).value_counts().head(15).reset_index()
    top_ports.columns = ['Portti', 'Estot']

    top_ports['Palvelu'] = top_ports['Portti'].map(portti_kartta).fillna('Tuntematon')

    top_ports['Label'] = top_ports['Portti'] + " (" + top_ports['Palvelu'] + ")"


    top_ports = top_ports.sort_values(by='Estot', ascending=True)

    plt.figure(figsize=(14, 8))

    plt.barh(top_ports['Label'], top_ports['Estot'], color='darkorange', edgecolor='black', alpha=0.8)

    for index, value in enumerate(top_ports['Estot']):
        plt.text(value + (value * 0.01), index, f'{value:,}'.replace(',', ' '), va='center', fontsize=11)

    plt.xlabel('Estettyjen yhteyksien määrä', fontsize=12)
    plt.ylabel('Kohdeportti ja todennäköinen palvelu', fontsize=12)
    plt.title('TOP 15 Hyökkäyskohteet', fontsize=16, fontweight='bold')

    plt.grid(axis='x', linestyle='--', alpha=0.5)

    plt.xlim(0, max(top_ports['Estot']) * 1.1)

    plt.tight_layout()
    plt.savefig('skannatuimmat_portit.png', dpi=300)
    print("Kaavio tallennettu: skannatuimmat_portit.png")

yleisimmat_osoitteet_maittain()
visualisoi_hyokkaykset_ajassa()
luo_maa_heatmap()
visualisoi_hyokkayskohteet()
visualisoi_top_maat()
