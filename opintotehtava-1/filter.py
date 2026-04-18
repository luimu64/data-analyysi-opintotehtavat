import csv

from dotenv import dotenv_values

input_traffic_csv = dotenv_values('.env')['INPUT_CSV']
input_metadata_csv = dotenv_values('.env')['INPUT_METADATA_CSV']
ipinfo_token = dotenv_values('.env')['IPINFO_TOKEN']

def process_firewall_logs(input_filename, output_filename):
    # Määritä manuaalinen blacklist tähän
    ip_blacklist = dotenv_values('.env')['IP_BLACKLIST'].split(',')  # Oletetaan, että musta lista on pilkuilla eroteltu

    results = []

    try:
        with open(input_filename, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                parts = line.split('\t')
                if len(parts) < 4:
                    continue

                # Erotetaan aikaleima
                timestamp_full = parts[0]
                date_part, time_part = timestamp_full.split('T')

                # Käsitellään CSV-osuus
                csv_payload = parts[3]
                reader = csv.reader([csv_payload])
                row = next(reader)

                try:
                    action = row[6].strip()    # block / pass
                    direction = row[7].strip() # in / out
                    proto = row[16].strip().lower()
                    src_ip = row[18].strip()   # Lähde-IP

                    # EHDOT:
                    # 1. Toiminto on 'block'
                    # 2. Suunta on 'in' (sisääntuleva)
                    # 3. Lähde-IP ei ole blacklistalla
                    if action == 'block' and direction == 'in' and src_ip not in ip_blacklist:
                        results.append({
                            'Päivämäärä': date_part,
                            'Kellonaika': time_part,
                            'Lähde_IP': src_ip,
                            'Kohde_IP': row[19],
                            'Lähde_portti': row[20] if len(row) > 20 else '-',
                            'Kohde_portti': row[21] if len(row) > 21 else '-',
                            'Protokolla': proto.upper()
                        })
                except IndexError:
                    continue
    except FileNotFoundError:
        print(f"Virhe: Tiedostoa '{input_filename}' ne löytynyt.")
        return

    # Kirjoitetaan lopputulos
    fieldnames = ['Päivämäärä', 'Kellonaika', 'Lähde_IP', 'Kohde_IP', 'Lähde_portti', 'Kohde_portti', 'Protokolla']
    with open(output_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"Suodatus valmis. Löytyi {len(results)} mustalla listalla olevaa sisääntulevaa estoa.")
    print(f"Tallennettu tiedostoon: {output_filename}")

# Suorita skripti
process_firewall_logs('filter.log', 'blocked_traffic.csv')
