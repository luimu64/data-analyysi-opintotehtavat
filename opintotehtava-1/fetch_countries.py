import os

import pandas as pd
import requests
from dotenv import dotenv_values

input_traffic_csv = dotenv_values('.env')['INPUT_CSV']
input_metadata_csv = dotenv_values('.env')['INPUT_METADATA_CSV']
ipinfo_token = dotenv_values('.env')['IPINFO_TOKEN']

def fetch_and_save_ip_metadata_safe(input_traffic_csv, output_metadata_csv, token):
    df = pd.read_csv(input_traffic_csv)
    unique_ips = df['Lähde_IP'].unique()

    existing_ips = set()
    file_exists = os.path.exists(output_metadata_csv)

    if file_exists:
        existing_df = pd.read_csv(output_metadata_csv)
        existing_ips = set(existing_df['IP'].unique())
        print(f"Löydetty {len(existing_ips)} aiemmin haettua IP-tietoa.")

    ips_to_fetch = [ip for ip in unique_ips if ip not in existing_ips]
    total_to_fetch = len(ips_to_fetch)

    if total_to_fetch == 0:
        print("Kaikki IP-tiedot on jo haettu.")
        return

    print(f"Aloitetaan haku {total_to_fetch} uudelle IP:lle. Tallennus 100 kpl välein.")

    batch = []
    processed_count = 0

    with requests.Session() as session:
        for ip in ips_to_fetch:
            if ip.startswith(('10.', '192.168.', '172.16.')):
                continue

            try:
                res = session.get(f"https://api.ipinfo.io/lite/{ip}?token={token}", timeout=10)

                if res.status_code == 200:
                    data = res.json()
                    batch.append({
                        'IP': ip,
                        'Maa_Alpha2': data.get('country_code', '??'),
                        'Operaattori': data.get('as_name', 'Unknown')
                    })
                elif res.status_code == 429:
                    print("\nRate limit ylittyi. Tallennetaan ja lopetetaan.")
                    break

                if len(batch) >= 100:
                    write_batch_to_csv(batch, output_metadata_csv)
                    processed_count += len(batch)
                    print(f"Tallennettu... Yhteensä valmiina: {processed_count}/{total_to_fetch}")
                    batch = []

            except Exception as e:
                print(f"\nVirhe IP:n {ip} kohdalla: {e}")
                continue

    if batch:
        write_batch_to_csv(batch, output_metadata_csv)
        print(f"Viimeiset {len(batch)} kpl tallennettu.")

def write_batch_to_csv(batch_data, filename):
    batch_df = pd.DataFrame(batch_data)
    file_exists = os.path.exists(filename)
    batch_df.to_csv(filename, mode='a', index=False, header=not file_exists, encoding='utf-8')

fetch_and_save_ip_metadata_safe(input_traffic_csv, input_metadata_csv, ipinfo_token)
