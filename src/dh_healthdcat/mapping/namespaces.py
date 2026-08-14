"""Espaces de noms RDF, alignés sur les préfixes du catalogue HDH.

Source de vérité : `hdh/catalogue-de-metadonnees/api/app/config/queries.yaml`
(clé `prefixes_ttl`). Garder ce fichier synchronisé avec le HDH plutôt que
d'inventer nos propres préfixes évite tout écart silencieux entre le Turtle
que nous produisons et celui que le HDH génère lui-même.
"""

from __future__ import annotations

from rdflib import Namespace
from rdflib.namespace import DCTERMS, FOAF, RDF, RDFS, SKOS, XSD

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

DCT = DCTERMS  # alias court, cohérent avec le préfixe HDH `dct`

PREFIXES: dict[str, Namespace] = {
    "adms": ADMS,
    "csvw": CSVW,
    "dcat": DCAT,
    "dcatap": DCATAP,
    "dct": DCT,
    "dpv": DPV,
    "dpvpd": DPVPD,
    "dqv": DQV,
    "eli": ELI,
    "foaf": FOAF,
    "healthdcatap": HEALTHDCATAP,
    "locn": LOCN,
    "oa": OA,
    "ont": ONT,
    "prov": PROV,
    "rdf": RDF,
    "rdfs": RDFS,
    "skos": SKOS,
    "vcard": VCARD,
    "xsd": XSD,
    "cv": CV,
}


def bind_prefixes(graph) -> None:  # noqa: ANN001 - rdflib.Graph, importé au site d'appel
    """Enregistre tous les préfixes connus sur un graphe, dans un ordre stable."""

    for prefix, namespace in PREFIXES.items():
        graph.bind(prefix, namespace, override=True)
