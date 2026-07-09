# OpenInfra v0.29.80

## v0.29.80 — Adresse complète DCIM/ITAM et code postal partenaires

OpenInfra v0.29.80 corrige l’exposition réelle des coordonnées DCIM/ITAM dans les parcours opérateur. Les sites DCIM exigent désormais une adresse exploitable avec pays, région, ville, rue, code postal, email et téléphone. Les organisations ITAM exigent le code postal et le téléphone ; les partenaires ITAM exigent le code postal dans leur carte d’identité entreprise.

Les champs `Pays` restent stockés sous forme ISO alpha-2, mais les formulaires web affichent uniquement le nom du pays. Les étages DCIM restent générés par OpenInfra à partir du bâtiment ; les conventions de code et de nom d’étage sont fonctionnelles et adaptées aux attributs réellement utilisés par le modèle interne.
