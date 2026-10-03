#!/usr/bin/env python3
"""One small stdlib proof on invented strings, or one offline v1 information run.

No input text, values, row identifiers, offsets or exception details are printed.
The optional v1 run copies only the explicitly supplied, non-blind v1 file into
ignored data/ before model inference; it never opens v3/v4 or a test split.
"""
import argparse
import copy
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from privacygate.address import MAX_REGION_CHARS, assemble


# Hand-invented compositions, not samples from any dataset/address database.
ADDRESSES = {
    "en": (
        "12 Zélmar Lane, flat 7B, VQ1 2ZX Vezford, United Kingdom",
        "Zélmar Road 12-14, apt 4C; 4821 QZ Vezdam, Netherlands",
        "c/o Dr. Qéz N. Vezorn\n14 Zélmar Street\nVQ2 3XZ Vezford\nUnited Kingdom",
        "PO Box 812\nVezville, TX 73145-1203\nUSA",
        "United Kingdom, Vezford VQ3 4ZX, 22 Zélmar Avenue",
        "16 Zélmar Rd.\n2nd floor\n4812 Vezbruck\nAustria",
        "P.O. Box 713, 4821 QZ Vezdam, Netherlands",
        "care of Qev Lanorn, suite 6, 18 Zev Lane, 73146 Vezville, USA",
        "18a Zélmar Way, unit C, VQ4 5ZX Vezford, United Kingdom",
        "Zélmar Drive 21 / building B, floor 3, 4813 Vezbruck, Austria",
    ),
    "de": (
        "Qélmarstraße 12a, Whg. 7B, 73145 Vezlingen, Deutschland",
        "12-14 Qélmarweg, 2. Stock, 4812 Vezbruck, Österreich",
        "c/o Herr Qév Vezorn\nQélmarplatz 14\nCH-8312 Vezwil\nSchweiz",
        "Postfach 811, 73146 Vezlingen, Deutschland",
        "Schweiz, Vezwil 8313, Qélmargasse 15, Wohnung 6",
        "Qélmarstr. 12bis, Hinterhaus 2, 73147 Vezlingen, Deutschland",
        "Qélmarplatz 7, Etg. 2, 8314 Vezwil, Schweiz",
        "Qélmargasse 8, 2. OG, 4813 Vezbruck, Österreich",
        "Am Qélmar Weg 12, Wohnung 4B, 73148 Vezlingen, Deutschland",
        "Postfach 913\r\n8315 Vezwil\r\nSchweiz",
    ),
    "fr": (
        "rue de Qélmar 12bis, appartement 7C, 75 001 Vézonne, France",
        "12 rue de Qélmar, 2e étage, 75002 Vézonne, France",
        "Boîte postale 812, 75003 Vézonne, France",
        "BP 813\n75004 Vézonne CEDEX 09\nFrance",
        "c/o Mme Qéva Vezorn\nrue Qélmar 14\n8312 Vézwil\nSuisse",
        "France, Vézonne 75005, avenue de Qélmar 18a",
        "avenue Qélmar 12-14, 3e étage, bâtiment C, escalier 2, 75006 Vézonne, France",
        "bd. Qélmar 8, appartement 2B, 4812 Vézbruck, Autriche",
        "chez Qéva Vezorn, rue Qélmar 9, 7314 Vézbel, Belgique",
        "16 rue Qélmar\nrez-de-chaussée\n75007 Vézonne\nFrance",
    ),
    "it": (
        "via Qélmar 12a, interno 7B, 73145 Vezonia, Italia",
        "12 via del Qélmar, piano secondo, 73146 Vezonia, Italia",
        "Casella postale 812, 73147 Vezonia, Italia",
        "C.P. 813\n73148 Vezonia\nItalia",
        "c/o Sig.ra Qéva Vezorn\nviale Qélmar 14\n8312 Vezwil\nSvizzera",
        "Italia, Vezonia 73149, piazza Qélmar 15",
        "corso Qélmar 12-14, scala B, piano 3, interno 4C, 73150 Vezonia (VQ), Italia",
        "viale Qélmar 8bis, palazzina C, 4812 Vezbruck, Austria",
        "presso Qéva Vezorn, via Qélmar 9, 73151 Vezonia, Italia",
        "16 piazza Qélmar\nprimo piano\n73152 Vezonia\nItalia",
    ),
    "es": (
        "calle de Qélmar 12a, piso 7, puerta B, 73145 Vezonia, España",
        "12 calle Qélmar, 2º B, 73146 Vezonia, España",
        "Apartado de correos 812, 73147 Vezonia, España",
        "Apdo. 813\n73148 Vezonia\nEspaña",
        "c/o Sr. Qév Vezorn\navenida Qélmar 14\n8312 Vezwil\nSuiza",
        "España, Vezonia 73149, plaza Qélmar 15",
        "c/ Qélmar 12-14, piso 3, puerta C, escalera 2, 73150 Vezonia, España",
        "avda. Qélmar 8bis, apartamento 2B, 4812 Vezbruck, Austria",
        "a la atención de Qéva Vezorn, calle Qélmar 9, 73151 Vezonia, España",
        "16 avenida Qélmar\n3º derecha\n73152 Vezonia\nEspaña",
    ),
}
NON_ADDRESSES = (
    "Vezford has a public museum.",
    "Order 4821 is manufactured in Vezdam.",
    "The meeting date is 2026-10-03 in Vezford.",
    "Room 12 is reserved for an exhibition.",
    "The product measures 12-14 cm and weighs 75 grams.",
    "Qélmar Lane is a public place mentioned in a travel article.",
    "Vezlingen hat ein öffentliches Museum.",
    "Produkt 73145 ist lieferbar.",
    "Der Termin ist am 03.10.2026 in Vezwil.",
    "Zimmer 12, Stock 2, ist ein öffentlicher Ausstellungsraum.",
    "73145 Vezlingen: öffentliche Wettervorhersage.",
    "Der Qélmarplatz liegt in einem öffentlichen Park.",
    "Vézonne possède un musée public.",
    "Le produit BP 812 est une pièce mécanique.",
    "La réunion est le 03/10/2026 à Vézonne.",
    "Chambre 12 au troisième étage du musée.",
    "75001 Vézonne figure dans la prévision météo.",
    "La rue Qélmar est mentionnée dans un guide public.",
    "Vezonia ha un museo pubblico.",
    "Il prodotto C.P. 813 è una componente meccanica.",
    "La riunione è il 03/10/2026 a Vezonia.",
    "Stanza 12 al secondo piano del museo.",
    "73145 Vezonia compare nelle previsioni del tempo.",
    "La piazza Qélmar è un luogo pubblico.",
    "Vezonia tiene un museo público.",
    "El producto Apdo. 813 es una pieza mecánica.",
    "La reunión es el 03/10/2026 en Vezonia.",
    "Habitación 12, piso 2, del museo público.",
    "73145 Vezonia aparece en el pronóstico del tiempo.",
    "La plaza Qélmar es un lugar público.",
)


def seed(start, end, label):
    return {
        "start": start, "end": end, "label": label, "source": "mbert",
        "score": 0.8, "validation": "unknown", "context": "unknown",
        "protected": False, "stage": "raw",
    }


def contains(cands, start, end):
    return any(c["start"] <= start and c["end"] >= end for c in cands)


def covered(cands, start, end):
    cursor = start
    for cand in sorted(cands, key=lambda c: (c["start"], c["end"])):
        if cand["end"] <= cursor:
            continue
        if cand["start"] > cursor:
            break
        cursor = max(cursor, cand["end"])
    return cursor >= end


def mixed_cases():
    """Five languages, five one-line layouts each, plus explicit recipients."""
    from privacygate.pipeline import _address_union
    from privacygate.spans import union

    invented = (
        ("Dr. Qéra Vezorn", "12 Zélmar Lane, VQ1 2ZX Vezford", "+44 1632 960123", "Phone", "mail", "c/o"),
        ("Dr. Qéva Vezorn", "Qélmarstraße 12, 73145 Vezlingen", "+49 30 00001234", "Tel.", "E-Mail", "z. Hd."),
        ("Mme Qélia Vezorn", "rue Qélmar 12, 75001 Vézonne", "+33 1 00001234", "tél.", "courriel", "à l'attention de"),
        ("Sig.ra Qélina Vezorn", "via Qélmar 12, 73145 Vezonia", "+39 06 00001234", "cell.", "mail", "presso"),
        ("Sra. Qélara Vezorn", "calle Qélmar 12, 73145 Vezonia", "+34 91 0001234", "Teléfono", "correo", "a la atención de"),
    )
    exact = total = care_exact = 0
    contract_ok = True
    for name, address, phone, phone_cue, email_cue, care_cue in invented:
        n, a = (name, "PERSONNAME"), (address, "ADDRESS")
        p, e = (phone, "TELEPHONENUM"), ("qev@invented.invalid", "EMAIL")
        layouts = (
            ("Name: ", n, ", ", a, ", " + phone_cue + " ", p),
            (a, "; Name: ", n, "; " + email_cue + " ", e),
            (email_cue + " ", e, "; Name: ", n, "; ", a),
            ("Name: ", n, "; " + phone_cue + " ", p, "; ", a, "; " + email_cue + " ", e),
            ("Name: ", n, ", ", a, ", ", p, ", ", e),
        )
        for parts in layouts:
            text, expected, seeds = "", [], []
            for part in parts:
                if isinstance(part, str):
                    text += part
                    continue
                value, label = part
                start = len(text)
                text += value
                expected.append({"start": start, "end": len(text), "label": label})
                if label != "ADDRESS":
                    seeds.append(seed(start, len(text), label))
            before = copy.deepcopy(seeds)
            found = assemble(text, seeds)
            result = _address_union(text, seeds + found)
            total += 1
            exact += result == expected
            contract_ok &= seeds == before
            # Simulate the real failure: one model ADDRESS envelopes all values.
            # Semantic boundaries may retain already-masked cue/separator chars,
            # but not one character from the old union may become exposed.
            broad = seed(expected[0]["start"], expected[-1]["end"], "ADDRESS")
            ledger = seeds + found + [broad]
            split = _address_union(text, ledger)
            old_mask = {i for c in union(ledger) for i in range(c["start"], c["end"])}
            new_mask = {i for c in split for i in range(c["start"], c["end"])}
            contract_ok &= old_mask == new_mask
            contract_ok &= all(any(c["label"] == gold["label"]
                                   and c["start"] <= gold["start"] and gold["end"] <= c["end"]
                                   for c in split) for gold in expected)
            contract_ok &= all(not any(c["start"] < gold["end"] and gold["start"] < c["end"]
                                      for gold in expected if gold["label"] != "ADDRESS")
                               for c in found)
        care = care_cue + " " + name + ", " + address
        text = care + ", " + phone_cue + " " + phone
        recipient = seed(len(care_cue) + 1, len(care_cue) + 1 + len(name), "PERSONNAME")
        contact = seed(len(text) - len(phone), len(text), "TELEPHONENUM")
        found = assemble(text, [recipient, contact])
        result = _address_union(text, [recipient, contact] + found)
        care_exact += result == [
            {"start": 0, "end": len(care), "label": "ADDRESS"},
            {"start": contact["start"], "end": contact["end"], "label": "TELEPHONENUM"},
        ]

    # No closed taxonomy: future structured labels must also stop postal growth.
    for label in ("PERSONNAME", "GIVENNAME", "SURNAME", "MIDDLENAME", "TITLE", "EMAIL",
                  "TELEPHONENUM", "USERNAME", "IBAN", "ACCOUNTNUM", "FUTURE_STRUCTURED"):
        address = "12 Zélmar Lane, VQ1 2ZX Vezford"
        suffix = "Qéra Vezorn" if label in {"PERSONNAME", "GIVENNAME", "SURNAME", "MIDDLENAME", "TITLE"} else "QZX001"
        text = address + ", " + suffix
        other = seed(len(address) + 2, len(text), label)
        other["source"] = "structured"
        found = assemble(text, [other, seed(0, len(text), "ADDRESS")])
        contract_ok &= found == [dict(seed(0, len(address), "ADDRESS"), source="address",
                                     score=None, stage="assembled")]
    # Cue words alone are barriers even with no structured/model contact seed.
    for cue in ("Tel.", "Telefon", "Phone", "Mobil", "Handy", "tél.", "cell.", "E-Mail", "mail"):
        address = "Qélmarstraße 12, 73145 Vezlingen"
        text = address + ", " + cue + " +49 30 00001234"
        found = assemble(text, [seed(0, len(text), "ADDRESS")])
        contract_ok &= len(found) == 1 and found[0]["start"] == 0 and found[0]["end"] == len(address)
    return exact, total, care_exact, len(invented), contract_ok


def check():
    complete = total = nonaddr = exact = 0
    contract_ok = True
    for values in ADDRESSES.values():
        for value in values:
            # Emoji, combining accent and CRLF before the value exercise ORIGINAL
            # Python character coordinates without a normalization/index map.
            prefix = "🔷 e\u0301 — Invented postal value: "
            text = prefix + value + ". Next sentence contains ordinary prose."
            found = assemble(text, [])
            start, end = len(prefix), len(prefix) + len(value)
            total += 1
            complete += contains(found, start, end)
            exact += len(found) == 1 and found[0]["start"] == start and found[0]["end"] == end
            for cand in found:
                contract_ok &= set(cand) == {
                    "start", "end", "label", "source", "score", "validation", "context", "protected", "stage",
                }
                contract_ok &= (cand["label"] == "ADDRESS" and cand["source"] == "address"
                                and cand["stage"] == "assembled" and not cand["protected"]
                                and cand["score"] is None
                                and 0 <= cand["start"] < cand["end"] <= len(text)
                                and cand["end"] - cand["start"] <= MAX_REGION_CHARS)
    for text in NON_ADDRESSES:
        nonaddr += len(assemble(text, []))

    # CITY/COUNTRY/ZIPCODE never establish an address, even if all are seeded.
    weak = "73145 Vezlingen, Deutschland"
    weak_seeds = [seed(0, 5, "ZIPCODE"), seed(6, 15, "CITY"), seed(17, len(weak), "COUNTRY")]
    nonaddr += len(assemble(weak, weak_seeds))

    # Read-only model components, with opaque street names and an independent
    # number; neither candidate union nor component mutation is required.
    value = "Qélvori 12a, 73145 Vezlingen, Deutschland"
    seeds = [seed(0, len("Qélvori"), "STREET")]
    before = copy.deepcopy(seeds)
    contract_ok &= contains(assemble(value, seeds), 0, len(value)) and seeds == before

    # Two addresses must not bridge ordinary prose, blank lines or even direct
    # punctuation-separated distinct street cores.
    first = "12 Zélmar Lane, VQ1 2ZX Vezford"
    second = "rue Qélmar 14, 75001 Vézonne"
    for separator in ("\n\n", "; ordinary explanatory prose; ", ", "):
        text = first + separator + second
        found = assemble(text, [])
        contract_ok &= (len(found) == 2 and contains(found, 0, len(first))
                        and contains(found, len(first) + len(separator), len(text)))

    # Adjacent sensitive values remain separate; lexical and supplied candidate
    # boundaries both stop growth, and names inside c/o are not barriers.
    for suffix, label in (("qev@invented.invalid", "EMAIL"), ("+49 620 123 456", "TELEPHONENUM"),
                          ("DE00 0000 0000 0000 0000 00", "IBAN")):
        text = first + ", " + suffix
        barrier = seed(len(first) + 2, len(text), label)
        contract_ok &= all(c["end"] <= len(first) for c in assemble(text, [barrier]))
        contract_ok &= contains(assemble(text, [barrier]), 0, len(first))
    care = "c/o Dr. Qéz Vezorn\n12 Zélmar Lane, VQ1 2ZX Vezford"
    contract_ok &= contains(assemble(care, [seed(4, len("c/o Dr. Qéz Vezorn"), "PERSONNAME")]), 0, len(care))
    long_text = first + ", France" * 40
    contract_ok &= all(c["end"] - c["start"] <= MAX_REGION_CHARS for c in assemble(long_text, []))
    contract_ok &= assemble("", []) == []
    for malformed in ([seed(-1, 2, "STREET")], [seed(0, 999, "CITY")], [{"start": True, "end": 2, "label": "CITY"}]):
        try:
            assemble("invented", malformed)
            contract_ok = False
        except ValueError as exc:
            contract_ok &= str(exc) == "address_candidate_invalid"

    mixed_exact, mixed_total, care_exact, care_total, mixed_ok = mixed_cases()
    contract_ok &= mixed_ok
    print(f"addr_complete={complete}/{total}")
    print(f"nonaddr_regions={nonaddr}")
    print(f"addr_exact={exact}/{total}")
    print(f"mixed_exact={mixed_exact}/{mixed_total}")
    print(f"care_exact={care_exact}/{care_total}")
    print(f"address_contract_ok={int(contract_ok)}")
    return (complete == total and nonaddr == 0 and contract_ok
            and mixed_exact * 10 >= mixed_total * 9 and care_exact == care_total)


def evaluate_v1(source, model_dir):
    if source.name != "masking-stress-dev.jsonl" or not source.is_file() or not model_dir.is_dir():
        raise ValueError("address_v1_paths_invalid") from None
    destination = ROOT / "data/augmentation/address-v1-copy.jsonl"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    from privacygate.hybrid import Mbert, regex
    rows = []
    with destination.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row.get("split") != "dev":
                raise ValueError("address_v1_split_invalid") from None
            rows.append(row)
    model = Mbert(model_dir=model_dir)
    # No raw model result or exception details go to stdout; raw() itself does
    # not log input. Computing in one batch amortizes the offline model load.
    raw = model.raw([row["text"] for row in rows], bs=16)
    complete = raw_complete = assembled_complete = total = 0
    for row, prediction in zip(rows, raw):
        text = row["text"]
        candidates = model.spans(prediction) + regex(text)
        regions = assemble(text, candidates)
        for gold in row["gold"]:
            if gold["label"] == "ADDRESS":
                total += 1
                raw_complete += covered(candidates, gold["start"], gold["end"])
                assembled_complete += contains(regions, gold["start"], gold["end"])
                complete += covered(candidates + regions, gold["start"], gold["end"])
    print(f"v1_address_complete={complete}/{total}")
    print(f"v1_address_raw_complete={raw_complete}/{total}")
    print(f"v1_address_assembled_complete={assembled_complete}/{total}")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1-source", type=Path)
    parser.add_argument("--model-dir", type=Path)
    args = parser.parse_args()
    try:
        if args.v1_source is not None:
            if args.model_dir is None:
                raise ValueError("address_v1_model_required") from None
            ok = evaluate_v1(args.v1_source, args.model_dir)
        else:
            ok = check()
        return 0 if ok else 1
    except Exception:
        print("address_check_failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
