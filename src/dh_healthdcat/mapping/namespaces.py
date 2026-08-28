"""Espaces de noms RDF, alignés sur les préfixes du catalogue HDH.

Source de vérité : `hdh/catalogue-de-metadonnees/api/app/config/queries.yaml`
(clé `prefixes_ttl`). Garder ce fichier synchronisé avec le HDH plutôt que
d'inventer nos propres préfixes évite tout écart silencieux entre le Turtle
que nous produisons et celui que le HDH génère lui-même.
"""

from __future__ import annotations

from rdflib import Graph, Namespace
from rdflib.namespace import DCTERMS
from rdflib.namespace import FOAF as _FOAF
from rdflib.namespace import RDF as _RDF
from rdflib.namespace import RDFS as _RDFS
from rdflib.namespace import SKOS as _SKOS
from rdflib.namespace import XSD as _XSD

__all__ = [
    "ADMS",
    "CSVW",
    "CV",
    "DCAT",
    "DCATAP",
    "DCT",
    "DPV",
    "DPVPD",
    "DQV",
    "ELI",
    "FOAF",
    "HEALTHDCATAP",
    "LOCN",
    "OA",
    "ONT",
    "PREFIXES",
    "PROV",
    "VCARD",
    "bind_prefixes",
]

# `DCT` / `FOAF` restent des `DefinedNamespace` rdflib : contrairement à
# `Namespace` (sous-classe de `str`), l'accès `DCT.title` / `DCT.format` y
# renvoie bien un `URIRef` et non la méthode `str` homonyme.
DCT = DCTERMS  # préfixe HDH `dct`
FOAF = _FOAF

ADMS = Namespace("http://www.w3.org/ns/adms#")
CSVW = Namespace("http://www.w3.org/ns/csvw#")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
DCATAP = Namespace("http://data.europa.eu/r5r/")
DPV = Namespace("https://w3id.org/dpv#")
DPVPD = Namespace("https://w3id.org/dpv/dpv-pd#")
DQV = Namespace("http://www.w3.org/ns/dqv#")
ELI = Namespace("http://data.europa.eu/eli/")
HEALTHDCATAP = Namespace("http://healthdataportal.eu/ns/health#")
LOCN = Namespace("http://www.w3.org/ns/locn#")
OA = Namespace("https://www.w3.org/ns/oa#")
ONT = Namespace("http://data.europa.eu/eli/ontology#")
PROV = Namespace("http://www.w3.org/ns/prov#")
VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")
CV = Namespace("http://data.europa.eu/m8g/")

# Mapping homogène `str -> Namespace` : les `DefinedNamespace` (dct, foaf, rdf,
# rdfs, skos, xsd) sont ré-enveloppés en `Namespace` pour `graph.bind`.
PREFIXES: dict[str, Namespace] = {
    "adms": ADMS,
    "csvw": CSVW,
    "dcat": DCAT,
    "dcatap": DCATAP,
    "dct": Namespace(str(DCTERMS)),
    "dpv": DPV,
    "dpvpd": DPVPD,
    "dqv": DQV,
    "eli": ELI,
    "foaf": Namespace(str(_FOAF)),
    "healthdcatap": HEALTHDCATAP,
    "locn": LOCN,
    "oa": OA,
    "ont": ONT,
    "prov": PROV,
    "rdf": Namespace(str(_RDF)),
    "rdfs": Namespace(str(_RDFS)),
    "skos": Namespace(str(_SKOS)),
    "vcard": VCARD,
    "xsd": Namespace(str(_XSD)),
    "cv": CV,
}


def bind_prefixes(graph: Graph) -> None:
    """Enregistre tous les préfixes connus sur un graphe, dans un ordre stable."""

    for prefix, namespace in PREFIXES.items():
        graph.bind(prefix, namespace, override=True)
