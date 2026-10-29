# Changelog

## [0.3.0](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/compare/v0.2.0...v0.3.0) (2026-10-29)


### ⚠ BREAKING CHANGES

* la valeur `NFS` de `healthdcatap.coding` n'est plus reconnue (ignorée avec un avertissement) ; la remplacer par `NABM`. Les IRI émises pour CIP13, UCD, CCAM et NABM changent.
* `--base-uri` n'a plus de défaut (`https://eds.aphp.fr`) et le repli `urn:aphp:conformsTo:<code>` disparaît. Déclarer `base_uri` dans le profil ou passer `--base-uri` à `export-file` et `push-hdh`.
* les SP `fr.aphp.healthdcat.*` ne sont plus lues. Les définitions (`dh-healthdcat properties`) et les valeurs doivent être migrées vers `healthdcatap.*` avant de monter de version.
* acryl-datahub >= 1.7 et < 1.8 est désormais requis. Un environnement qui impose un acryl-datahub plus ancien, ou d'une mineure non encore vérifiée, ne peut plus installer l'exporteur sans forcer la résolution.

### Features

* avertir si le serveur DataHub est hors de la plage supportée ([c8edb92](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/c8edb9234297d5a200d2bc48a1a5107017a200c2)), closes [#128](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/128)
* exporter dcat:landingPage et foaf:page ([3dabe4b](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/3dabe4b6f550cd5ac13fbc00b67a3aaf1c800ae7)), closes [#145](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/145)
* lanceur local d'un serveur DataHub isolé par version ([5aa454f](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/5aa454f2b66802acd9a7b8f01f53b8926a4513c3)), closes [#170](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/170)
* lire les structured properties sous le préfixe healthdcatap ([7e78057](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/7e78057bc16db96019eb2e3f58a1e9cf66adc961)), closes [#135](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/135)
* livrer les définitions des SP et la commande properties ([0a97c45](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/0a97c457a3ed6e5dd88a958616044cbb75178553)), closes [#134](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/134)
* ne publier que les output ports d'un Data Product ([5868297](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/5868297bf212e4d056b32416e589308470335d7f)), closes [#147](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/147)
* rendre l'URI de base obligatoire ([a45ddc7](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/a45ddc7571ac39bebb91150c051785fe5cb95ef2)), closes [#136](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/136)
* URIs de l'ANS pour les systèmes de codage français ([a8bc3a9](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/a8bc3a9b3cde16576fcfe8e95ff879675eddbeae)), closes [#138](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/138)


### Bug Fixes

* émettre dct:modified depuis les distributions ([5059fe2](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/5059fe21ed593ba33a317510613e734d7b8b4d13)), closes [#143](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/143)
* ne demander à DataHub que les aspects lus ([f5d7e5f](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/f5d7e5ff22d95d612d390bba6ec83e7f076abcf8)), closes [#142](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/142)
* ne supprimer que les volumes du projet après le contrôle Docker ([eb2713d](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/eb2713de47f214ba078c48c630c2dce6ca4b32d1)), closes [#170](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/170)
* relever le plancher de typer à 0.16 ([abf9762](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/abf976277b8fd6f666b04123ac53dc6377b512fb)), closes [#127](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/127)
* un nœud de distribution par DataProduct pour un asset partagé ([a7ee466](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/a7ee4667b1fb7830a924c01c9b07f14ae15a894f)), closes [#144](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/144)


### Dependencies

* Bump msgpack from 1.2.2 to 1.2.3 ([6aac09e](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/6aac09e0b3be975fd6814dcdcce71f4a1dc05bb2))


### Documentation

* ADR-0004 politique de support des versions DataHub ([cd08972](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/cd08972d0e98411c85fc44b75180761ffcb2ced0)), closes [#124](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/124)
* ADR-0005 contrat des structured properties healthdcatap.* ([1cb4331](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/1cb43318fa67be87abfa279acccd6d7676f5ab37)), closes [#125](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/125)
* ADR-0006, hiérarchie de Data Products et output ports ([3b9a756](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/3b9a756fb8e708c31d918c5ef2f2b143e41e945e))
* guide de migration vers la 0.3.0 ([57475b6](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/57475b61c761cf5a31fcb6abd1ca088c0aa1225d)), closes [#140](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/140)
* lancer les scripts shell sous Windows avec Git Bash ([8488097](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/848809718517b0fae8e68a80e2ead251f735e33c)), closes [#170](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/170)
* note de recherche sur les URIs des systèmes de codage ([3763ef5](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/3763ef530182264b1079ccb962b413106e353b5a)), closes [#137](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/137)
* présenter l'exporteur pour tout adoptant ([c07da2c](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/c07da2c9572a86fe97aa984ac9b60f01f018552b)), closes [#139](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/139)
* procédure d'élargissement de la plage DataHub ([b3ced16](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/b3ced16b0a54b0f35384a7725e115952404dbfd7)), closes [#131](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/131)
* recherche sur le Data Product de DataHub 1.8 ([1cc296d](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/1cc296d9b269e05f27e14c283f6bb31ef8de82cf)), closes [#124](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/124)
* versionner les specs sous docs/specs ([371d8ba](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/371d8baf1e24f9e75b510a8fd0b1832f2bdaf0e8))


### Build System

* restreindre acryl-datahub à la plage vérifiée &gt;=1.7,&lt;1.8 ([afd1180](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/afd1180f5c45fa3e9a4b503ded77987b3bb6868f)), closes [#127](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/127)

## [0.2.0](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/compare/v0.1.9...v0.2.0) (2026-10-26)


### ⚠ BREAKING CHANGES

* Python 3.11 minimum. Les utilisateurs en 3.10 restent sur la série 0.1.x.

### Features

* abandonner Python 3.10, en fin de vie ([22bef55](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/22bef552828682d639dcb3c69055bccac33f0dd6))


### Dependencies

* acryl-datahub 1.7.0.14 → 1.7.0.16, certifi 2026.7.22 → 2026.10.19 ([3fba98c](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/3fba98c1e4137972d2436144d0ad42cab934257c))
* Bump acryl-datahub from 1.7.0.16 to 1.7.0.17 ([9b6d757](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/9b6d7574db80fba02b57e9c056a454c4ca7dbd0a))


### Documentation

* **adr:** release patch sur montée de dépendance de prod ([3fba98c](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/3fba98c1e4137972d2436144d0ad42cab934257c))

## [0.1.9](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/compare/v0.1.8...v0.1.9) (2026-10-05)


### Documentation

* activer les Dependabot security updates (ADR-0003) ([4dd6140](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/4dd61405cf265b3e480bf4748e26f31cd86ace6c))


### Dependencies

* urllib3 2.7.0 → 2.8.0 : corrige PYSEC-2026-4175, PYSEC-2026-4176 et PYSEC-2026-4177 ([6b3940b](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/6b3940b6efae5f1739b647f4e85d5aa9b218dd23))

## [0.1.8](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/compare/v0.1.7...v0.1.8) (2026-09-20)


### Documentation

* corriger l'état du ruleset tags-v et du dépôt jumeau ([495efa9](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/495efa90c4b9a2f9a918848fedb7ca0c52593d83))
* corriger l'état du ruleset tags-v et du dépôt jumeau ([3e32e23](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/3e32e23cffbe999696df669bc536726f29a8a568))
* ruleset main comme unique protection de branche ([9a757ab](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/9a757ab46f6dd4860ef2a02c02a074a3ad8aa960))
* ruleset main comme unique protection de branche ([6b87bea](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/6b87bea3e7d316d377d887c121f0762f16aecf77))

## [0.1.7](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/compare/v0.1.6...v0.1.7) (2026-09-18)


### Documentation

* flag PersonalData.yml namespace mix and Death term vs DPV-PD spec ([a44355c](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/a44355cede3e1fa2964d2d6931ec846acbc11c7a))
* flag PersonalData.yml namespace mix and Death term vs DPV-PD spec ([c702260](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/c70226070fc4e1071c4dadd6bd368e3f4ff8a168))
* revert local Death removal, consolidate HDH vs HealthDCAT-AP gaps ([1a86b4d](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/1a86b4d474811cb04a025585039e2d53ccced3ce))
* revert local Death removal, consolidate HDH vs HealthDCAT-AP gaps ([6380124](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/638012485e3a7b7bdb07f226b73afcc969f1d2ec))

## [0.1.6](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/compare/v0.1.5...v0.1.6) (2026-09-17)


### Documentation

* add Python versions badge to README ([48ff23e](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/48ff23e2165a3bb15eda22ef8391ffbbc5506fff))
* switch the Python versions badge to a static one ([3d90788](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/3d9078894ac49ea5f077fc8a9d45c9af6fdde0f2))
* switch the Python versions badge to a static one ([8497abb](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/8497abb620f614978a008906ba117495699ee7e8))

## [0.1.5](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/compare/v0.1.4...v0.1.5) (2026-09-14)


### Documentation

* publish the shared CI/CD, security & quality standard ([f73b400](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/f73b400e2a4f7650075b721116422ede591f1528))
* publish the shared CI/CD, security & quality standard ([af84194](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/af8419482a577273bb3a9a1da28b7ca334da519d))
* reconcile ADR-0003 with the CI/CD standardization pass ([965e086](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/965e0864ab30b581b760e5fde1b86707c11a58d7))
* reconcile ADR-0003 with the CI/CD standardization pass ([500112e](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/500112eee4a4e9b6f921ecf3a9dad5c4e006641a))

## [0.1.4](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/compare/v0.1.3...v0.1.4) (2026-09-02)


### Bug Fixes

* **release:** garder fromJSON du sync uv.lock + dispatch de rattrapage ([ac29cd9](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/ac29cd92ec3880cdf25ae373a9d8784b2982fd00))
* **release:** garder fromJSON du sync uv.lock + dispatch de rattrapage ([481b650](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/481b6501698a6901f071afdd1302db17181d1975))

## [0.1.3](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/compare/v0.1.2...v0.1.3) (2026-09-02)


### Bug Fixes

* **audit:** job pip-audit vert + signalement par issue fiabilisé ([63d878e](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/63d878e28d7d31c2cc76c68360d84a5f5fcefe1d))
* **audit:** job vert + issue seule, et répare le signalement ([c1d2705](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/c1d270574b0b36c0ebf7dab8a8b244aa365e5837))
* **release:** recaler uv.lock sur le bump de version ([d06155c](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/d06155c906d99bb3393c1be1e4ec6b77afb3b301))
* **release:** recaler uv.lock sur le bump de version ([dd2a2f5](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/dd2a2f5ef738cef6a3ffbbfce0cc66b05ccfdfe5))

## [0.1.2](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/compare/v0.1.1...v0.1.2) (2026-08-28)


### Bug Fixes

* ruleset tags v* sans bypass Integration ni règle creation ([96869e6](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/96869e6cff122a0d4124c3b6543f7972b74f6d60))
* ruleset tags v* sans bypass Integration ni règle creation ([d5c0ce6](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/d5c0ce67ce08b79911881aa18cdc5c6498b1218e))

## [0.1.1](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/compare/v0.1.0...v0.1.1) (2026-08-28)


### Bug Fixes

* signoff release-please via le fichier de config ([ada5620](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/ada56208854f8584aa176b251e529a5fce450401))
* signoff release-please via le fichier de config, pas l'input ([26f2cff](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/26f2cff2c63090275938521a67c3369c78375e37))
* tolérer les corps de commit longs de Dependabot dans commitlint ([46d02d2](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/46d02d2e82aed6b4830f1109abe7d39e50aff9eb))
* tolérer les corps de commit longs de Dependabot dans commitlint ([34b8f7b](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/34b8f7b2ad995e921edab3bfa24df7c78ad2279d))


### Documentation

* badges CI / Codecov / PyPI / licence dans le README ([a2fe10f](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/a2fe10f707575da51c54d1f06bffedea3a312f77))
* badges CI / Codecov / PyPI / licence dans le README ([9a57021](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/9a570213401eefe2e7b9d2df3ede32acb940296a))
* consolider les notes de recherche CI/CD sur main ([f961893](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/f961893221a714aeae0d1291f128a52bd54f3491))
* JSON reproductible des rulesets main et v* ([e19ec4b](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/e19ec4bd59d27ca6361b9c2a6eb4c4d59148bd3d))
* JSON reproductible des rulesets main et v* ([#27](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/27)) ([2df33f9](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/2df33f988e1d2b584cd6108a1ba929d8ccaa9837))
* research — Dependabot support for uv (map [#17](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/17), ticket [#21](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/21)) ([1058efd](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/1058efdf3ea3dce28feaf9999d0e6b39e4ca6c66))
* research — PyPI Trusted Publishing + OIDC (map [#17](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/17), ticket [#23](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/23)) ([5cc793f](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/5cc793f33839233ce4d1335389e2471c4ba0730b))
* research — release-please for Python + PyPI (map [#17](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/17), ticket [#22](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/22)) ([d372369](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/commit/d372369c802826b628a892dbf88785cca6c51028))
