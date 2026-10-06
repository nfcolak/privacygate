"""8,000 invented rows: five languages, 4,000 PERSONNAME positives, 4,000 clean twins.

No external document is consulted for templates or values. Ten culture-inspired
syllable grammars are deliberately invented rather than real-person records.
Each quartet has the same financial tail and a cue-free/cued positive pair plus
company-actor clean twins; amounts, counts, percentages, URLs/domains and product
codes occur in both classes, never as personal-reference or email gold.
"""
from collections import Counter
import random

from .convert import require
from .spec import SEED

# Prefix / middle / suffix combinations, inspired by varied orthographies only.
CULTURES = {
    'germanic': (('Alv', 'Erl', 'Vel', 'Rov', 'Tav', 'Ner'), ('en', 'il', 'or', 'ar', 'el', 'un'), ('a', 'in', 'en', 'ulf', 'win', 'rik')),
    'romance': (('Év', 'Mél', 'Lor', 'Riv', 'Sél', 'Nov'), ('an', 'er', 'av', 'el', 'or', 'iv'), ('elle', 'ia', 'ine', 'io', 'ane', 'et')),
    'slavic': (('Zel', 'Ves', 'Mir', 'Dan', 'Rad', 'Ost'), ('av', 'or', 'en', 'il', 'ev', 'un'), ('ova', 'ina', 'ek', 'ski', 'ev', 'ic')),
    'arabic_inspired': (('Zay', 'Raf', 'Nad', 'Sam', 'Hav', 'Fal'), ('im', 'ar', 'if', 'un', 'el', 'av'), ('an', 'a', 'ir', 'ah', 'un', 'el')),
    'persian_inspired': (('Arv', 'Del', 'Far', 'Mehr', 'Nav', 'Zar'), ('an', 'iv', 'un', 'el', 'or', 'im'), ('eh', 'an', 'a', 'in', 'ar', 'un')),
    'south_asian': (('Rev', 'Tan', 'Nav', 'Kir', 'Dev', 'Sam'), ('an', 'av', 'il', 'un', 'or', 'el'), ('ika', 'esh', 'ini', 'an', 'it', 'ya')),
    'east_asian': (('Rin', 'Yev', 'Han', 'Luv', 'Ken', 'Mei'), ('a', 'o', 'u', 'e', 'ai', 'an'), ('ri', 'na', 'ko', 'lin', 'yu', 'sen')),
    'african_inspired': (('Zem', 'Kel', 'Ad', 'Nol', 'Tam', 'Rav'), ('ani', 'ele', 'olu', 'emi', 'ava', 'ilo'), ('la', 'ni', 'ko', 'ra', 'mi', 'ba')),
    'hispanic': (('Val', 'Mar', 'Sol', 'Ner', 'Bel', 'Lur'), ('av', 'en', 'or', 'il', 'un', 'er'), ('ia', 'ela', 'ino', 'án', 'ina', 'ez')),
    'turkic_inspired': (('Ör', 'Gül', 'Ser', 'Tan', 'İlv', 'Dem'), ('el', 'an', 'av', 'il', 'or', 'un'), ('ay', 'er', 'in', 'al', 'a', 'un')),
}
FRAMES = {
    'en': ('{actor} checked the totals; {tail}', 'The revised calculation reached {actor}; {tail}',
           '{actor} approved the draft; {tail}', 'The remarks from {actor} are attached; {tail}',
           'The next meeting includes {actor}; {tail}', 'Thank you, {actor}. {tail}',
           '{tail}\nRegards,\n{actor}', 'The adjustment was discussed with {actor}; {tail}'),
    'de': ('{actor} prüfte die Summen; {tail}', 'Die neue Berechnung erreichte {actor}; {tail}',
           '{actor} bestätigte den Entwurf; {tail}', 'Die Anmerkungen von {actor} liegen bei; {tail}',
           'Am nächsten Treffen nimmt {actor} teil; {tail}', 'Vielen Dank, {actor}. {tail}',
           '{tail}\nMit freundlichen Grüßen\n{actor}', 'Die Anpassung wurde mit {actor} besprochen; {tail}'),
    'fr': ('{actor} a vérifié les totaux ; {tail}', 'Le calcul révisé est parvenu à {actor} ; {tail}',
           '{actor} a approuvé le brouillon ; {tail}', 'Les remarques de {actor} sont jointes ; {tail}',
           'La prochaine réunion inclut {actor} ; {tail}', 'Merci, {actor}. {tail}',
           '{tail}\nCordialement,\n{actor}', 'La correction a été discutée avec {actor} ; {tail}'),
    'it': ('{actor} ha controllato i totali; {tail}', 'Il calcolo aggiornato è arrivato a {actor}; {tail}',
           '{actor} ha approvato la bozza; {tail}', 'Le osservazioni di {actor} sono allegate; {tail}',
           'Alla prossima riunione partecipa {actor}; {tail}', 'Grazie, {actor}. {tail}',
           '{tail}\nCordiali saluti,\n{actor}', 'La modifica è stata discussa con {actor}; {tail}'),
    'es': ('{actor} revisó los totales; {tail}', 'El cálculo revisado llegó a {actor}; {tail}',
           '{actor} aprobó el borrador; {tail}', 'Se adjuntan los comentarios de {actor}; {tail}',
           'La próxima reunión incluye a {actor}; {tail}', 'Gracias, {actor}. {tail}',
           '{tail}\nSaludos,\n{actor}', 'El ajuste se discutió con {actor}; {tail}'),
}
TITLES = {'en': 'Mr ', 'de': 'Herr ', 'fr': 'Mme ', 'it': 'Sig. ', 'es': 'Sr. '}
TAILS = {
    'en': 'Quarterly Results: balance {money}; {count} units; change {percent}%; website {url}; domain {domain}; model {model}.',
    'de': 'Quartalsergebnis: Saldo {money}; {count} Stück; Änderung {percent}%; Webseite {url}; Domain {domain}; Modell {model}.',
    'fr': 'Résultats trimestriels : solde {money} ; {count} unités ; variation {percent}% ; site {url} ; domaine {domain} ; modèle {model}.',
    'it': 'Risultati trimestrali: saldo {money}; {count} unità; variazione {percent}%; sito {url}; dominio {domain}; modello {model}.',
    'es': 'Resultados trimestrales: saldo {money}; {count} unidades; cambio {percent}%; sitio {url}; dominio {domain}; modelo {model}.',
}
SUFFIXES = ('GmbH', 'AG', 'SA', 'Ltd', 'S.p.A.')


def invented(rng, pools):
    return ''.join(rng.choice(pool) for pool in pools)


def money(index):
    whole = 1200 + index * 37
    major = format(whole, ',')
    continental = major.replace(',', '.')
    spaced = major.replace(',', '\u202f')
    return (f'${major}.45', f'€{continental},70', f'£{major}.20',
            f'{spaced},15 €', f'CHF {major.replace(chr(44), chr(39))}.80', f'¥{whole}')[index % 6]


def build_synthetic():
    rows, counts = [], {axis: Counter() for axis in ('culture_grammar', 'name_form', 'casing', 'cue', 'legal_suffix', 'frame')}
    cultures = tuple(CULTURES)
    for li, language in enumerate(('en', 'de', 'fr', 'it', 'es')):
        rng = random.Random(SEED + 97 * li)
        for index in range(400):
            culture = cultures[index % len(cultures)]
            pools = CULTURES[culture]
            first, surname = invented(rng, pools), invented(rng, pools)
            form = ('first_only', 'surname_only', 'full_name')[(index // 10) % 3]
            name = first if form == 'first_only' else surname if form == 'surname_only' else first + ' ' + surname
            casing = ('title', 'lower', 'upper')[(index // 30) % 3]
            name = name.lower() if casing == 'lower' else name.upper() if casing == 'upper' else name
            marker = TITLES[language] if index % 2 == 0 else 'Name: '
            company = invented(rng, CULTURES['romance']) + ' ' + SUFFIXES[(index // 2) % 5]
            model = 'QV-{}{}'.format(3200 + index * 11 + li, 'ABXZ'[index % 4])
            domain = 'ledger-{}-{}.invalid'.format(language, index)
            url = ('https://' if index % 2 else 'http://') + domain + '/reports/' + model.lower()
            tail = TAILS[language].format(money=money(index + li), count=31 + index * 13,
                percent=('{}.{}'.format(1 + index % 79, index % 10) if language == 'en'
                         else '{},{}'.format(1 + index % 79, index % 10)),
                url=url, domain=domain, model=model)
            frame_index = (index // 3) % len(FRAMES[language])
            frame = FRAMES[language][frame_index]
            rendered = []
            for variant, actor, cue, positive in (
                    ('no_cue', name, '', True), ('with_cue', name, marker, True),
                    ('clean_no_cue', company, '', False), ('clean_with_cue', company, 'Company: ', False)):
                # Replace a sentinel once so offsets never depend on searching a repeated value.
                before, after = frame.format(actor='\0', tail=tail).split('\0')
                text = before + cue + actor + after
                start = len(before) + len(cue)
                gold = [dict(start=start, end=start + len(actor), label='PERSONNAME')] if positive else []
                rows.append({'case_id': 'v6-syn-{}-{:04d}-{}'.format(language, index, variant),
                    'family': 'v6_person_{}_{}_{}'.format(form, casing, variant) if positive else 'v6_hard_negative_' + variant,
                    'language': language, 'split': 'train', 'text': text, 'gold': gold})
                rendered.append(text)
            require(rendered[1] == before + marker + name + after, 'cue_pair_mismatch')
            require(rendered[0] == before + name + after, 'cue_dropout_mismatch')
            counts['culture_grammar'][culture] += 2
            counts['name_form'][form] += 2
            counts['casing'][casing] += 2
            counts['cue']['none'] += 1
            counts['cue']['title' if index % 2 == 0 else 'name_label'] += 1
            counts['legal_suffix'][SUFFIXES[(index // 2) % 5]] += 2
            counts['frame'][str(frame_index)] += 4
    require(len(rows) == 8000 and sum(bool(row['gold']) for row in rows) == 4000, 'synthetic_size')
    return rows, {'quartets': 2000, 'cue_dropout_pairs': 2000, 'positive_clean_twin_pairs': 4000,
                  'positive_rows': 4000, 'clean_rows': 4000, 'rows_per_language': 1600,
                  'hard_negative_exposures': {key: 4000 for key in (
                      'money', 'counts', 'percentages', 'urls', 'domains', 'companies', 'product_model_codes')},
                  'axes': {axis: dict(sorted(counter.items())) for axis, counter in counts.items()}}
