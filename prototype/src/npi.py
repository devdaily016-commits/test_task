from __future__ import annotations


def _luhn_digit(payload: str) -> str:
    """Check digit so that `payload + digit` passes Luhn.

    The rightmost payload digit is doubled, because the check digit sits to its right.
    """
    total = 0
    for index, char in enumerate(reversed(payload)):
        digit = int(char)
        if index % 2 == 0:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return str((10 - (total % 10)) % 10)


def make_npi(first9: str) -> str:
    if len(first9) != 9 or not first9.isdigit():
        raise ValueError("NPI base must be 9 digits")
    # CMS computes the NPI check digit on the 80840 prefix plus the first 9 digits.
    return first9 + _luhn_digit("80840" + first9)


def npi_is_valid(npi: str) -> bool:
    if len(npi) != 10 or not npi.isdigit():
        return False
    return make_npi(npi[:9]) == npi
