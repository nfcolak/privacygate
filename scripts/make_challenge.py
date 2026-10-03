"""Deterministic synthetic IBAN / decoy / clean challenge set (EN, DE, FR, IT, ES). Standard library only.

python3 scripts/make_challenge.py            # write data/challenge/{dev,test}.jsonl + docs/challenge/manifest.json
python3 scripts/make_challenge.py --verify   # regenerate in memory, compare to manifest and files on disk
Prints counts and hashes only. Dev and test use disjoint template pools.
"""
import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from privacygate.detect import detect, iban_valid  # noqa: E402

SEED = 20261001
N = {"iban": 100, "iban_decoy": 40, "clean": 100}
LANGS = ["en", "de", "fr", "it", "es"]
SPLITS = ["dev", "test"]

# ---- templates: T[stratum][split][lang] -> list. {X} = the code (IBAN / decoy / none); {N} number; {P} price; {V} version
T = {"iban": {"dev": {
    "en": ["Please transfer the deposit to {X} by Friday.", "My account for the refund is {X}, thanks.",
           "Payment details: beneficiary account {X}.", "The invoice will be settled from {X} next week.", "Could you confirm that {X} is the right account?"],
    "de": ["Bitte überweisen Sie die Kaution auf {X} bis Freitag.", "Mein Konto für die Rückzahlung lautet {X}.",
           "Zahlungsdaten: Empfängerkonto {X}.", "Die Rechnung wird von {X} beglichen.", "Können Sie bestätigen, dass {X} stimmt?"],
    "fr": ["Merci de virer la caution sur {X} avant vendredi.", "Mon compte pour le remboursement est {X}.",
           "Coordonnées de paiement : compte bénéficiaire {X}.", "La facture sera réglée depuis {X}.", "Pouvez-vous confirmer que {X} est correct ?"],
    "it": ["Si prega di versare la caparra su {X} entro venerdì.", "Il mio conto per il rimborso è {X}.",
           "Dati di pagamento: conto beneficiario {X}.", "La fattura sarà saldata da {X}.", "Può confermare che {X} è corretto?"],
    "es": ["Por favor transfiera la fianza a {X} antes del viernes.", "Mi cuenta para el reembolso es {X}.",
           "Datos de pago: cuenta beneficiaria {X}.", "La factura se pagará desde {X}.", "¿Puede confirmar que {X} es correcto?"]},
    "test": {
    "en": ["Wire the membership fee to {X} please.", "Our company pays salaries from {X} each month.", "IBAN for the donation: {X}",
           "I changed banks, so use {X} from now on.", "Standing order set up to {X} starting in March."],
    "de": ["Überweisen Sie bitte den Mitgliedsbeitrag an {X}.", "Wir zahlen die Gehälter monatlich von {X}.", "IBAN für die Spende: {X}",
           "Ich habe die Bank gewechselt, bitte nutzen Sie {X}.", "Dauerauftrag an {X} ab März eingerichtet."],
    "fr": ["Veuillez virer la cotisation sur {X}.", "Nous payons les salaires chaque mois depuis {X}.", "IBAN pour le don : {X}",
           "J'ai changé de banque, utilisez désormais {X}.", "Virement permanent vers {X} à partir de mars."],
    "it": ["Versi la quota associativa su {X}, grazie.", "Paghiamo gli stipendi ogni mese da {X}.", "IBAN per la donazione: {X}",
           "Ho cambiato banca, usi ora {X}.", "Bonifico periodico verso {X} da marzo."],
    "es": ["Ingrese la cuota de socio en {X}, gracias.", "Pagamos los sueldos cada mes desde {X}.", "IBAN para la donación: {X}",
           "Cambié de banco, use ahora {X}.", "Orden permanente a {X} a partir de marzo."]}},
    "iban_decoy": {"dev": {
    "en": ["Your order reference is {X}, keep it for support.", "Tracking number {X} was scanned at the depot.", "Please quote code {X} in your reply.", "Serial {X} is printed on the back."],
    "de": ["Ihre Bestellnummer lautet {X}, bitte aufbewahren.", "Sendungsnummer {X} wurde im Depot gescannt.", "Bitte nennen Sie den Code {X} in Ihrer Antwort.", "Die Seriennummer {X} steht auf der Rückseite."],
    "fr": ["Votre référence de commande est {X}, à conserver.", "Le colis {X} a été scanné au dépôt.", "Merci d'indiquer le code {X} dans votre réponse.", "Le numéro de série {X} figure au dos."],
    "it": ["Il suo riferimento d'ordine è {X}, lo conservi.", "Il pacco {X} è stato scansionato al deposito.", "Indichi il codice {X} nella risposta.", "Il numero di serie {X} è sul retro."],
    "es": ["Su referencia de pedido es {X}, guárdela.", "El paquete {X} fue escaneado en el almacén.", "Indique el código {X} en su respuesta.", "El número de serie {X} está en la parte trasera."]},
    "test": {
    "en": ["Ticket {X} has been escalated to level two.", "The parcel with ID {X} left the warehouse.", "License key batch {X} is now available.", "Reference {X} appears on the delivery note."],
    "de": ["Ticket {X} wurde an die zweite Stufe eskaliert.", "Das Paket mit der ID {X} hat das Lager verlassen.", "Die Lizenzcharge {X} ist jetzt verfügbar.", "Die Referenz {X} steht auf dem Lieferschein."],
    "fr": ["Le ticket {X} a été remonté au niveau deux.", "Le colis d'identifiant {X} a quitté l'entrepôt.", "Le lot de licences {X} est disponible.", "La référence {X} figure sur le bon de livraison."],
    "it": ["Il ticket {X} è stato passato al secondo livello.", "Il pacco con ID {X} ha lasciato il magazzino.", "Il lotto di licenze {X} è disponibile.", "Il riferimento {X} è sulla bolla di consegna."],
    "es": ["El ticket {X} se escaló al segundo nivel.", "El paquete con ID {X} salió del almacén.", "El lote de licencias {X} ya está disponible.", "La referencia {X} aparece en el albarán."]}},
    "clean": {"dev": {
    "en": ["The weather will stay cloudy with {N} mm of rain on Tuesday.", "This blender costs {P} and has {N} speed settings.", "The meeting room fits {N} people and has a projector.",
           "Please update to version {V} before the demo.", "Great launch day! #teamwork #{V}", "See you @ the office kitchen at noon."],
    "de": ["Das Wetter bleibt am Dienstag bewölkt mit {N} mm Regen.", "Dieser Mixer kostet {P} und hat {N} Stufen.", "Der Besprechungsraum bietet Platz für {N} Personen.",
           "Bitte aktualisieren Sie vor der Demo auf Version {V}.", "Toller Starttag! #teamwork #{V}", "Wir sehen uns @ Büroküche um zwölf."],
    "fr": ["Le temps restera nuageux avec {N} mm de pluie mardi.", "Ce mixeur coûte {P} et a {N} vitesses.", "La salle de réunion accueille {N} personnes.",
           "Merci de passer à la version {V} avant la démo.", "Belle journée de lancement ! #equipe #{V}", "Rendez-vous @ la cuisine du bureau à midi."],
    "it": ["Il tempo resterà nuvoloso con {N} mm di pioggia martedì.", "Questo frullatore costa {P} e ha {N} velocità.", "La sala riunioni ospita {N} persone.",
           "Aggiorni alla versione {V} prima della demo.", "Ottimo giorno di lancio! #squadra #{V}", "Ci vediamo @ cucina dell'ufficio a mezzogiorno."],
    "es": ["El tiempo seguirá nublado con {N} mm de lluvia el martes.", "Esta batidora cuesta {P} y tiene {N} velocidades.", "La sala de reuniones admite {N} personas.",
           "Actualice a la versión {V} antes de la demo.", "¡Gran día de lanzamiento! #equipo #{V}", "Nos vemos @ la cocina de la oficina a mediodía."]},
    "test": {
    "en": ["Sunny spells expected, with a high of {N} degrees.", "The new chair is priced at {P} and ships in {N} days.", "Printer on floor {N} is out of paper again.",
           "Release {V} fixes the scrolling issue.", "Quarterly town hall was fun #{V} #office", "Stand-up moved @ room {N} tomorrow."],
    "de": ["Sonnige Abschnitte, Höchstwert {N} Grad.", "Der neue Stuhl kostet {P} und wird in {N} Tagen geliefert.", "Der Drucker im Stock {N} hat wieder kein Papier.",
           "Release {V} behebt das Scroll-Problem.", "Das Quartalsmeeting war toll #{V} #büro", "Stand-up morgen @ Raum {N} verschoben."],
    "fr": ["Éclaircies attendues, maximum de {N} degrés.", "La nouvelle chaise coûte {P} et est livrée en {N} jours.", "L'imprimante de l'étage {N} n'a plus de papier.",
           "La version {V} corrige le problème de défilement.", "La réunion trimestrielle était sympa #{V} #bureau", "Stand-up déplacé @ salle {N} demain."],
    "it": ["Previste schiarite, massima di {N} gradi.", "La nuova sedia costa {P} e arriva in {N} giorni.", "La stampante al piano {N} è di nuovo senza carta.",
           "La versione {V} risolve il problema di scorrimento.", "La riunione trimestrale era divertente #{V} #ufficio", "Stand-up spostato @ sala {N} domani."],
    "es": ["Se esperan claros, con máxima de {N} grados.", "La silla nueva cuesta {P} y llega en {N} días.", "La impresora de la planta {N} no tiene papel otra vez.",
           "La versión {V} corrige el problema de desplazamiento.", "La reunión trimestral fue genial #{V} #oficina", "Stand-up movido @ sala {N} mañana."]}}}

# ---- IBAN generation
SPEC = {"DE": (22, "n"), "FR": (27, "n"), "IT": (27, "i"), "ES": (24, "n"), "CH": (21, "n"), "GB": (22, "g"), "NL": (18, "l")}
UP = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def check_digits(cc, bban):
    r = bban + cc + "00"
    return "{:02d}".format(98 - int("".join(str(int(c, 36)) for c in r)) % 97)


def make_iban(rng, cc=None):
    cc = cc or rng.choice(sorted(SPEC))
    n, kind = SPEC[cc]
    body = n - 4
    dig = lambda k: "".join(rng.choice("0123456789") for _ in range(k))
    let = lambda k: "".join(rng.choice(UP) for _ in range(k))
    bban = {"n": dig(body), "i": let(1) + dig(body - 1), "g": let(4) + dig(body - 4), "l": let(4) + dig(body - 4)}[kind]
    iban = cc + check_digits(cc, bban) + bban
    assert iban_valid(iban) and len(iban) == n
    return iban


def fmt(rng, iban):
    return " ".join(iban[i:i + 4] for i in range(0, len(iban), 4)) if rng.random() < 0.5 else iban


def make_decoy(rng):
    k = rng.randrange(4)
    if k == 0:  # IBAN-shaped, checksum broken (single-character change is always detected by mod 97)
        iban = make_iban(rng)
        i = rng.randrange(4, len(iban))
        bad = iban[:i] + rng.choice([c for c in "0123456789" if c != iban[i]]) + iban[i + 1:] if iban[i].isdigit() else iban
        if bad == iban:
            bad = iban[:-1] + str((int(iban[-1]) + 1) % 10)
        bad = fmt(rng, bad)
    elif k == 1:
        bad = "ORD-{}-{}".format(rng.randrange(2020, 2030), "".join(rng.choice(UP + "0123456789") for _ in range(8)))
    elif k == 2:
        bad = "1Z" + "".join(rng.choice(UP + "0123456789") for _ in range(16))
    else:
        bad = "".join(rng.choice(UP + "0123456789") for _ in range(rng.randrange(14, 24)))
    return bad


def fill(tpl, rng, x=""):
    return (tpl.replace("{X}", x).replace("{N}", str(rng.randrange(2, 90))).replace("{P}", "{}.{:02d} EUR".format(rng.randrange(5, 400), rng.randrange(100)))
            .replace("{V}", "v{}.{}.{}".format(rng.randrange(1, 9), rng.randrange(0, 20), rng.randrange(0, 30))))


def generate(split):
    rows = []
    for lang in LANGS:
        for stratum, count in N.items():
            rng = random.Random("{}:{}:{}:{}".format(SEED, split, lang, stratum))
            pool = T[stratum][split][lang]
            for i in range(count):
                tpl = rng.choice(pool)
                spans = []
                if stratum == "iban":
                    code = fmt(rng, make_iban(rng, sorted(SPEC)[i % len(SPEC)]))
                    text = fill(tpl, rng, code)
                    s = text.index(code)
                    spans = [{"start": s, "end": s + len(code), "label": "IBAN"}]
                else:
                    while True:
                        code = make_decoy(rng) if stratum == "iban_decoy" else ""
                        text = fill(tpl, rng, code)
                        if not detect(text):  # decoys/clean must be negatives for the regex by construction
                            break
                rows.append({"id": "{}-{}-{}-{:03d}".format(split, lang, stratum, i), "lang": lang, "stratum": stratum, "text": text, "spans": spans})
    return rows


def dumps(rows):
    return "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows).encode("utf-8")


def build():
    files, counts = {}, {}
    for split in SPLITS:
        rows = generate(split)
        files[split] = dumps(rows)
        c = {}
        for r in rows:
            c.setdefault(r["lang"], {}).setdefault(r["stratum"], 0)
            c[r["lang"]][r["stratum"]] += 1
        counts[split] = c
    man = {"seed": SEED, "generator": "scripts/make_challenge.py", "strata_per_lang_per_split": N, "counts": counts,
           "sha256": {s: hashlib.sha256(b).hexdigest() for s, b in files.items()},
           "iban_countries": sorted(SPEC), "note": "synthetic; text not committed; dev/test template pools disjoint"}
    return files, man


def main():
    files, man = build()
    mpath = ROOT / "docs/challenge/manifest.json"
    if "--verify" in sys.argv:
        ok = json.loads(mpath.read_text()) == man
        for s, b in files.items():
            p = ROOT / "data/challenge/{}.jsonl".format(s)
            ok = ok and p.is_file() and p.read_bytes() == b
        print("VERIFY OK" if ok else "VERIFY FAILED", man["sha256"])
        return 0 if ok else 1
    (ROOT / "data/challenge").mkdir(parents=True, exist_ok=True)
    mpath.parent.mkdir(parents=True, exist_ok=True)
    for s, b in files.items():
        (ROOT / "data/challenge/{}.jsonl".format(s)).write_bytes(b)
    mpath.write_text(json.dumps(man, indent=2, sort_keys=True) + "\n")
    print(man["sha256"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
