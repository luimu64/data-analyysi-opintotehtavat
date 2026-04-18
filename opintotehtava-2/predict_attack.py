import argparse
import ipaddress
import json

import numpy as np
import tensorflow as tf

# LATAUS
try:
    model = tf.keras.models.load_model("attack_classifier.keras")
    # Ladataan nimet tiedostosta
    with open("class_names.json", "r") as f:
        class_names = json.load(f)
except Exception as e:
    print(f"Virhe latauksessa: {e}")
    exit()


def analyze_traffic(ip, l_port, k_port):
    try:
        ip_n = int(ipaddress.IPv4Address(ip.strip()))
        input_data = np.array([[ip_n, l_port, k_port]], dtype="float32")

        preds = model.predict(input_data, verbose=0)
        idx = np.argmax(preds)
        conf = np.max(preds) * 100

        return class_names[idx], conf
    except Exception as e:
        return f"Virhe: {e}", 0


# KOMENTORIVI
parser = argparse.ArgumentParser()
parser.add_argument("ip", help="IP-osoite")
parser.add_argument("--lp", type=int, default=443)
parser.add_argument("--kp", type=int, default=80)

args = parser.parse_args()

# TULOS
tyyppi, varmuus = analyze_traffic(args.ip, args.lp, args.kp)

print("\n" + "=" * 40)
print(f"LIIKENNEANALYYSIN TULOS")
print(f"Kohde: {args.ip}:{args.kp}")
print(f"Luokittelu: {tyyppi} ({varmuus:.2f}% varmuus)")
print("=" * 40)
