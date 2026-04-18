import pandas as pd
from dotenv import dotenv_values

input_csv = dotenv_values('.env')['INPUT_CSV']

def analysoi_skannauksen_laajuus():
    df = pd.read_csv(input_csv)

    # Lasketaan montako *uniikkia* porttia kukin IP on kokeillut koko datan ajalta
    ip_kattavuus = df.groupby('Lähde_IP')['Kohde_portti'].nunique().reset_index()
    ip_kattavuus.columns = ['Lähde_IP', 'Uniikit_portit']

    # Suodatetaan aggressiivisimmat (esim. yli 100 eri porttia kokeilleet)
    aggressiiviset = ip_kattavuus[ip_kattavuus['Uniikit_portit'] > 100].sort_values(by='Uniikit_portit', ascending=False)

    print(f"--- Skannauksen laajuus ---")
    print(f"Löytyi {len(aggressiiviset)} IP-osoitetta, jotka ovat kokeilleet yli 100 eri porttia.")
    if not aggressiiviset.empty:
        print("Pahimmat haravoijat:")
        print(aggressiiviset.head(5).to_string(index=False))

def tunnista_aikapoikkeamat():
    df = pd.read_csv(input_csv)

    # Varmistetaan aikaleima
    date_col = 'Päivämäärä' if 'Päivämäärä' in df.columns else 'Paivamaara'
    df['Timestamp'] = pd.to_datetime(df[date_col] + ' ' + df['Kellonaika'])
    df.set_index('Timestamp', inplace=True)

    # Tarkastellaan liikennettä 10 minuutin ikkunoissa
    ikkunat = df.resample('10min').size()

    # Lasketaan tilastolliset rajat
    keskiarvo = ikkunat.mean()
    # Määritetään hälytysraja: 3 x keskiarvo on jo selkeä poikkeama
    halytysraja = keskiarvo * 3

    # Suodatetaan ikkunat, jotka ylittävät hälytysrajan
    poikkeamat = ikkunat[ikkunat > halytysraja]

    print("--- Poikkeamat ja Hyökkäyspiikit ---")
    print(f"Normaali taso: ~{keskiarvo:.0f} blokkia / 10min")
    print(f"Hälytysraja asetettu: {halytysraja:.0f} blokkiin\n")

    if poikkeamat.empty:
        print("Ei merkittäviä hyökkäyspiikkejä datassa (tasainen kohina).")
    else:
        print("HAVAITTU POIKKEUKSELLISEN SUURIA LIIKENNEMÄÄRIÄ:")
        for aika, maara in poikkeamat.items():
            print(f"- {aika.strftime('%Y-%m-%d %H:%M')}: {maara} blokkia ({(maara/keskiarvo):.1f}x yli normaalin)")

tunnista_aikapoikkeamat()
print("\n")
analysoi_skannauksen_laajuus()
