import ipaddress
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.utils import class_weight
from tensorflow.keras import layers, models
from tensorflow.keras.callbacks import EarlyStopping

# DATAN LATAUS JA YHDISTÄMINEN
# Käytetään raportin 1 kuvaamia lokitietoja
df_lokit = pd.read_csv("blocked_traffic.csv")  # Sisältää portit ja pituudet

# Siivotaan ja varmistetaan numeerisuus
df_lokit["Kohde_portti"] = pd.to_numeric(df_lokit["Kohde_portti"], errors="coerce")
df_lokit["Lähde_portti"] = pd.to_numeric(df_lokit["Lähde_portti"], errors="coerce")


def ip_to_int(ip):
    try:
        return int(ipaddress.IPv4Address(str(ip).strip()))
    except:
        return np.nan


df_lokit["IP_num"] = df_lokit["Lähde_IP"].apply(ip_to_int)
df = df_lokit.dropna(subset=["IP_num", "Lähde_portti", "Kohde_portti"])


# LUOKITTELULOGIIKKA
# Luodaan tekoälylle "oikeat vastaukset" tunnettujen porttien perusteella
def classify_attack(port):
    if port in [22, 23, 2222, 3389]:
        return "Brute-force"  # SSH, Telnet, RDP
    if port in [80, 443, 8080, 3000, 8443]:
        return "Web-exploit"  # HTTP/S
    return "Scan/Other"  # Laaja porttien haravointi


df["Attack_Type"] = df["Kohde_portti"].apply(classify_attack)

df_web = df[df["Attack_Type"] == "Web-exploit"]
df_brute = df[df["Attack_Type"] == "Brute-force"]
df_scan = df[df["Attack_Type"] == "Scan/Other"].sample(
    n=len(df_web) * 2
)  # Otetaan vain tuplamäärä webbiin nähden

# Yhdistetään takaisin tasapainoisemmaksi paketiksi
df_balanced = (
    pd.concat([df_web, df_brute, df_scan]).sample(frac=1).reset_index(drop=True)
)

# Valmistellaan piirteet (X) ja tavoite (y)
X = df_balanced[["IP_num", "Lähde_portti", "Kohde_portti"]].values.astype("float32")

# VALMISTELLAAN TAVOITE TASAPAINOTETUSTA DATASTA
le = LabelEncoder()
y = le.fit_transform(df_balanced["Attack_Type"])

class_names = list(le.classes_)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# NEUROVERKKO JA SKAALAUS
normalizer = layers.Normalization(axis=-1)
normalizer.adapt(X_train)

model = models.Sequential(
    [
        normalizer,
        layers.Dense(128, activation="relu"),
        layers.Dropout(0.3),
        layers.Dense(64, activation="relu"),
        layers.Dense(len(class_names), activation="softmax"),
    ]
)

model.compile(
    optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"]
)

# KOULUTUS JA VISUALISOINTI
weights = class_weight.compute_class_weight(
    class_weight="balanced", classes=np.unique(y_train), y=y_train
)
class_weights_dict = dict(enumerate(weights))

# Koulutetaan mallia kunnes se meinaa alkaa ylioppimaan
early_stop = EarlyStopping(
    monitor="val_loss",
    patience=5,  # Kuinka monta epochia odotetaan ilman parannusta
    restore_best_weights=True,
    start_from_epoch=30,
)

history = model.fit(
    X_train,
    y_train,
    epochs=50,
    validation_split=0.2,
    callbacks=[early_stop],
)

# Tallennetaan malli ja nimet
model.class_names = class_names
model.save("attack_classifier.keras")

with open("class_names.json", "w") as f:
    json.dump(class_names, f)

print("Malli ja luokkien nimet tallennettu!")

# Piirretään tulokset raporttia varten
plt.figure(figsize=(10, 4))

#  Accuracy
plt.subplot(1, 2, 1)
plt.plot(history.history["accuracy"], label="Train")
plt.plot(history.history["val_accuracy"], label="Val")
plt.title("Accuracy")
plt.xlabel("Epoch")
plt.ylabel("Tarkkuus")
plt.legend()

# Loss
plt.subplot(1, 2, 2)
plt.plot(history.history["loss"], label="Train")
plt.plot(history.history["val_loss"], label="Val")
plt.title("Loss")
plt.xlabel("Epoch")
plt.ylabel("Häviö")
plt.legend()

plt.tight_layout()
plt.savefig("training_results.png")
plt.show()
print("Malli koulutettu, visualisoitu ja tallennettu!")

y_pred_probs = model.predict(X_test)
y_pred = np.argmax(y_pred_probs, axis=1)

# Tulostetaan tekstimuotoinen raportti
# Tämä näyttää Precision, Recall ja F1-score arvot jokaiselle luokalle erikseen
print("\nLUOKITTELURAPORTTI:")
print(classification_report(y_test, y_pred, target_names=class_names))

# Luodaan ja piirretään confusion-matriisi
cm = confusion_matrix(y_test, y_pred)

plt.figure(figsize=(10, 8))
sns.heatmap(
    cm,
    annot=True,
    fmt="d",
    xticklabels=class_names,
    yticklabels=class_names,
    cmap="Blues",
)

plt.xlabel("Ennustettu luokka")
plt.ylabel("Todellinen luokka")
plt.title("Confusion Matrix")
plt.savefig("confusion_matrix.png")
plt.show()

print("Confusion matriisi tallennettu tiedostoon confusion_matrix.png")
