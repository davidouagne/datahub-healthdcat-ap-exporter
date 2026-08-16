"""CLI `dh-healthdcat` — export-file (Lot 2), validate et push-hdh (Lot 3).

Ne prend plus aucune décision d'inclusion/exclusion : `pipeline.py` orchestre
lecture -> mapping -> validation SHACL -> décision et produit une séquence
d'outcomes typés (spec-feature-export-pipeline.md). Ce module se contente de
traduire chaque outcome en couleur de sortie, en compteur agrégé et en code de
sortie du processus."""

from __future__ import annotations

from pathlib import Path

import typer
from rdflib import Graph

from dh_healthdcat import pipeline
from dh_healthdcat.model import HealthDataset, Severity
from dh_healthdcat.reader.dataproduct import DEFAULT_BASE_URI
from dh_healthdcat.reader.graph import ReadContext, from_env
from dh_healthdcat.selection import select_data_product_urns
from dh_healthdcat.validate.shacl import ShaclResult, validate_graph

app = typer.Typer(add_completion=False, help="Exporteur DataHub -> HealthDCAT-AP")


def _echo_issues(dataset: HealthDataset) -> None:
    for issue in dataset.issues:
        color = typer.colors.RED if issue.severity is Severity.ERROR else typer.colors.YELLOW
        typer.secho(str(issue), fg=color, err=True)


def _echo_shacl_violation(dataset: HealthDataset, shacl: ShaclResult) -> None:
    if not shacl.conforms:
        typer.secho(f'DataProduct "{dataset.title}" : non conforme SHACL', fg=typer.colors.RED, err=True)
        typer.echo(shacl.report_text, err=True)


def _resolve_target_or_exit(
    *, cli_url: str | None, cli_profile: str | None, cli_config: Path | None, cli_api_key_env: str | None
):
    import os

    from dh_healthdcat import config as config_module

    try:
        config_path = config_module.find_config_file(explicit=cli_config, env=os.environ, cwd=Path.cwd(), home=Path.home())
        cfg = config_module.load_config(config_path) if config_path else None
        return config_module.resolve_target(
            config=cfg, env=os.environ, cli_url=cli_url, cli_profile=cli_profile, cli_api_key_env=cli_api_key_env
        )
    except config_module.ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc


def _select_or_exit(
    ctx: ReadContext, *, urn: list[str], domain: list[str], tag: list[str], tag_mode: str, exclude_tag: list[str]
) -> list[str]:
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

    return selected


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
    selected = _select_or_exit(ctx, urn=urn, domain=domain, tag=tag, tag_mode=tag_mode, exclude_tag=exclude_tag)

    graphs: list[Graph] = []
    any_error = False
    any_shacl_violation = False
    excluded = 0

    for outcome in pipeline.prepare(ctx, selected, base_uri=base_uri, strict=strict):
        if isinstance(outcome, pipeline.Unreadable):
            typer.secho(f"IGNORÉ {outcome.urn} : {outcome.reason}", fg=typer.colors.RED, err=True)
            any_error = True
            excluded += 1
            continue

        dataset = outcome.dataset
        _echo_issues(dataset)

        if dataset.has_errors:
            any_error = True
        if not outcome.shacl.conforms:
            any_shacl_violation = True
        _echo_shacl_violation(dataset, outcome.shacl)

        if isinstance(outcome, pipeline.Rejected):
            typer.secho(f'  -> "{dataset.title}" exclu de l\'export : erreurs ci-dessus (--no-strict pour forcer)', fg=typer.colors.YELLOW, err=True)
            excluded += 1
            continue

        graph = outcome.graph
        graphs.append(graph)

        if split_per_dataset:
            from dh_healthdcat.emit.turtle import FORMAT_TO_EXTENSION

            out_path = output / f"{dataset.dataset_id}{FORMAT_TO_EXTENSION[fmt]}"
            write_graph(graph, out_path, fmt=fmt)
            typer.echo(f"  -> {out_path}")

    suffix = f", {excluded} exclu(s)" if excluded else ""

    if split_per_dataset:
        typer.echo(f"{len(graphs)}/{len(selected)} jeu(x) écrit(s) dans {output}{suffix}")
    else:
        if not graphs:
            typer.secho("Export non écrit : aucun DataProduct valide dans la sélection (--no-strict pour forcer).", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)

        merged = Graph()
        for g in graphs:
            merged += g
        from dh_healthdcat.mapping.namespaces import bind_prefixes

        bind_prefixes(merged)
        write_graph(merged, output, fmt=fmt)
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
    hdh_url: str | None = typer.Option(None, "--hdh-url", help="Base URL du catalogue (prioritaire sur $HDH_URL et le profil sélectionné)"),
    profile: str | None = typer.Option(None, "--profile", help="Profil déclaré dans le fichier de configuration (sinon $HDH_PROFILE, default_profile, ou l'unique profil)"),
    config: Path | None = typer.Option(None, "--config", help="Fichier de configuration (sinon $HDH_CONFIG, ./.dh-healthdcat.yml, ~/.dh-healthdcat.yml)"),
    api_key: str | None = typer.Option(None, "--api-key", help="Clé mdc_... (sinon lue depuis la variable résolue par --api-key-env)"),
    api_key_env: str | None = typer.Option(None, "--api-key-env", help="Variable d'environnement portant la clé API (sinon celle du profil, sinon HDH_API_KEY)"),
    urn: list[str] = typer.Option([], "--urn", help="URN de DataProduct à pousser (répétable). Sans valeur : tout le catalogue. Prioritaire sur --domain/--tag/--exclude-tag."),
    domain: list[str] = typer.Option([], "--domain", help="Filtre par domaine (urn ou id, répétable)"),
    tag: list[str] = typer.Option([], "--tag", help="Filtre par tag (urn ou nom, répétable)"),
    tag_mode: str = typer.Option("any", "--tag-mode", help="any (au moins un des --tag, défaut) | all (tous les --tag)"),
    exclude_tag: list[str] = typer.Option([], "--exclude-tag", help="Exclut les DataProducts portant ce tag (urn ou nom, répétable)"),
    base_uri: str = typer.Option(DEFAULT_BASE_URI, "--base-uri", help="Base pour dct:identifier"),
    state_file: Path | None = typer.Option(None, "--state-file", help="Fichier de correspondance URN->id HDH (défaut : .dh-healthdcat-state.json)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Valide et affiche ce qui serait envoyé, sans appel réseau d'écriture"),
) -> None:
    """Pousse le catalogue DataHub (DataProducts) vers /ingest/datasets du HDH.

    Politique d'exclusion fixée à "strict" — voir `pipeline.push()` — sans
    `--no-strict` : ne jamais envoyer de données invalides au HDH est une
    propriété de sûreté, pas une préférence configurable."""

    import os

    from dh_healthdcat.emit import state as state_module
    from dh_healthdcat.emit.hdh_client import HdhClient, HdhClientError

    resolved = _resolve_target_or_exit(cli_url=hdh_url, cli_profile=profile, cli_config=config, cli_api_key_env=api_key_env)

    resolved_key = api_key or os.environ.get(resolved.api_key_env)
    if not resolved_key:
        typer.secho(f"Aucune clé API : passez --api-key ou définissez ${resolved.api_key_env}.", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    client = HdhClient(base_url=resolved.url, api_key=resolved_key)
    try:
        who = client.whoami()
    except HdhClientError as exc:
        typer.secho(f"Clé API invalide ou rôle data-provider manquant : {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    profile_label = f" (profil {resolved.profile_name})" if resolved.profile_name else ""
    typer.echo(f"Connecté à {resolved.url}{profile_label} ({who}).")

    ctx = from_env()
    selected = _select_or_exit(ctx, urn=urn, domain=domain, tag=tag, tag_mode=tag_mode, exclude_tag=exclude_tag)

    state_path = state_file or state_module.DEFAULT_STATE_PATH
    state = state_module.PushState.open(
        state_path, instance=resolved.url, on_warning=lambda m: typer.secho(m, fg=typer.colors.YELLOW, err=True)
    )
    any_failure = False

    for outcome in pipeline.push(ctx, selected, target=client, state=state, base_uri=base_uri, dry_run=dry_run):
        if isinstance(outcome, pipeline.Unreadable):
            typer.secho(f"IGNORÉ {outcome.urn} : {outcome.reason}", fg=typer.colors.RED, err=True)
            any_failure = True
            continue

        dataset = outcome.dataset
        _echo_issues(dataset)

        if isinstance(outcome, pipeline.Rejected):
            typer.secho(f'IGNORÉ "{dataset.title}" : invalide (SHACL et/ou champs obligatoires manquants, voir ci-dessus)', fg=typer.colors.RED, err=True)
            if not outcome.shacl.conforms:
                typer.echo(outcome.shacl.report_text, err=True)
            any_failure = True
            continue

        if isinstance(outcome, pipeline.Planned):
            action = f"PUT (mise à jour de {outcome.existing_id})" if outcome.existing_id else "POST (création)"
            typer.echo(f'[dry-run] "{dataset.title}" -> {action} · {outcome.turtle_bytes} octets Turtle')
            continue

        if isinstance(outcome, pipeline.PushFailed):
            typer.secho(f'ÉCHEC "{dataset.title}" : {outcome.error}', fg=typer.colors.RED, err=True)
            any_failure = True
            continue

        # pipeline.Pushed — story 10 : indiquer création vs mise à jour.
        action_label = "créé" if outcome.action is pipeline.PushAction.CREATED else "mis à jour"
        typer.echo(f'"{dataset.title}" -> {outcome.hdh_id} ({action_label})')

    if any_failure:
        raise typer.Exit(code=1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
