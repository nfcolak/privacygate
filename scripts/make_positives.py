"""Deterministic synthetic POSITIVE PII augmentation (EN/DE/FR/IT/ES), train + dev only. Standard library only.

env -u PYTHONPATH python3 scripts/make_positives.py            # write data/augmentation/positive-{train,dev}.jsonl + artifacts/positive-data/manifest.json
env -u PYTHONPATH python3 scripts/make_positives.py --verify   # regenerate in memory; compare with manifest/files; run loader checks
Prints counts and hashes only; generated text is gitignored. Spans are built by string assembly (no find/replace).
Train and dev use disjoint template pools AND disjoint name/street/city/stem pools; code-like values are
rejected in dev if already used in train. There is no test split.
"""
import hashlib
import json
import random
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from privacygate import positive_data as pd

LANGS, VERSION = pd.LANGS, pd.GEN_VERSION
SEED = 20261002
OUT = {"train": ROOT / "data/augmentation/positive-train.jsonl", "dev": ROOT / "data/augmentation/positive-dev.jsonl"}
MANIFEST = ROOT / "artifacts/positive-data/manifest.json"
VARIANTS = {"train": 6, "dev": 4}  # rows per template
FAMILIES = ("names", "phone", "identity", "address", "username", "account", "personalref")
SLOT = {"G": "GIVENNAME", "S": "SURNAME", "PH": "TELEPHONENUM", "ID": "IDCARDNUM", "PP": "PASSPORTNUM",
        "DL": "DRIVERLICENSENUM", "ST": "STREET", "NO": "BUILDINGNUM", "ZP": "ZIPCODE", "CT": "CITY",
        "US": "USERNAME", "AC": "ACCOUNTNUM", "RF": "PERSONALREF"}

# T[family][lang] = (3 train templates, 2 dev templates). Fixed text has no digits; every variable is a slot.
T = {
 "names": {
  "en": (["My name is {G} {S}.", "The report was written by {G} {S} last spring.", "Please address the letter to {S}, {G}."],
         ["Hello, this is {G} {S} speaking.", "Thanks for waiting, {G}."]),
  "de": (["Mein Name ist {G} {S}.", "Der Bericht stammt von {G} {S}.", "Bitte adressieren Sie den Brief an {S}, {G}."],
         ["Hallo, hier spricht {G} {S}.", "Danke fürs Warten, {G}."]),
  "fr": (["Je m'appelle {G} {S}.", "Le rapport a été rédigé par {G} {S}.", "Merci d'adresser la lettre à {S}, {G}."],
         ["Bonjour, ici {G} {S}.", "Merci d'avoir attendu, {G}."]),
  "it": (["Mi chiamo {G} {S}.", "Il rapporto è stato scritto da {G} {S}.", "Si prega di indirizzare la lettera a {S}, {G}."],
         ["Buongiorno, sono {G} {S}.", "Grazie per l'attesa, {G}."]),
  "es": (["Me llamo {G} {S}.", "El informe fue escrito por {G} {S}.", "Dirija la carta a {S}, {G}."],
         ["Hola, habla {G} {S}.", "Gracias por esperar, {G}."]),
 },
 "phone": {
  "en": (["You can reach {G} {S} on {PH}.", "Call {PH} and ask for {G}.", "{S}, {G}: mobile {PH}"],
         ["{G} {S} gave us this number: {PH}.", "The phone of {G} {S} is {PH}, please call after lunch."]),
  "de": (["{G} {S} erreichen Sie unter {PH}.", "Rufen Sie {PH} an und fragen Sie nach {G}.", "{S}, {G}: Mobil {PH}"],
         ["{G} {S} hat uns diese Nummer gegeben: {PH}.", "Das Telefon von {G} {S} lautet {PH}, bitte rufen Sie nach dem Mittag an."]),
  "fr": (["Vous pouvez joindre {G} {S} au {PH}.", "Appelez le {PH} et demandez {G}.", "{S}, {G} : mobile {PH}"],
         ["{G} {S} nous a donné ce numéro : {PH}.", "Le téléphone de {G} {S} est le {PH}, merci d'appeler après midi."]),
  "it": (["Puoi contattare {G} {S} al numero {PH}.", "Chiama il {PH} e chiedi di {G}.", "{S}, {G}: cellulare {PH}"],
         ["{G} {S} ci ha dato questo numero: {PH}.", "Il telefono di {G} {S} è {PH}, chiamate dopo pranzo."]),
  "es": (["Puede llamar a {G} {S} al {PH}.", "Llame al {PH} y pregunte por {G}.", "{S}, {G}: móvil {PH}"],
         ["{G} {S} nos dio este número: {PH}.", "El teléfono de {G} {S} es el {PH}, llame después de comer."]),
 },
 "identity": {
  "en": (["The identity card of {G} {S} has the number {ID}.", "Passport {PP} was issued to {G} {S}.", "{G} {S} showed driver licence {DL} at the desk."],
         ["Applicant {G} {S}, passport number {PP}.", "Driver licence {DL} and ID card {ID} both belong to {G} {S}."]),
  "de": (["Der Personalausweis von {G} {S} hat die Nummer {ID}.", "Reisepass {PP} wurde auf {G} {S} ausgestellt.", "{G} {S} zeigte am Schalter den Führerschein {DL}."],
         ["Antragsteller {G} {S}, Reisepassnummer {PP}.", "Führerschein {DL} und Ausweis {ID} gehören beide {G} {S}."]),
  "fr": (["La carte d'identité de {G} {S} porte le numéro {ID}.", "Le passeport {PP} a été délivré à {G} {S}.", "{G} {S} a présenté le permis de conduire {DL} au guichet."],
         ["Demandeur {G} {S}, numéro de passeport {PP}.", "Le permis {DL} et la carte {ID} appartiennent tous deux à {G} {S}."]),
  "it": (["La carta d'identità di {G} {S} ha il numero {ID}.", "Il passaporto {PP} è stato rilasciato a {G} {S}.", "{G} {S} ha mostrato la patente {DL} allo sportello."],
         ["Richiedente {G} {S}, numero di passaporto {PP}.", "La patente {DL} e la carta {ID} appartengono entrambe a {G} {S}."]),
  "es": (["El documento de identidad de {G} {S} tiene el número {ID}.", "El pasaporte {PP} fue emitido a nombre de {G} {S}.", "{G} {S} mostró el carné de conducir {DL} en la ventanilla."],
         ["Solicitante {G} {S}, número de pasaporte {PP}.", "El carné {DL} y el documento {ID} pertenecen a {G} {S}."]),
 },
 "address": {
  "en": (["Please deliver the parcel to {G} {S}, {NO} {ST}, {CT} {ZP}.", "I live at {NO} {ST}, {CT} {ZP}.", "Sender: {G} {S}, {NO} {ST}, {CT} {ZP}"],
         ["Send the post to {S}, {G}, {NO} {ST}, {CT} {ZP}.", "The address of {G} {S} is {NO} {ST}, {CT} {ZP}."]),
  "de": (["Die Lieferung geht an {G} {S}, {ST} {NO}, {ZP} {CT}.", "Ich wohne unter der Adresse {ST} {NO}, {ZP} {CT}.", "Absender: {G} {S}, {ST} {NO}, {ZP} {CT}"],
         ["Bitte schicken Sie die Post an {S}, {G}, {ST} {NO}, {ZP} {CT}.", "Die Anschrift von {G} {S} lautet {ST} {NO}, {ZP} {CT}."]),
  "fr": (["Merci de livrer le colis à {G} {S}, {NO} {ST}, {ZP} {CT}.", "J'habite au {NO} {ST}, {ZP} {CT}.", "Expéditeur : {G} {S}, {NO} {ST}, {ZP} {CT}"],
         ["Envoyez le courrier à {S}, {G}, {NO} {ST}, {ZP} {CT}.", "L'adresse de {G} {S} est {NO} {ST}, {ZP} {CT}."]),
  "it": (["Consegnare il pacco a {G} {S}, {ST} {NO}, {ZP} {CT}.", "Abito in {ST} {NO}, {ZP} {CT}.", "Mittente: {G} {S}, {ST} {NO}, {ZP} {CT}"],
         ["Inviate la posta a {S}, {G}, {ST} {NO}, {ZP} {CT}.", "L'indirizzo di {G} {S} è {ST} {NO}, {ZP} {CT}."]),
  "es": (["Entregue el paquete a {G} {S}, {ST} {NO}, {ZP} {CT}.", "Vivo en {ST} {NO}, {ZP} {CT}.", "Remitente: {G} {S}, {ST} {NO}, {ZP} {CT}"],
         ["Envíen el correo a {S}, {G}, {ST} {NO}, {ZP} {CT}.", "La dirección de {G} {S} es {ST} {NO}, {ZP} {CT}."]),
 },
 "username": {
  "en": (["The forum account {US} belongs to {G} {S}.", "{G} {S} plays online under the handle {US}.", "Username of {G} {S}: {US}"],
         ["{G} {S} posts on the forum as {US}.", "The profile {US} was created by {G} {S}."]),
  "de": (["Das Forenkonto {US} gehört {G} {S}.", "{G} {S} spielt online unter dem Namen {US}.", "Benutzername von {G} {S}: {US}"],
         ["Unter dem Handle {US} schreibt {G} {S} im Forum.", "Das Profil {US} wurde von {G} {S} angelegt."]),
  "fr": (["Le compte du forum {US} appartient à {G} {S}.", "{G} {S} joue en ligne sous le pseudo {US}.", "Pseudo de {G} {S} : {US}"],
         ["{G} {S} écrit sur le forum sous {US}.", "Le profil {US} a été créé par {G} {S}."]),
  "it": (["L'account del forum {US} appartiene a {G} {S}.", "{G} {S} gioca online con il nome {US}.", "Nome utente di {G} {S}: {US}"],
         ["{G} {S} scrive sul forum come {US}.", "Il profilo {US} è stato creato da {G} {S}."]),
  "es": (["La cuenta del foro {US} pertenece a {G} {S}.", "{G} {S} juega en línea con el alias {US}.", "Nombre de usuario de {G} {S}: {US}"],
         ["{G} {S} escribe en el foro como {US}.", "El perfil {US} fue creado por {G} {S}."]),
 },
 "account": {
  "en": (["Membership number {AC} belongs to {G} {S}.", "Customer number {AC} is registered to {G} {S}.", "{G} {S}, library card {AC}"],
         ["For {G} {S}, the loyalty card is {AC}.", "The rewards account of {G} {S} has the number {AC}."]),
  "de": (["Die Mitgliedsnummer {AC} gehört zu {G} {S}.", "Kundennummer {AC} ist auf {G} {S} registriert.", "{G} {S}, Bibliotheksausweis {AC}"],
         ["Für {G} {S} lautet die Kundenkarte {AC}.", "Das Treuekonto von {G} {S} hat die Nummer {AC}."]),
  "fr": (["Le numéro d'adhérent {AC} appartient à {G} {S}.", "Le numéro client {AC} est enregistré au nom de {G} {S}.", "{G} {S}, carte de bibliothèque {AC}"],
         ["Pour {G} {S}, la carte de fidélité est {AC}.", "Le compte de fidélité de {G} {S} porte le numéro {AC}."]),
  "it": (["Il numero di tessera {AC} appartiene a {G} {S}.", "Il numero cliente {AC} è registrato a nome di {G} {S}.", "{G} {S}, tessera della biblioteca {AC}"],
         ["Per {G} {S}, la carta fedeltà è {AC}.", "L'account fedeltà di {G} {S} ha il numero {AC}."]),
  "es": (["El número de socio {AC} pertenece a {G} {S}.", "El número de cliente {AC} está registrado a nombre de {G} {S}.", "{G} {S}, carné de biblioteca {AC}"],
         ["Para {G} {S}, la tarjeta de fidelidad es {AC}.", "La cuenta de puntos de {G} {S} tiene el número {AC}."]),
 },
 "personalref": {
  "en": (["Order {RF} was placed by {G} {S}.", "Tracking code {RF} for the parcel addressed to {G} {S}.", "{G} {S}, your case reference {RF}"],
         ["The parcel of {G} {S} has tracking number {RF}.", "The file for {G} {S} carries reference {RF}."]),
  "de": (["Die Bestellung {RF} wurde von {G} {S} aufgegeben.", "Sendungsnummer {RF} für das Paket an {G} {S}.", "{G} {S}, Ihre Vorgangsnummer {RF}"],
         ["Das Paket von {G} {S} hat die Sendungsverfolgung {RF}.", "Zum Fall von {G} {S} gehört das Aktenzeichen {RF}."]),
  "fr": (["La commande {RF} a été passée par {G} {S}.", "Code de suivi {RF} pour le colis adressé à {G} {S}.", "{G} {S}, votre référence de dossier {RF}"],
         ["Le colis de {G} {S} a le numéro de suivi {RF}.", "Le dossier de {G} {S} porte la référence {RF}."]),
  "it": (["L'ordine {RF} è stato effettuato da {G} {S}.", "Codice di tracciamento {RF} per il pacco indirizzato a {G} {S}.", "{G} {S}, il suo riferimento pratica {RF}"],
         ["Il pacco di {G} {S} ha il numero di tracciamento {RF}.", "La pratica di {G} {S} riporta il riferimento {RF}."]),
  "es": (["El pedido {RF} fue realizado por {G} {S}.", "Código de seguimiento {RF} del paquete dirigido a {G} {S}.", "{G} {S}, su referencia de expediente {RF}"],
         ["El paquete de {G} {S} tiene el número de seguimiento {RF}.", "El expediente de {G} {S} lleva la referencia {RF}."]),
 },
}

# Invented, syllable-composed names; onsets are split-disjoint. Incidental coincidence with real names is possible.
GIVEN_ON = {"train": ["Mar", "Tal", "Bren", "Cor", "Eli", "Lan", "Ser", "Vil", "Dor", "Fen"],
            "dev": ["Nor", "Pel", "Kas", "Hal", "Ren", "Ost", "Jav", "Wen", "Ulr", "Yar"]}
GIVEN_END = {"en": ["ric", "wyn", "ley", "ton", "dra"], "de": ["hild", "mund", "bert", "ke", "lind"],
             "fr": ["ette", "ien", "aud", "ine", "elle"], "it": ["ino", "ella", "ardo", "etta", "io"],
             "es": ["ita", "ando", "ino", "illa", "ero"]}
SUR_ON = {"train": ["Brel", "Corv", "Dunsk", "Falv", "Gorm", "Harv", "Jask", "Kelb", "Lorv", "Marsk"],
          "dev": ["Nerv", "Orsk", "Pelv", "Quarn", "Rask", "Selv", "Torv", "Ulsk", "Varn", "Welk"]}
SUR_END = {"en": ["ford", "well", "son", "ham"], "de": ["mann", "berg", "feld", "hoff"],
           "fr": ["eau", "ot", "ier", "mont"], "it": ["elli", "oni", "ucci", "ato"], "es": ["ez", "ales", "ero", "ido"]}
STEMS = {"train": ["Alder", "Brindle", "Corvin", "Dunmore", "Elmcrest", "Fallow"],
         "dev": ["Gorsedale", "Hartwell", "Ivymoor", "Kestrel", "Lindhurst", "Marrow"]}
STREET_FMT = {"en": ["{} Street", "{} Lane", "{} Road", "{} Avenue"], "de": ["{}straße", "{}weg", "{}allee"],
              "fr": ["Rue {}", "Avenue {}", "Boulevard {}"], "it": ["Via {}", "Viale {}", "Piazza {}"],
              "es": ["Calle {}", "Avenida {}", "Plaza {}"]}
CITIES = {"train": {"en": ["Leeds", "Bristol", "Dundee", "Cardiff"], "de": ["Köln", "Bremen", "Leipzig", "Dresden"],
                    "fr": ["Lyon", "Nantes", "Lille", "Rennes"], "it": ["Torino", "Bologna", "Genova", "Verona"],
                    "es": ["Sevilla", "Valencia", "Zaragoza", "Bilbao"]},
          "dev": {"en": ["Norwich", "Exeter", "Bath", "Derby"], "de": ["Mainz", "Kiel", "Bonn", "Ulm"],
                  "fr": ["Dijon", "Tours", "Nîmes", "Metz"], "it": ["Parma", "Padova", "Trieste", "Bari"],
                  "es": ["Málaga", "Granada", "Murcia", "Alicante"]}}
HANDLE_STEMS = {"train": ["quietfox", "bluepine", "tallowlamp", "nightkite", "softgrain", "oldharbor"],
                "dev": ["mistwren", "copperleaf", "slowtide", "paperowl", "greenlatch", "wintermoth"]}
IBAN_CC = {"en": "GB", "de": "DE", "fr": "FR", "it": "IT", "es": "ES"}
UP = "ABCDEFGHJKLMNPRSTUVWXYZ"


def _digits(rng, n):
    return "".join(rng.choice("0123456789") for _ in range(n))


def _mod97(s):
    s = s[4:] + s[:4]
    return int("".join(str(int(c, 36)) for c in s)) % 97


def _phone(rng, lang):
    a, b = rng.randrange(1000), rng.randrange(100)
    c, d = rng.randrange(100), rng.randrange(10000)
    f = {"en": ["+44 7700 900{:03d}", "07700 900{:03d}"], "de": ["+49 30 23125{:03d}", "030 23125{:03d}"]}
    if lang in f:
        return rng.choice(f[lang]).format(a)
    if lang == "fr":
        return rng.choice(["+33 1 99 00 {:02d} {:02d}", "01 99 00 {:02d} {:02d}"]).format(b, c)
    if lang == "it":
        return rng.choice(["+39 06 555 {:04d}", "06 555 {:04d}"]).format(d)
    return rng.choice(["+34 91 555 {:02d} {:02d}", "91 555 {:02d} {:02d}"]).format(b, c)


def _ref(rng, lang, stats):
    style = rng.randrange(6)
    if style == 0:
        return "ORD-" + _digits(rng, 7)
    if style == 1:
        return "{}{}{}{}".format(rng.choice(UP), rng.choice(UP), _digits(rng, 9), rng.choice(UP) + rng.choice(UP))
    if style == 2:
        return "{}-{}-{}".format(_digits(rng, 4), _digits(rng, 4), _digits(rng, 2))
    if style == 3:
        return "{}{}".format(rng.choice(UP) + rng.choice(UP), _digits(rng, 10))
    if style == 4:
        return "REF/{}/{}".format(_digits(rng, 4), rng.choice(UP) + rng.choice(UP) + _digits(rng, 3))
    while True:  # IBAN-shaped string with an INVALID checksum, in a person-linked context: still a positive
        code = IBAN_CC[lang] + _digits(rng, 2) + _digits(rng, 18)
        if _mod97(code) != 1:
            stats["ref_ibanlike_invalid_checksum"] += 1
            return code


def _value(label, lang, split, rng, used, stats):
    """One synthetic value; `used` holds values already used in the other split (rejected when seen)."""
    for _ in range(1000):
        if label == "GIVENNAME":
            v = rng.choice(GIVEN_ON[split]) + rng.choice(GIVEN_END[lang])
        elif label == "SURNAME":
            v = rng.choice(SUR_ON[split]) + rng.choice(SUR_END[lang])
        elif label == "STREET":
            v = rng.choice(STREET_FMT[lang]).format(rng.choice(STEMS[split]))
        elif label == "BUILDINGNUM":
            return str(rng.randrange(1, 200)) + rng.choice(["", "", "", "a", "b"])
        elif label == "CITY":
            return rng.choice(CITIES[split][lang])
        elif label == "TELEPHONENUM":
            v = _phone(rng, lang)
        elif label == "ZIPCODE":
            v = ("{}{}{} {}{}{}".format(rng.choice(UP), rng.choice(UP), rng.randrange(1, 10), rng.randrange(1, 10), rng.choice(UP), rng.choice(UP))
                 if lang == "en" else _digits(rng, 5))
        elif label == "IDCARDNUM":
            v = rng.choice(UP) + _digits(rng, 2) + rng.choice(UP) + _digits(rng, 6)
        elif label == "PASSPORTNUM":
            v = rng.choice([rng.choice(UP) + _digits(rng, 8), rng.choice(UP) + rng.choice(UP) + _digits(rng, 7)])
        elif label == "DRIVERLICENSENUM":
            v = "{}{}-{}".format(rng.choice(UP), _digits(rng, 7), _digits(rng, 2))
        elif label == "USERNAME":
            v = rng.choice(HANDLE_STEMS[split]) + rng.choice(["", "_", "."]) + _digits(rng, rng.choice([2, 3]))
        elif label == "ACCOUNTNUM":
            v = rng.choice(["{}{}{}-{}".format(rng.choice(UP), rng.choice(UP), rng.choice(UP), _digits(rng, 6)), _digits(rng, 9),
                            "{}-{}".format(_digits(rng, 3), _digits(rng, 7))])
        else:  # PERSONALREF
            v = _ref(rng, lang, stats)
        if v not in used.get(label, ()):
            return v
    raise ValueError("value_space_exhausted")


def parse(tpl):
    out = []
    for p in re.split(r"(\{[A-Z]+\})", tpl):
        if p.startswith("{") and p.endswith("}"):
            out.append(("slot", SLOT[p[1:-1]]))
        elif p:
            out.append(("lit", p))
    return out


def assemble(tpl, values):
    """String assembly: offsets recorded while concatenating; a literal never contains a slot value."""
    text, mask = "", []
    for kind, v in parse(tpl):
        if kind == "lit":
            text += v
        else:
            val = values[v]
            mask.append({"start": len(text), "end": len(text) + len(val), "label": v})
            text += val
    return text, mask


def generate():
    rows, stats = [], {"ref_ibanlike_invalid_checksum": 0}
    used = {"train": {}, "dev": {}}  # label -> set of generated values per split
    for split, ti_range in (("train", range(3)), ("dev", range(2))):
        for fam in FAMILIES:
            for lang in LANGS:
                tpls = T[fam][lang][0] if split == "train" else T[fam][lang][1]
                for i, tpl in enumerate(tpls):
                    tid = "pos-{}-{}-{}{}".format(fam, lang, "t" if split == "train" else "d", i)
                    rng = random.Random("{}:{}:{}".format(SEED, VERSION, tid))
                    seen, n, guard = set(), 0, 0
                    labels = [v for k, v in parse(tpl) if k == "slot"]
                    while n < VARIANTS[split]:
                        guard += 1
                        if guard > 500:
                            raise ValueError("variant_space_exhausted")
                        vals = {}
                        for lab in labels:
                            vals[lab] = _value(lab, lang, split, rng, used["train"] if split == "dev" else {}, stats)
                        text, mask = assemble(tpl, vals)
                        if text in seen:
                            continue
                        seen.add(text)
                        for lab, v in vals.items():
                            used[split].setdefault(lab, set()).add(v)
                        rid = hashlib.sha256("{}:{}:{}".format(VERSION, tid, text).encode()).hexdigest()
                        rows.append({"row_id": rid, "language": lang, "source_text": text, "privacy_mask": mask,
                                     "template_id": tid, "split": split})
                        n += 1
    return {s: [r for r in rows if r["split"] == s] for s in ("train", "dev")}, stats, used


def template_set_hash():
    return hashlib.sha256(json.dumps([T, GIVEN_ON, GIVEN_END, SUR_ON, SUR_END, STEMS, STREET_FMT, CITIES, HANDLE_STEMS],
                                     sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def summarize(rows):
    pl, lab, fam, famlang, tm = {l: 0 for l in LANGS}, {}, {}, {}, {}
    for r in rows:
        pl[r["language"]] += 1
        f = r["template_id"].split("-")[1]
        fam[f] = fam.get(f, 0) + 1
        k = "{}/{}".format(f, r["language"])
        famlang[k] = famlang.get(k, 0) + 1
        tm[r["template_id"]] = tm.get(r["template_id"], 0) + 1
        for m in r["privacy_mask"]:
            lab[m["label"]] = lab.get(m["label"], 0) + 1
    return {"rows": len(rows), "per_language": pl, "per_label": dict(sorted(lab.items())),
            "per_family": dict(sorted(fam.items())), "per_family_language": dict(sorted(famlang.items())),
            "templates": len(tm), "rows_per_template": dict(sorted(tm.items())), "sha256": pd.content_hash(rows)}


def disjointness(splits):
    a, b = splits["train"], splits["dev"]
    skel = lambda s: {tpl for fam in T.values() for lang in fam.values() for tpl in lang[0 if s == "train" else 1]}
    return {"template_ids": not ({r["template_id"] for r in a} & {r["template_id"] for r in b}),
            "template_strings": not (skel("train") & skel("dev")),
            "row_ids": not ({r["row_id"] for r in a} & {r["row_id"] for r in b}),
            "exact_texts": not ({(r["language"], r["source_text"]) for r in a} & {(r["language"], r["source_text"]) for r in b}),
            "name_pools": all(not ({o + e for o in GIVEN_ON["train"] for e in GIVEN_END[l]} & {o + e for o in GIVEN_ON["dev"] for e in GIVEN_END[l]})
                              and not ({o + e for o in SUR_ON["train"] for e in SUR_END[l]} & {o + e for o in SUR_ON["dev"] for e in SUR_END[l]})
                              for l in LANGS),
            "street_stems_cities_handles": not (set(STEMS["train"]) & set(STEMS["dev"])) and not (set(HANDLE_STEMS["train"]) & set(HANDLE_STEMS["dev"]))
                              and all(not (set(CITIES["train"][l]) & set(CITIES["dev"][l])) for l in LANGS)}


def manifest_of(splits, stats):
    tmpl_pool = {s: sum(len(T[f][l][0 if s == "train" else 1]) for f in FAMILIES for l in LANGS) for s in ("train", "dev")}
    return {
        "generator_version": VERSION, "seed": SEED, "template_set_sha256": template_set_hash(),
        "variants_per_template": VARIANTS, "template_pool_sizes": tmpl_pool,
        "families": {"core": ["names", "phone", "identity", "address"], "new_proposed": ["username", "account", "personalref"]},
        "labels": {"existing_exact": list(pd.CORE_LABELS), "new_proposed": list(pd.NEW_LABELS)},
        "files": {s: "data/augmentation/positive-{}.jsonl".format(s) for s in ("train", "dev")},
        "splits": {s: summarize(splits[s]) for s in ("train", "dev")},
        "disjoint": disjointness(splits),
        "ref_ibanlike_invalid_checksum_rows": stats["ref_ibanlike_invalid_checksum"],
        "note": "synthetic; text not committed; no test split; all identifiers are invented and are not verified real or "
                "non-real; USERNAME/ACCOUNTNUM/PERSONALREF are initial proposed operational labels, not a taxonomy or legal "
                "classification; no trained support; health/narrative/biometric coverage remains open",
    }


def _expect_reject(raw, code, **kw):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "x.jsonl"
        p.write_bytes(raw)
        try:
            pd.load_positive_file(p, **kw)
        except ValueError as e:
            return str(e) == code and "pos_" in str(e)
    return False


def synthetic_checks(splits):
    row = dict(splits["train"][0])
    def one(**ch):
        r = json.loads(json.dumps(row)); r.update(ch); return (json.dumps(r) + "\n").encode()
    m = row["privacy_mask"][0]
    def with_mask(mask):
        return one(privacy_mask=mask)
    n = len(row["source_text"])
    checks = {
        "dev_rejected_in_train_mode": _expect_reject(pd.dumps(splits["dev"][:1]).encode(), "pos_split_mismatch"),
        "train_rejected_in_dev_mode": _expect_reject(pd.dumps(splits["train"][:1]).encode(), "pos_split_mismatch", allowed_split="dev"),
        "bool_offset": _expect_reject(with_mask([{"start": True, "end": m["end"], "label": m["label"]}]), "pos_mask_type"),
        "out_of_bounds": _expect_reject(with_mask([{"start": 0, "end": n + 1, "label": m["label"]}]), "pos_span_bounds"),
        "negative_start": _expect_reject(with_mask([{"start": -1, "end": 2, "label": m["label"]}]), "pos_span_bounds"),
        "empty_span": _expect_reject(with_mask([{"start": 2, "end": 2, "label": m["label"]}]), "pos_span_bounds"),
        "overlap": _expect_reject(with_mask([{"start": 0, "end": 3, "label": "CITY"}, {"start": 2, "end": 5, "label": "STREET"}]), "pos_span_overlap"),
        "unknown_label": _expect_reject(with_mask([{"start": 0, "end": 2, "label": "OTHER"}]), "pos_label"),
        "copied_value_key": _expect_reject(with_mask([{"start": 0, "end": 2, "label": "CITY", "value": "x"}]), "pos_mask_schema"),
        "extra_row_key": _expect_reject(one(extra=1), "pos_schema"),
        "empty_mask": _expect_reject(with_mask([]), "pos_annotation_count"),
        "forbidden_id": _expect_reject(one(), "pos_row_id", forbid_ids=(row["row_id"],)),
        "unparseable": _expect_reject(b"{not json\n", "pos_unparseable"),
        "bad_allowed_split": _expect_reject(one(), "pos_bad_allowed_split", allowed_split="test"),
    }
    # an error must not echo text/offset/label content
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "x.jsonl"; p.write_bytes(with_mask([{"start": 0, "end": n + 7, "label": "CITY"}]))
        try:
            pd.load_positive_file(p)
        except ValueError as e:
            checks["error_value_free"] = row["source_text"][:8] not in str(e) and str(n + 7) not in str(e)
    return checks


def main():
    splits, stats, _ = generate()
    for s in splits:
        pd.check_rows(splits[s], s)
    man = manifest_of(splits, stats)
    if "--verify" in sys.argv:
        bad = []
        if not all(OUT[s].is_file() for s in OUT) or not MANIFEST.is_file():
            print("VERIFY FAIL: missing output or manifest"); return 1
        if json.loads(MANIFEST.read_text()) != man:
            bad.append("manifest differs from regeneration")
        for s in OUT:
            rows, b = pd.load_positive_file(OUT[s], allowed_split=s)
            if b["sha256"] != man["splits"][s]["sha256"] or pd.content_hash(rows) != man["splits"][s]["sha256"]:
                bad.append("{} file hash differs".format(s))
            if rows != splits[s]:
                bad.append("{} rows differ from regeneration".format(s))
            for r in rows:  # no literal text may contain digits => every variable value is inside a slot span
                if not r["privacy_mask"]:
                    bad.append("unannotated row")
            if (b["per_label"] != man["splits"][s]["per_label"]) or (b["per_language"] != man["splits"][s]["per_language"]):
                bad.append("{} binding counts differ".format(s))
            for lab in pd.LABELS:
                if lab not in b["per_label"]:
                    bad.append("{} lacks label {}".format(s, lab))
            for f in FAMILIES:
                for l in LANGS:
                    if man["splits"][s]["per_family_language"].get("{}/{}".format(f, l), 0) < 2:
                        bad.append("{} family/language gap".format(s))
        if not all(man["disjoint"].values()):
            bad.append("split isolation failed")
        for fam in T.values():
            for lang in fam.values():
                for tpl in lang[0] + lang[1]:
                    if any(c.isdigit() for k, v in parse(tpl) if k == "lit" for c in v):
                        bad.append("digit in template literal")
        try:
            pd.load_positive_file(OUT["dev"])
            bad.append("dev accepted in default train mode")
        except ValueError:
            pass
        chk = synthetic_checks(splits)
        bad += ["synthetic check failed: " + k for k, v in chk.items() if not v]
        if bad:
            print("VERIFY FAIL: " + "; ".join(sorted(set(bad)))); return 1
        print("VERIFY OK train_rows={} dev_rows={} train_sha256={} dev_sha256={} synthetic_checks={}".format(
            man["splits"]["train"]["rows"], man["splits"]["dev"]["rows"], man["splits"]["train"]["sha256"],
            man["splits"]["dev"]["sha256"], len(chk)))
        return 0
    OUT["train"].parent.mkdir(parents=True, exist_ok=True); MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    for s in OUT:
        OUT[s].write_text(pd.dumps(splits[s]))
    MANIFEST.write_text(json.dumps(man, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    print("WROTE train_rows={} dev_rows={} train_sha256={} dev_sha256={}".format(
        man["splits"]["train"]["rows"], man["splits"]["dev"]["rows"], man["splits"]["train"]["sha256"], man["splits"]["dev"]["sha256"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
