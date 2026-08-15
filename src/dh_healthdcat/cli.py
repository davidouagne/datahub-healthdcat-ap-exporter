"""CLI `dh-healthdcat` — export-file (Lot 2) et push-hdh (Lot 3)."""

from __future__ import annotations

from pathlib import Path

import typer
from rdflib import Graph

from dh_healthdcat.mapping.dataset import dataset_to_graph
from dh_healthdcat.model import HealthDataset, Severity
from dh_healthdcat.reader.dataproduct import DEFAULT_BASE_URI, read_data_product
from dh_healthdcat.reader.graph import from_env
from dh_healthdcat.selection import select_data_product_urns
from dh_healthdcat.validate.shacl import validate_graph

app = typer.Typer(add_completion=False, help="Exporteur DataHub -> HealthDCAT-AP")


def _echo_issues(dataset: HealthDataset) -> None:
    for issue in dataset.issues:
        color = typer.colors.RED if issue.severity is Severity.ERROR else typer.colors.YELLOW
        typer.secho(str(issue), fg=color, err=True)


@app.command("export-file")
def export_file(
    output: Path = typer.Option(..., "--output", "-o", help="Fichier ou dossier de sortie (voir --split-per-dataset)"),
    urn: list[str] = typer.Option([], "--urn", help="URN de DataProduct à exporter (répétable). Sans valeur : tout le catalogue. Prioritaire sur --domain/--tag/--exclude-tag."),
    domain: list[str] = typer.Option([], "--domain", help="Filtre par domaine (urn ou id, répétable)"),
    tag: list[str] = typer.Option([], "--tag", help="Filtre par tag (urn ou nom, répétable)"),
    tag_mode: str = typer.Option("any", "--tag-mode", help="any (au moins un des --tag, défaut) | all (tous les --tag)"),
    exclude_tag: list[str] = typer.Option([], "--exclude-tag", help="Exclut les DataProducts portant ce tag (urn ou nom, répétable)"),
    fmt: str = typer.Option("turtle", "--format", help="turtle | json-ld | n-triples"),
    split_per_dataset: bool = typer.Option(False, "--split-per-dataset", help="Un fichier par DataProduct dans --output (dossier)"),
    base_uri: str = typer.Option(DEFAULT_BASE_URI, "--base-uri", help="Base pour dct:identifier"),
    strict: bool = typer.Option(True, "--strict/--no-strict", help="Échoue si un jeu a une ERREUR SHACL (désactiver pour un export exploratoire)"),
) -> None:
    """Exporte le catalogue DataHub (DataProducts) en HealthDCAT-AP."""

    from dh_healthdcat.emit.turtle import write_graph

    ctx = from_env()
    try:
        selected = select_data_product_urns(
            ctx,
            urns=urn,
            domains=domain,
            tags=tag,
            tag_mode=tag_mode,
            exclude_tags=exclude_tag,
            on_warning=lambda m: typer.secho(m, fg=typer.colors.YELLOW, err=True),
        )
    except ValueError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc

    if not selected:
        typer.secho("Aucun DataProduct ne correspond aux filtres.", fg=typer.colors.YELLOW, err=True)
        raise typer.Exit(code=1)

    graphs: list[Graph] = []
    any_error = False
    any_shacl_violation = False
    excluded = 0

    for dp_urn in selected:
        try:
            dataset = read_data_product(ctx, dp_urn, base_uri=base_uri)
        except ValueError as exc:
            typer.secho(f"IGNORÉ {dp_urn} : {exc}", fg=typer.colors.RED, err=True)
            any_error = True
            excluded += 1
            continue

        graph = dataset_to_graph(dataset)
        _echo_issues(dataset)

        if dataset.has_errors:
            any_error = True

        result = validate_graph(graph)
        if not result.conforms:
            any_shacl_violation = True
            typer.secho(f'DataProduct "{dataset.title}" : non conforme SHACL', fg=typer.colors.RED, err=True)
            typer.echo(result.report_text, err=True)

        # Un DataProduct invalide est exclu de l'export, pas le lot entier :
        # les autres jeux sélectionnés ne doivent pas payer pour celui-ci
        # (voir investigation --tag aphp:access, qui a fait échouer un export
        # entier à cause de DataProducts de production sans rapport avec le
        # filtre, jamais peuplés en propriétés HealthDCAT-AP).
        if strict and (dataset.has_errors or not result.conforms):
            typer.secho(f'  -> "{dataset.title}" exclu de l\'export : erreurs ci-dessus (--no-strict pour forcer)', fg=typer.colors.YELLOW, err=True)
            excluded += 1
            continue

        graphs.append(graph)

        if split_per_dataset:
            from dh_healthdcat.emit.turtle import FORMAT_TO_EXTENSION

            out_path = output / f"{dataset.dataset_id}{FORMAT_TO_EXTENSION[fmt]}"
            write_graph(graph, out_path, fmt=fmt)
            typer.echo(f"  -> {out_path}")

    if not split_per_dataset:
        if not graphs:
            typer.secho("Export non écrit : aucun DataProduct valide dans la sélection (--no-strict pour forcer).", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)

        merged = Graph()
        for g in graphs:
            merged += g
        from dh_healthdcat.mapping.namespaces import bind_prefixes

        bind_prefixes(merged)
        write_graph(merged, output, fmt=fmt)
        suffix = f", {excluded} exclu(s)" if excluded else ""
        typer.echo(f"Écrit : {output} ({len(merged)} triplets, {len(graphs)}/{len(selected)} jeu(x){suffix})")

    if strict and (any_error or any_shacl_violation):
        raise typer.Exit(code=1)


@app.command("validate")
def validate(
    file: Path = typer.Argument(..., help="Fichier RDF à valider (Turtle, JSON-LD, N-Triples...)"),
    fmt: str | None = typer.Option(None, "--format", help="Format RDF (turtle|json-ld|n-triples). Déduit de l'extension si omis."),
) -> None:
    """Valide un graphe RDF contre les shapes SHACL du HDH, indépendamment de DataHub.

    Utile pour un fichier .ttl obtenu autrement qu'via `export-file` (édité à
    la main, produit par un autre outil, récupéré du HDH...)."""

    from dh_healthdcat.emit.turtle import FORMAT_TO_RDFLIB

    rdflib_format = FORMAT_TO_RDFLIB.get(fmt) if fmt else None
    graph = Graph()
    try:
        if rdflib_format:
            graph.parse(str(file), format=rdflib_format)
        else:
            graph.parse(str(file))  # rdflib devine le format depuis l'extension
    except Exception as exc:
        typer.secho(f"Impossible de lire {file} : {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc

    result = validate_graph(graph)
    if result.conforms:
        typer.secho(f"Conforme ({len(graph)} triplets).", fg=typer.colors.GREEN)
        return

    typer.secho("Non conforme :", fg=typer.colors.RED, err=True)
    typer.echo(result.report_text, err=True)
    raise typer.Exit(code=1)


@app.command("push-hdh")
def push_hdh(
    hdh_url: str = typer.Option(..., "--hdh-url", help="Base URL du catalogue HDH (ex: https://catalogue.health-data-hub.fr)"),
    api_key: str | None = typer.Option(None, "--api-key", help="Clé mdc_... (sinon lue depuis --api-key-env)"),
    api_key_env: str = typer.Option("HDH_API_KEY", "--api-key-env", help="Variable d'environnement portant la clé API"),
    urn: list[str] = typer.Option([], "--urn", help="URN de DataProduct à pousser (répétable). Sans valeur : tout le catalogue. Prioritaire sur --domain/--tag/--exclude-tag."),
    domain: list[str] = typer.Option([], "--domain", help="Filtre par domaine (urn ou id, répétable)"),
    tag: list[str] = typer.Option([], "--tag", help="Filtre par tag (urn ou nom, répétable)"),
    tag_mode: str = typer.Option("any", "--tag-mode", help="any (au moins un des --tag, défaut) | all (tous les --tag)"),
    exclude_tag: list[str] = typer.Option([], "--exclude-tag", help="Exclut les DataProducts portant ce tag (urn ou nom, répétable)"),
    base_uri: str = typer.Option(DEFAULT_BASE_URI, "--base-uri", help="Base pour dct:identifier"),
    state_file: Path | None = typer.Option(None, "--state-file", help="Fichier de correspondance URN->id HDH (défaut : .dh-healthdcat-state.json)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Valide et affiche ce qui serait envoyé, sans appel réseau d'écriture"),
) -> None:
    """Pousse le catalogue DataHub (DataProducts) vers /ingest/datasets du HDH."""

    import os

    from dh_healthdcat.emit import state as state_module
    from dh_healthdcat.emit.hdh_client import HdhClient, HdhClientError

    resolved_key = api_key or os.environ.get(api_key_env)
    if not resolved_key:
        typer.secho(f"Aucune clé API : passez --api-key ou définissez ${api_key_env}.", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    client = HdhClient(base_url=hdh_url.rstrip("/"), api_key=resolved_key)
    try:
        who = client.whoami()
    except HdhClientError as exc:
        typer.secho(f"Clé API invalide ou rôle data-provider manquant : {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Connecté au HDH ({who}).")

    ctx = from_env()
    try:
        selected = select_data_product_urns(
            ctx,
            urns=urn,
            domains=domain,
            tags=tag,
            tag_mode=tag_mode,
            exclude_tags=exclude_tag,
            on_warning=lambda m: typer.secho(m, fg=typer.colors.YELLOW, err=True),
        )
    except ValueError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc
    if not selected:
        typer.secho("Aucun DataProduct ne correspond aux filtres.", fg=typer.colors.YELLOW, err=True)
        raise typer.Exit(code=1)

    state_path = state_file or state_module.DEFAULT_STATE_PATH
    dataset_state = state_module.load(state_path)
    any_failure = False

    for dp_urn in selected:
        try:
            dataset = read_data_product(ctx, dp_urn, base_uri=base_uri)
        except ValueError as exc:
            typer.secho(f"IGNORÉ {dp_urn} : {exc}", fg=typer.colors.RED, err=True)
            any_failure = True
            continue

        graph = dataset_to_graph(dataset)
        _echo_issues(dataset)

        # P0-10 : aucune requête réseau d'écriture pour un jeu invalide.
        result = validate_graph(graph)
        if dataset.has_errors or not result.conforms:
            typer.secho(f'IGNORÉ "{dataset.title}" : invalide (SHACL et/ou champs obligatoires manquants, voir ci-dessus)', fg=typer.colors.RED, err=True)
            if not result.conforms:
                typer.echo(result.report_text, err=True)
            any_failure = True
            continue

        turtle = graph.serialize(format="turtle")
        existing_id = state_module.get_hdh_id(dataset_state, dp_urn)

        if dry_run:
            action = f"PUT (mise à jour de {existing_id})" if existing_id else "POST (création)"
            typer.echo(f'[dry-run] "{dataset.title}" -> {action} · {len(turtle)} octets Turtle')
            continue

        try:
            if existing_id:
                hdh_id = client.update_dataset(existing_id, turtle)
            else:
                hdh_id = client.create_dataset(turtle)
        except HdhClientError as exc:
            typer.secho(f'ÉCHEC "{dataset.title}" : {exc}', fg=typer.colors.RED, err=True)
            any_failure = True
            continue

        state_module.set_hdh_id(dataset_state, dp_urn, hdh_id)
        typer.echo(f'"{dataset.title}" -> {hdh_id}')

    if not dry_run:
        state_module.save(dataset_state, state_path)

    if any_failure:
        raise typer.Exit(code=1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
