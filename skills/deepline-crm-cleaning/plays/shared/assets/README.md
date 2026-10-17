# Frozen inputs

`public-suffix-list.txt` contains the public/private suffix snapshot from tldextract 5.3.1. The domain collector records its SHA-256. Retain its attribution and MPL 2.0 license.

`../unicode-casefold.json` contains full default Unicode 16.0.0 case-fold mappings. It matches every C/F entry in [CaseFolding.txt](https://www.unicode.org/Public/16.0.0/ucd/CaseFolding.txt). It excludes locale-specific Turkic mappings. Retain `unicode.LICENSE.txt`.

Changing either input changes the Play artifact. Run matching and domain evaluation after any update.
