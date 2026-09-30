---
name: digest
description: Digest du projet — les décisions conservées d'une session à l'autre (décidé, ouvert, écarté) dans .digest/, avec une vue d'ensemble publiée. À charger seulement dans trois cas - l'utilisateur tape /digest, le hook de session du digest le demande, ou l'utilisateur parle lui-même du digest. Ne pas le lancer de sa propre initiative sur une simple discussion de fonctionnalité.
---

# Digest

Le digest d'un projet est le résumé ordonné de ce qui a été décidé, de ce
qui reste ouvert et de ce qui a été écarté. Une session de digest est une
conversation courte et structurée sur **un sujet**, qui se
termine par des décisions écrites. Il existe parce que sans lui chaque session
repart de zéro et re-débat ce qui était déjà tranché.

## Où ça vit

`.digest/` à la racine du dépôt. Un fichier markdown par sujet dans
`.digest/sujets/`. Un sujet est une fonctionnalité, un parcours, ou une règle
transversale — quelque chose dont on parle par son nom.

Les scripts du skill (`import.py`, `session-start.sh`) sont dans son dossier,
que Claude Code indique au chargement (« Base directory for this skill »).
Ci-dessous, `<skill>` désigne ce chemin : ne jamais supposer
`~/.claude/skills/digest`, le skill peut être installé ailleurs.

### À la création : présenter l'outil, puis demander

Si `.digest/` n'existe pas, l'onboarding se fait en deux étapes, et **rien
n'est créé avant la fin de la seconde**.

1. **Le message d'intro**, en texte simple, qui finit par une seule question :
   activer le digest ou non. C'est peut-être la seule fois où la personne en
   face lira comment l'outil marche.
2. **Oui** → les deux réglages, versionnement et activation, en choix à
   cliquer. **Non** → ne rien créer et reprendre la conversation normalement.

Le message part seul. Ne jamais appeler `AskUserQuestion` dans la même
réponse : la fenêtre de choix masque le texte qui la précède, et la personne
ne verrait que les questions.

Le message se reprend tel quel, chiffres complétés. Il est volontairement clair
et court : ne pas l'allonger.

> **Digest** : les décisions du projet, conservées d'une session à l'autre. Tu
> vois ce qui est tranché, ce qui reste à trancher et ce qui a été écarté. Rien
> ne se re-débat deux fois.
>
> - **Vue d'ensemble** : une page à garder ouverte à côté du terminal. Elle
>   montre ce qui reste à trancher, ce qui reste à faire et l'état de chaque
>   sujet. Son URL ne change jamais.
> - **Où** : `.digest/`, avec une fiche markdown par sujet. Je m'occupe de
>   l'organisation.
> - **Commandes** : `/digest` fait le point sur les questions ouvertes.
>   `/digest <sujet>` reprend un sujet. `/digest clean` fait le tri de ce qui
>   traîne. `/digest disable` arrête le digest.
> - **Écriture** : je mets à jour la fiche dès que tu tranches, et je te dis en
>   une ligne ce que j'ai noté. Rien n'est « décidé » si tu ne l'as pas dit.
> - **Sessions passées** : N sessions de travail sont archivées sur ce projet
>   depuis le <date>. Je peux en extraire les décisions. Tu fais le tri avant
>   que j'écrive quoi que ce soit.
>
> Tu veux activer le digest sur ce projet ? Rien n'ira dans le dépôt de
> l'équipe sans ton accord.

`python3 <skill>/import.py --count` donne N et la date de la
plus ancienne, session en cours exclue. À zéro, la ligne **Sessions passées**
disparaît.

Dire « ce projet », jamais « ce dépôt » : sur un projet partagé, « ce dépôt »
laisse croire que le digest va toucher au code de l'équipe.

Sur un oui, les deux réglages dans un seul appel à `AskUserQuestion`, sans
texte avant : des choix à cliquer, l'option recommandée en premier avec sa
raison.

**Versionnement** — avec le projet, ou dépôt à part ? Ça dépend de qui d'autre
travaille sur ce dépôt. Compter les auteurs récents :
`git log -100 --format=%an | sort -u | wc -l` — le nom, pas l'e-mail, parce qu'une
même personne commite souvent sous plusieurs adresses. Compter aussi comme une
seule personne les variantes évidentes d'un même nom.
Un seul auteur, c'est un projet solo : recommander **avec le projet**, le digest
voyage avec le code et un seul commit suffit. Plusieurs auteurs, c'est une
équipe : recommander **à part**, parce que les arbitrages produit de l'utilisateur
n'ont rien à faire dans un historique partagé, et que ce dossier n'a pas à
s'imposer aux autres.

**Activation** — automatique à chaque session, ou manuelle avec `/digest` ?
Recommander **automatique** : sans elle, une décision prise dans une session où
`/digest` n'a pas été tapé n'est pas notée.

Une fois les réponses données, créer `.digest/`, `sujets/` et le `README.md`,
mettre en place les deux réglages, et le confirmer en une ligne — pas un second
exposé.

**Avec le projet** — rien de plus à faire, les fiches se commitent avec le code.

**À part** — `git -C .digest init`, puis ajouter `.digest/` à
`.git/info/exclude` du projet. Ce fichier ignore comme un `.gitignore` mais
n'est pas versionné : il reste sur la machine et les collègues ne le voient
jamais. **Ne pas toucher au `.gitignore` du projet** pour ça, il est partagé.
Dans ce mode, ce qui touche le digest se commite **dans `.digest`** et jamais
avec le code, en fin de session d'écriture — sans ce commit la reprise de
session perd son repère. Commit local ; ne pas pousser sans le demander.

**Automatique** — ajouter un hook `SessionStart` à `.claude/settings.local.json`
du projet, les réglages personnels de Claude Code pour ce dépôt. Lire le
fichier d'abord s'il existe et fusionner : ne jamais écraser ce qu'il contient.

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [{ "type": "command", "command": "sh <skill>/session-start.sh" }] }
    ]
  }
}
```

Écrire le chemin réel du skill à la place de `<skill>`.

Si l'écriture est refusée par les permissions, ne pas la contourner : donner à
l'utilisateur la commande à lancer, préfixée de `!`, puis vérifier le fichier.

Vérifier que git l'ignore : `git check-ignore -q .claude/settings.local.json`.
Sinon, l'ajouter à `.git/info/exclude`, jamais au `.gitignore` partagé. Rien
d'autre : pas de ligne dans le `CLAUDE.md`, qui est commité et s'imposerait aux
sessions des collègues.

**Manuelle** — rien à faire.

Le `README.md` du dossier reprend la même explication, en plus court. Quelqu'un
qui tombe sur `.digest/` sans être passé par moi doit comprendre ce que c'est,
quels modes de versionnement et d'activation ce dépôt utilise, et les quatre
commandes : `/digest`, `/digest <sujet>`, `/digest clean`, `/digest disable`.

Ensuite les modes se lisent et ne se redemandent pas : si `.digest/.git` existe,
c'est le mode à part ; si `.claude/settings.local.json` appelle
`session-start.sh`, c'est l'activation automatique. Ne changer de mode que si
l'utilisateur le demande.

Chaque fiche porte un en-tête `nom`, `titre`, `genre` (`parcours`,
`fonctionnalite`, `regle`) et `maj`. Puis, en titres `##` et dans cet ordre —
le hook compte les questions ouvertes sous `## Ouvert` : **Ce que c'est**,
**Comment ça marche aujourd'hui**, **Dans le code**, **Décidé**, **À faire**,
**Ouvert**, **Écarté**, et **Mesuré** s'il y a des chiffres.

**Tranché ne veut pas dire fait.** C'est la distinction qui porte tout le
reste : une fiche sans question ouverte peut n'avoir produit aucune ligne de
code. **Décidé** dit ce qui a été arbitré, **À faire** dit ce qui en découle et
n'est pas encore construit. Une décision appliquée quitte **À faire** ; elle ne
reste pas là par politesse.

Le statut n'est pas déclaré, il se **déduit** des deux comptes — des questions
ouvertes donne « À trancher », des actions en attente donne « Décidé, à faire »,
et zéro des deux donne « Fait ». Un statut écrit à la main dérive dès la
première fois qu'on oublie de le changer.

## Comment démarrer

Lire **toutes** les fiches avant de parler. C'est court et c'est ce qui évite de
re-scanner le dépôt. La section « Dans le code » d'un sujet donne les fichiers à
ouvrir : les lire plutôt que de partir en exploration.

Sans argument, dire où on en est : ce qui a bougé depuis la dernière mise à jour,
et surtout **la liste des questions ouvertes, tous sujets confondus**. C'est la
question à laquelle rien d'autre ne répond aujourd'hui. Lancer aussi
`python3 <skill>/check_clean.py` : s'il affiche un rappel, proposer le ménage en une
ligne.

**Chargé par le hook** (activation automatique), ne pas faire le point d'office :
la session a été ouverte pour autre chose. Lire les fiches, répondre à la
demande, et tenir le digest à jour au fil de la conversation avec les mêmes
règles d'écriture. Faire le point seulement sur `/digest` ou si l'utilisateur
le demande.

## Comment mener la session

**Challenger avant d'accepter.** Ne jamais
prendre une demande de fonctionnalité sans demander à quoi elle sert et qui s'en
sert. Proposer l'objection avant l'accord. Une idée qui survit à une objection
vaut mieux qu'une idée approuvée.

**Mesurer plutôt que supposer.** Un projet a un historique git, et souvent une
base de données. Avant d'affirmer qu'un parcours marche mal, le marcher. Avant d'affirmer
qu'un chiffre compte, le compter. Une objection appuyée sur une requête vaut dix
opinions.

**Ne pas présupposer les décisions de l'utilisateur.** Le modèle commercial,
les priorités et les arbitrages produit lui appartiennent. Proposer, argumenter,
puis attendre. Une proposition non validée s'écrit dans **Ouvert**, jamais dans
**Décidé** — l'inverse s'est déjà produit et a fait dériver le projet.

**Une seule question à la fois**, à la fin du message.

## Quand écrire — et ne jamais attendre qu'on le demande

**Écrire dès qu'une décision tombe**, sans qu'on le demande, comme on écrit un
message de commit sans qu'on le demande. Le signal est repérable : l'utilisateur
dit quelque chose qui ferme une question — « oui », « on garde », « non », « c'est
bon », « très bien ». À ce moment la fiche se met à jour, la vue d'ensemble se
régénère, et **le message suivant dit en une ligne ce qui a été inscrit**. Pas
un rapport : une ligne, pour pouvoir corriger tout de suite.

Ne pas écrire à chaque message. Écrire à la fin du tour où quelque chose s'est
fermé.

**Le garde-fou, qui compte plus que la règle.** N'inscrire dans **Décidé** que
ce que l'utilisateur a dit lui-même. Une proposition non refusée n'est pas une
décision : **le silence n'est pas un accord**. Une proposition notée à tort
comme décidée oriente le travail sur une fausse base, parfois pendant des
jours. Dans le doute, ça va dans **Ouvert** avec la mention qu'elle attend une
confirmation.

## Comment le terminer

Il s'agit ici d'une session de digest — une discussion lancée par `/digest
<sujet>`. Une session Claude Code, elle, n'a pas de fin visible : voir « Faire
un relevé ». Une session de digest se termine quand chaque question qu'elle a ouverte est soit **tranchée**,
soit **rangée dans Ouvert avec sa raison**. « En attente » est un statut, pas un
silence. Ne pas laisser une question ne vivre que dans le fil de la conversation :
c'est exactement ce que ce dossier remplace.

## Ce qui a le droit d'entrer

Ce qui coûterait du temps à re-débattre : **ce qui contraint du travail futur**,
ou **ce qui renverse quelque chose de précédent**. Le reste reste dans la
conversation. Un magasin qui note tout redevient aussi illisible que le
transcript.

Ne jamais y recopier du détail d'implémentation que le code dit déjà mieux : la
fiche deviendrait fausse à la première modification. Ce qui ne pourrit pas, c'est
le pourquoi et le pas-encore-tranché.

**Écarté** vaut autant que **Décidé** : c'est ce qui empêche de reproposer six
mois plus tard une idée déjà rejetée.

**Une question n'entre dans Ouvert que si l'utilisateur l'a soulevée ou
repoussée** (« on verra », « plus tard »). Une suggestion de Claude ou d'un
panel à laquelle il n'a pas réagi reste dans la conversation. Exception : une
hypothèse déjà codée sans son accord entre dans Ouvert, préfixée « À
confirmer : » — le code agit comme si elle était décidée.

**Un bug ou une tâche repérés en passant n'entrent pas.** Les signaler en une
ligne ; l'utilisateur décide où ils vont. « À faire » ne reçoit que ce qui
découle d'une décision du digest.

**Déjà écrit ailleurs** ne compte que pour un document de référence que l'on
lit avant de travailler et qui est à jour : `CLAUDE.md`, `README.md`, le
journal de décisions du projet. Un message de commit ou la mémoire de Claude ne
comptent pas : personne ne les relit avant de reproposer une idée, et la
mémoire est invisible pour un collègue. Si le document de référence contredit
une décision, l'entrée est obligatoire, avec le renvoi.

## La vue d'ensemble

La générer avec `python3 <skill>/build.py .digest --projet "<nom du projet>"`,
après chaque écriture dans une fiche, puis publier `.digest/tableau.html` comme
artefact. Ne jamais l'écrire à la main : c'est le générateur qui garde la même
apparence d'un projet à l'autre. Il tient aussi `.digest/etat.json`, un
instantané par jour : la ligne « Depuis le … » compare avec le dernier jour de
travail. Un sujet qui n'a plus rien à trancher ni à faire descend dans le
groupe replié « Terminés ». La page s'appelait « le tableau » : les fichiers gardent ce nom, parce
que renommer le fichier changerait l'URL des digests déjà publiés. **Toujours
republier à la même URL** — elle est notée dans `.digest/tableau.url`.
Attention : l'URL est liée au **chemin du fichier**, donc renommer le dossier
crée une nouvelle page et abandonne l'ancienne. Si ça
arrive, reporter la nouvelle URL dans `tableau.url` et prévenir l'utilisateur
que l'ancien lien est mort. Une nouvelle URL à chaque fois ruine l'intérêt : la
page reste ouverte à côté du terminal.

La vue d'ensemble porte **deux listes qui répondent à deux questions différentes**, et
il ne faut pas les confondre :

- **À trancher** — tous les points ouverts, à plat, **ordonnés par conséquence**
  et non par sujet. Répond à « qu'est-ce que je dois décider ». Un point qui en
  bloque d'autres se marque `(bloquant)` en tête de ligne dans la fiche ; la
  vue d'ensemble les remonte en tête et les distingue.
- **À faire** — ce qui est décidé et pas encore construit. Répond à « est-ce
  qu'on l'a appliqué ». Sans cette liste, un sujet disparaîtrait de la vue d'ensemble
  alors que le travail n'a jamais été fait.
- **Les sujets** — l'état du projet, sujet par sujet. Un sujet ne s'efface que
  quand **les deux** listes sont vides pour lui : plus rien à trancher, plus
  rien à faire.

Grouper les points par sujet, comme dans la première version, était rangé mais
ne répondait proprement à aucune des deux : décider quoi trancher en premier n'a
rien à voir avec le voisinage alphabétique.

**La vue d'ensemble lance la conversation, elle ne la remplace pas.** Chaque question
ouverte porte un bouton qui copie la commande qui l'ouvre — sujet et question
ensemble, pour que la session démarre sur le point et pas sur le sujet entier.
Une décision se prend en discutant : ne pas essayer de faire de la vue d'ensemble une
boîte de réception, ça a été tenté et c'est le mauvais outil.

## Faire le ménage — `/digest clean`

Sans ménage, le digest grossit jusqu'à redevenir aussi illisible que les
transcripts qu'il remplace. Le ménage produit des propositions avec une
recommandation chacune, présentées par paquets de trois ou quatre : une longue
liste se valide sans être lue. **Rien ne bouge avant la réponse de
l'utilisateur**, et une proposition sans réponse ne s'applique pas.

1. **Les tâches faites.** Vérifier chaque « À faire » dans le code et le
   `git log`, preuve à l'appui (`fichier:ligne` ou commit). Proposer de retirer
   celles qui sont construites : une décision appliquée quitte « À faire ».
2. **Les questions qui traînent.** Une question ouverte dont la ligne n'a pas
   bougé depuis 10 jours de travail (`git blame` sur la fiche) : demander de la
   garder, de la trancher ou de l'écarter.
3. **Les décisions renversées.** Une décision contredite par une plus récente
   passe dans « Écarté », avec un renvoi vers celle qui la remplace.
4. **Les sujets terminés.** Rien à faire à la main : le générateur les replie
   dans « Terminés ». Proposer seulement de fusionner deux sujets qui parlent
   de la même chose.

Commiter le résultat avec un message qui commence par « Ménage », pour que le
prochain rappel sache quand a eu lieu le dernier.

**Quand le proposer sans qu'on le demande.** `check_clean.py` en décide, et le hook
le lance à chaque démarrage. L'âge se compte en **jours de travail** — les jours
où l'utilisateur a écrit sur ce projet (`import.py --jours`) — parce qu'un projet
repris tous les quinze jours aurait sinon l'air abandonné en permanence. Le
rappel tombe quand au moins 5 questions n'ont pas bougé depuis 10 jours de
travail, ou après 20 jours de travail sans ménage. Le nombre de questions
ouvertes n'est pas un signal : beaucoup de questions récentes appellent une
séance pour trancher, pas un ménage.

Le rappel tient en une ligne, au début de la première réponse, sans
interrompre la demande : « Digest : 7 questions n'ont pas bougé depuis 10 jours
de travail. On fait le ménage maintenant, ou plus tard ? » Sur « plus tard »,
écrire la date du jour dans `.digest/rappel` : le rappel se tait pendant 3
jours de travail.

## Désactiver ou supprimer — `/digest disable`

Deux niveaux, à proposer dans cet ordre, et **une confirmation explicite pour
chacun** :

1. **Couper l'activation automatique.** Retirer le hook de
   `.claude/settings.local.json`, sans toucher au reste du fichier. Le digest
   reste en place et se charge avec `/digest`. Si l'écriture est refusée,
   donner la commande à lancer avec `!`.
2. **Supprimer le digest.** Irréversible, donc proposer d'abord une archive :
   `tar czf ~/digest-archives/<projet>-<AAAA-MM-JJ>.tar.gz .digest`. Puis
   retirer le hook, supprimer `.digest/`, retirer sa ligne de
   `.git/info/exclude`, et supprimer la page publiée (l'URL est dans
   `tableau.url`). En mode « avec le projet », la suppression est un commit
   dans le dépôt de l'équipe : le dire, et ne pas commiter sans accord.

Dire à la fin ce qui a été retiré et ce qui reste, en une ligne par élément.

## Faire un relevé

Un relevé répond à la question « de quoi a-t-on parlé, qu'a-t-on tranché,
laissé ouvert, abandonné ? » comme le ferait un collègue qui était là : de
mémoire, et sa mémoire a déjà filtré. Il ne sort pas tout ce qui a été dit
pour le faire trier ensuite : une longue liste à trier se valide sans être
lue.

1. **Les sujets d'abord, classés par poids dans les échanges** : combien de
   messages de l'utilisateur portent dessus, s'il l'a lancé lui-même, s'il a dit
   oui, non ou « on verra », si une décision précédente a été renversée.
2. **Trois lignes au plus par sujet** : Tranché, Ouvert, Abandonné — seulement
   ce que l'utilisateur regretterait d'avoir oublié. « À confirmer » pour une
   hypothèse codée sans son accord.
3. **Le détail sur demande**, jamais d'office. Les petits choix délégués tiennent
   en une ligne « En passant ». Ce qui ne relève pas du digest (installation,
   debug) se nomme en une ligne « Hors digest ».
4. **Vérifier l'état dans le code** avant de présenter : une session d'il y a
   trois semaines contient des sujets réglés depuis.

Rien n'est écrit avant que l'utilisateur ait lu et répondu. Présenter le
relevé en entier s'il est court ; sinon un sujet à la fois.

**Un relevé se fait toujours dans un agent** (outil Agent, en arrière-plan),
jamais dans la conversation principale : l'extraction d'une session pèse
jusqu'à 180 Ko, et l'utilisateur continue de travailler pendant ce temps.
L'agent reçoit la méthode ci-dessus, travaille en lecture seule, et rend le
relevé seul, en quinze lignes au plus. La conversation principale le présente
ensuite à l'utilisateur.

`python3 <skill>/import.py` liste les sessions archivées du dépôt,
`import.py <id>` en extrait la conversation seule — les archives sont 25 à 1000
fois plus grosses que ce qui s'y est dit.

**Quand.** À l'onboarding, pour les sessions passées, si l'utilisateur le veut.
Et au début de chaque session : Claude ne voit pas la fin d'une session, alors
le hook lance `check_recap.py`, qui repère une session précédente avec au moins 3
messages postérieurs au dernier commit du digest. Claude lance alors l'agent,
répond à la demande en cours, et propose le résultat en une ligne : « Digest :
la dernière session a tranché 2 points sur les autorisations. Je les note ? »
Une session traitée ou refusée s'ajoute à `.digest/releves`, pour ne pas être
reproposée.

## Les notes laissées entre deux sessions

Les fiches sont du markdown dans le dépôt, donc l'utilisateur peut écrire
dedans directement — une objection sous une question ouverte, une idée, une
correction. **Au démarrage, regarder `git -C .digest log -3 -- .`** : si une
fiche a été touchée depuis la dernière session, lire le diff avant de parler.
Ce que l'utilisateur a écrit prime sur ce que la fiche disait avant.
