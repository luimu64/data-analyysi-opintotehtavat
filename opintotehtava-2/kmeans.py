import ipaddress

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import ScalarFormatter
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# Datan lataus
df = pd.read_csv("blocked_traffic.csv")

# Datan siivous ja tyyppimuunnokset
# Muutetaan portit numeroiksi ja poistetaan virheelliset rivit
df["Kohde_portti"] = pd.to_numeric(df["Kohde_portti"], errors="coerce")
df["Lähde_portti"] = pd.to_numeric(df["Lähde_portti"], errors="coerce")


# Muunnetaan IP-osoitteet numeroiksi K-meansia varten
def ip_to_int(ip):
    try:
        return int(ipaddress.IPv4Address(str(ip).strip()))
    except:
        return np.nan


df["IP_num"] = df["Lähde_IP"].apply(ip_to_int)

# Poistetaan rivit, joissa on NaN-arvoja
df_clean = df.dropna(subset=["IP_num", "Kohde_portti", "Lähde_portti"]).copy()

# Käytetään IP-numeroa, lähdeporttia ja kohdeporttia
X = df_clean[["IP_num", "Lähde_portti", "Kohde_portti"]]

# Skalaus
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

"""
# Kyynärpäämetodi jolla saamme selville optimaalisen k:n arvon
inertia = []
k_range = range(1, 11)  # Testataan ryhmämäärät 1-10

for k in k_range:
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    kmeans.fit(X_scaled)
    inertia.append(kmeans.inertia_)

# Visualisointi
plt.figure(figsize=(10, 6))
plt.plot(k_range, inertia, marker="o", linestyle="--", color="b")
plt.xlabel("Ryhmien määrä (k)")
plt.ylabel("Inertia (WCSS)")
plt.title("Kyynärpäämenetelmä optimaalisen k:n löytämiseksi")
plt.xticks(k_range)
plt.grid(True)
"""

# K-means -klusterointi
kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
df_clean["Ryhma"] = kmeans.fit_predict(X_scaled)

# Tulosten tulostus raporttia varten
print(f"Analysoitu {len(df_clean)} riviä.")
print("\nRyhmien koot:")
print(df_clean["Ryhma"].value_counts())

# Visualisointi
plt.figure(figsize=(12, 7))
scatter = plt.scatter(
    df_clean["Lähde_portti"],
    df_clean["Kohde_portti"],
    c=df_clean["Ryhma"],
    cmap="rainbow",
    s=1,
    alpha=0.1,
)

plt.colorbar(scatter, label="Ryhmä ID")
plt.xlabel("Lähdeportti")
plt.ylabel("Kohdeportti")
plt.gca().yaxis.set_major_formatter(ScalarFormatter())
plt.grid(True, which="both", linestyle="--", alpha=0.5)
plt.tick_params(axis="y", labelsize=9)
plt.title("K-means: Hyökkäysprofiilien ryhmittely")
plt.grid(True, linestyle="--", alpha=0.5)
plt.show()

profiili = df_clean.groupby("Ryhma").agg(
    {
        "Kohde_portti": ["mean", "std"],  # Missä porteissa ne viihtyvät?
        "Lähde_portti": "mean",  # Onko lähdeportti vakio?
        "IP_num": "nunique",  # Kuinka monta eri hyökkääjää ryhmässä on?
    }
)
print(profiili)
