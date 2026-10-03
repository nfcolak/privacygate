"""Synthetic financial values with real checksum algorithms."""
import re


def grouped(value, widths, separator=" "):
    parts, offset = [], 0
    for width in widths:
        if offset >= len(value):
            break
        parts.append(value[offset:offset + width])
        offset += width
    if offset < len(value):
        parts.append(value[offset:])
    return separator.join(parts)


def mod97(value):
    compact = re.sub(r"[ -]", "", value).upper()
    rearranged = compact[4:] + compact[:4]
    digits = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
    return int(digits) % 97


def iban(country, number, variant):
    bban = {
        "GB": "VELR" + f"{number:014d}",
        "DE": f"{number:018d}", "FR": f"{number:023d}",
        "IT": "V" + f"{number:022d}", "ES": f"{number:020d}",
    }[country]
    tail = "".join(str(ord(c) - 55) for c in country) + "00"
    expanded = "".join(str(ord(c) - 55) if c.isalpha() else c for c in bban)
    check = 98 - int(expanded + tail) % 97
    value = country + f"{check:02d}" + bban
    widths = ((4,) * 8, (2, 2, 6, 3, 5, 9), (5, 5, 5, 5, 9), (2, 7, 4, 8, 9))
    value = grouped(value, widths[variant % 4], "-" if variant % 4 == 3 else " ")
    if mod97(value) != 1:
        raise ValueError("invalid_generated_iban")
    return value


def luhn_total(digits):
    total = 0
    for i, char in enumerate(reversed(digits)):
        digit = int(char)
        if i % 2:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total


def card(number, variant):
    body = "4" + f"{number:014d}"
    digit = (-luhn_total(body + "0")) % 10
    value = body + str(digit)
    if luhn_total(value) % 10:
        raise ValueError("invalid_generated_card")
    widths = ((4, 4, 4, 4), (6, 6, 4), (4, 6, 6), (8, 8))
    return grouped(value, widths[variant % 4], "-" if variant % 2 else " ")
