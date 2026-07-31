export type NewsCategory = "conflict" | "climate" | "politics" | "tech" | "economy";

export interface NewsSource {
  name: string;
  url: string;
  logo: string;
  reliability: "high" | "medium" | "low";
}

export interface NewsItem {
  id: string;
  title: string;
  summary: string;
  fullContent: string;
  category: NewsCategory;
  coordinates: [number, number]; // [longitude, latitude]
  location: string;
  country: string;
  date: string;
  image: string;
  sources: NewsSource[];
  tags: string[];
  views: number;
}

export const NEWS_DATA: NewsItem[] = [
  {
    id: "ukraine-conflict",
    title: "Ukraine : Nouvelles offensives sur le front Est",
    summary:
      "Les forces ukrainiennes ont lancé une contre-offensive majeure dans la région de Donetsk, repoussant les avancées russes. Les combats intenses se concentrent autour de plusieurs villages stratégiques.",
    fullContent: `Les forces armées ukrainiennes ont déclenché une vaste opération militaire dans la région de Donetsk, ciblant plusieurs positions clés tenues par les forces russes depuis plusieurs mois. Selon des sources militaires ukrainiennes, l'opération a permis de reprendre le contrôle d'au moins trois villages et d'infliger des pertes significatives à l'adversaire.

Cette contre-offensive intervient après des semaines de préparation intensive, soutenue par la livraison de nouveaux équipements militaires occidentaux, notamment des chars Leopard 2 et des systèmes d'artillerie à longue portée. Les combats se déroulent principalement à l'est de Bakhmut, une ville stratégique dont la bataille a duré plusieurs mois.

Du côté humanitaire, la situation reste préoccupante : des milliers de civils ont fui les zones de combat, et plusieurs convois d'aide humanitaire ont été bloqués par les affrontements. L'ONU estime que plus de 14 millions d'Ukrainiens ont été déplacés depuis le début du conflit en 2022.

Les partenaires occidentaux de l'Ukraine surveillent attentivement l'évolution de la situation, avec plusieurs capitales européennes qui ont réaffirmé leur soutien militaire et financier à Kiev.`,
    category: "conflict",
    coordinates: [36.5, 49.0],
    location: "Donetsk, Ukraine",
    country: "Ukraine",
    date: "2025-01-14",
    image: "/images/news-ukraine.jpg",
    sources: [
      {
        name: "Reuters",
        url: "https://reuters.com",
        logo: "🔴",
        reliability: "high",
      },
      {
        name: "BBC News",
        url: "https://bbc.com",
        logo: "🔵",
        reliability: "high",
      },
      {
        name: "Le Monde",
        url: "https://lemonde.fr",
        logo: "⚫",
        reliability: "high",
      },
      {
        name: "The Guardian",
        url: "https://theguardian.com",
        logo: "🟣",
        reliability: "high",
      },
    ],
    tags: ["Guerre", "Ukraine", "Russie", "OTAN", "Donetsk"],
    views: 142800,
  },
  {
    id: "gaza-conflict",
    title: "Gaza : Tensions humanitaires au bord du gouffre",
    summary:
      "La situation humanitaire à Gaza atteint un niveau critique selon l'ONU. Les négociations pour un cessez-le-feu reprennent sous médiation internationale avec des propositions inédites.",
    fullContent: `L'ONU tire une nouvelle fois la sonnette d'alarme sur la situation à Gaza, qualifiant la crise humanitaire de « catastrophe sans précédent ». Les hôpitaux fonctionnent en mode dégradé, manquant de médicaments, d'eau potable et d'électricité. Selon les derniers chiffres des agences onusiennes, plus de 2 millions de personnes sont en situation d'insécurité alimentaire grave.

Des pourparlers de paix ont repris au Caire sous l'égide de l'Égypte, du Qatar et des États-Unis. Les médiateurs auraient soumis une nouvelle proposition incluant un cessez-le-feu de six semaines, la libération d'otages en échange de prisonniers palestiniens, et l'ouverture de corridors humanitaires supplémentaires.

Les organisations humanitaires présentes sur le terrain, dont Médecins Sans Frontières et la Croix-Rouge internationale, appellent à un accès immédiat et sans restriction pour acheminer l'aide. Plusieurs pays européens ont annoncé des contributions supplémentaires au fonds d'urgence de l'UNRWA.

La communauté internationale reste divisée sur la réponse à apporter, avec des positions très différentes entre les États-Unis, l'Union européenne, les pays arabes et la Russie.`,
    category: "conflict",
    coordinates: [34.5, 31.5],
    location: "Gaza, Palestine",
    country: "Palestine",
    date: "2025-01-13",
    image: "/images/news-gaza.jpg",
    sources: [
      {
        name: "Al Jazeera",
        url: "https://aljazeera.com",
        logo: "🟤",
        reliability: "high",
      },
      {
        name: "AFP",
        url: "https://afp.com",
        logo: "🔵",
        reliability: "high",
      },
      {
        name: "The New York Times",
        url: "https://nytimes.com",
        logo: "⚫",
        reliability: "high",
      },
    ],
    tags: ["Gaza", "Humanitaire", "ONU", "Cessez-le-feu", "Proche-Orient"],
    views: 234500,
  },
  {
    id: "usa-politics",
    title: "USA : Nouveau bras de fer au Congrès sur la dette fédérale",
    summary:
      "Le Congrès américain est à nouveau paralysé par un désaccord majeur sur le plafond de la dette. Les marchés financiers mondiaux réagissent nerveusement à l'incertitude politique.",
    fullContent: `Le Congrès des États-Unis est une nouvelle fois confronté à une crise institutionnelle autour du plafond de la dette fédérale. Les républicains de la Chambre des représentants ont refusé de voter un relèvement automatique du plafond, exigeant en contrepartie des coupes budgétaires drastiques dans plusieurs programmes sociaux fédéraux.

La Secrétaire au Trésor a averti que les États-Unis pourraient manquer à leurs obligations financières dès la fin du mois si un accord n'est pas trouvé rapidement. Un défaut de paiement américain, même temporaire, aurait des répercussions mondiales considérables sur les marchés obligataires et les taux d'intérêt.

Les négociations entre la Maison Blanche et les leaders républicains au Congrès se déroulent dans un climat tendu. Plusieurs scénarios sont à l'étude : un accord bipartite minimum, l'utilisation du 14ème amendement, ou le recours à des mesures comptables extraordinaires pour gagner du temps.

Les agences de notation S&P et Moody's ont toutes deux averti qu'elles pourraient reconsidérer la note de crédit AAA des États-Unis si la situation n'est pas résolue rapidement, ce qui aurait un impact majeur sur le coût de la dette américaine.`,
    category: "politics",
    coordinates: [-77.0, 38.9],
    location: "Washington D.C., USA",
    country: "États-Unis",
    date: "2025-01-12",
    image: "/images/news-usa.jpg",
    sources: [
      {
        name: "The Washington Post",
        url: "https://washingtonpost.com",
        logo: "🟦",
        reliability: "high",
      },
      {
        name: "Wall Street Journal",
        url: "https://wsj.com",
        logo: "⚫",
        reliability: "high",
      },
      {
        name: "Politico",
        url: "https://politico.com",
        logo: "🔴",
        reliability: "high",
      },
      {
        name: "CNN",
        url: "https://cnn.com",
        logo: "🔴",
        reliability: "medium",
      },
    ],
    tags: ["USA", "Congrès", "Dette", "Politique", "Marchés financiers"],
    views: 98700,
  },
  {
    id: "china-tech",
    title: "Chine : L'IA DeepSeek bouleverse l'ordre mondial technologique",
    summary:
      "La startup chinoise DeepSeek a lancé un modèle d'IA qui rivalise avec GPT-4 à une fraction du coût. Cette percée remet en question la suprématie américaine dans le secteur de l'intelligence artificielle.",
    fullContent: `DeepSeek, une startup chinoise fondée en 2023, a créé un véritable séisme dans l'industrie de l'intelligence artificielle en dévoilant son modèle R1, capable de rivaliser avec les meilleurs modèles américains tels que GPT-4o d'OpenAI et Gemini Ultra de Google, mais à un coût de développement jusqu'à 100 fois inférieur.

Le modèle utilise des techniques d'optimisation novatrices qui permettent d'obtenir des performances comparables avec beaucoup moins de puissance de calcul. Cette approche remet en question la logique de "plus de GPU = meilleure IA" qui a prévalu jusqu'ici dans le secteur, et inquiète les géants américains qui ont investi des dizaines de milliards de dollars dans leurs infrastructures.

Les actions des entreprises de semi-conducteurs, notamment NVIDIA, ont chuté de manière significative à Wall Street suite à cette annonce, les investisseurs remettant en question la durabilité des valorisations actuelles du secteur tech. Nvidia aurait perdu plus de 500 milliards de dollars de capitalisation boursière en une seule journée.

Cette percée soulève également des questions géopolitiques : malgré les restrictions américaines sur l'exportation de puces avancées vers la Chine, les ingénieurs chinois ont réussi à développer des solutions alternatives innovantes. Plusieurs experts voient dans DeepSeek la preuve que les sanctions technologiques américaines ont des effets limités.`,
    category: "tech",
    coordinates: [121.5, 31.2],
    location: "Shanghai, Chine",
    country: "Chine",
    date: "2025-01-20",
    image: "/images/news-china.jpg",
    sources: [
      {
        name: "Financial Times",
        url: "https://ft.com",
        logo: "🟡",
        reliability: "high",
      },
      {
        name: "Bloomberg",
        url: "https://bloomberg.com",
        logo: "⚫",
        reliability: "high",
      },
      {
        name: "TechCrunch",
        url: "https://techcrunch.com",
        logo: "🟢",
        reliability: "medium",
      },
      {
        name: "Wired",
        url: "https://wired.com",
        logo: "🔵",
        reliability: "high",
      },
    ],
    tags: ["IA", "DeepSeek", "Chine", "Technologie", "NVIDIA"],
    views: 412000,
  },
  {
    id: "africa-climate",
    title: "Afrique : La sécheresse du Sahel menace 40 millions de personnes",
    summary:
      "Une sécheresse historique frappe le Sahel, avec des conséquences dévastatrices pour les populations rurales. Les experts climatiques alertent sur l'aggravation irréversible du phénomène.",
    fullContent: `Le Programme alimentaire mondial (PAM) alerte sur une crise alimentaire d'ampleur exceptionnelle qui touche la bande sahélienne s'étendant du Sénégal au Tchad. Avec des précipitations inférieures de 40% à la moyenne sur les 18 derniers mois, les récoltes ont été catastrophiques dans plusieurs pays, notamment le Mali, le Burkina Faso et le Niger.

Les scientifiques du GIEC et des instituts météorologiques africains s'accordent à dire que cette sécheresse est directement liée au changement climatique, qui provoque une intensification et une prolongation des épisodes de sécheresse dans la région. Les modèles climatiques prévoient une aggravation des phénomènes dans les décennies à venir.

La situation est aggravée par les conflits armés qui sévissent dans plusieurs pays du Sahel, rendant difficile l'acheminement de l'aide humanitaire. Des groupes armés contrôlent plusieurs zones rurales et empêchent parfois les organisations humanitaires d'accéder aux populations les plus vulnérables.

La communauté internationale a mobilisé un fonds d'urgence de 2 milliards de dollars, mais les experts estiment que cela ne représente qu'une fraction des besoins réels. Des appels sont lancés pour une aide structurelle à plus long terme, incluant des projets d'irrigation et d'adaptation agricole.`,
    category: "climate",
    coordinates: [5.0, 15.0],
    location: "Sahel, Afrique de l'Ouest",
    country: "Afrique",
    date: "2025-01-10",
    image: "/images/news-africa.jpg",
    sources: [
      {
        name: "RFI",
        url: "https://rfi.fr",
        logo: "🔵",
        reliability: "high",
      },
      {
        name: "Le Monde Afrique",
        url: "https://lemonde.fr/afrique",
        logo: "⚫",
        reliability: "high",
      },
      {
        name: "The Africa Report",
        url: "https://theafricareport.com",
        logo: "🟢",
        reliability: "high",
      },
    ],
    tags: ["Sahel", "Sécheresse", "Climat", "Humanitaire", "Afrique"],
    views: 67300,
  },
  {
    id: "arctic-climate",
    title: "Arctique : La banquise estivale disparaît plus vite que prévu",
    summary:
      "Les scientifiques enregistrent une réduction record de la banquise arctique estivale. Les modèles prévoient désormais des étés sans glace en Arctique dès 2030, soit 20 ans plus tôt que prévu.",
    fullContent: `Une étude publiée dans la revue Nature Climate Change révèle que la banquise arctique disparaît à un rythme nettement supérieur aux prévisions les plus pessimistes du GIEC. Les chercheurs de l'Université de Copenhague et du NSIDC américain ont analysé 45 ans de données satellitaires et concluent que des étés entièrement sans glace pourraient survenir dès 2030.

Cette disparition accélérée de la glace arctique a des conséquences en cascade sur le système climatique mondial : modification des courants océaniques, perturbation du jet-stream affectant les météos des zones tempérées, libération de méthane piégé dans le pergélisol, et montée accélérée des eaux. Le réchauffement arctique est quatre fois plus rapide que la moyenne mondiale.

Les États riverains de l'Arctique — Russie, Canada, États-Unis, Norvège, Danemark — intensifient leur présence militaire dans la région, voyant dans la fonte des glaces l'ouverture de nouvelles routes maritimes commerciales et l'accès à d'importantes ressources naturelles estimées à des milliers de milliards de dollars.

La faune arctique est également gravement menacée : les populations d'ours polaires, de narvals et de morses déclinent rapidement faute d'habitat viable. Plusieurs espèces pourraient disparaître avant la fin du siècle selon les écologistes.`,
    category: "climate",
    coordinates: [-20.0, 80.0],
    location: "Arctique",
    country: "International",
    date: "2025-01-08",
    image: "/images/news-arctic.jpg",
    sources: [
      {
        name: "Nature",
        url: "https://nature.com",
        logo: "🟢",
        reliability: "high",
      },
      {
        name: "Science Magazine",
        url: "https://science.org",
        logo: "🔵",
        reliability: "high",
      },
      {
        name: "NASA",
        url: "https://nasa.gov",
        logo: "🔴",
        reliability: "high",
      },
    ],
    tags: ["Arctique", "Banquise", "Réchauffement climatique", "GIEC", "Biodiversité"],
    views: 89100,
  },
  {
    id: "india-tech",
    title: "Inde : Bengaluru devient le nouveau hub mondial de l'IA",
    summary:
      "L'Inde s'impose comme une puissance montante de l'intelligence artificielle. Bengaluru dépasse désormais San Francisco en nombre de startups IA fondées par an.",
    fullContent: `L'Inde connaît un boom sans précédent dans le secteur de l'intelligence artificielle. La ville de Bengaluru, surnommée la "Silicon Valley de l'Inde", a vu le nombre de startups IA fondées doubler en deux ans, dépassant San Francisco en termes de création d'entreprises selon un rapport du cabinet McKinsey.

Ce boom est soutenu par plusieurs facteurs : un vivier exceptionnel d'ingénieurs formés dans les IIT (Instituts Indiens de Technologie), des coûts de développement compétitifs, un marché domestique de 1,4 milliard de personnes, et une politique gouvernementale ambitieuse avec le programme "India AI Mission" doté de 1,25 milliard de dollars.

Les géants technologiques américains — Google, Microsoft, Amazon — ont massivement investi dans des centres de R&D en Inde, attirés par les talents locaux. Des champions nationaux émergent également, comme Sarvam AI, spécialisé dans les modèles multilingues pour les 22 langues officielles de l'Inde.

L'Inde positionne stratégiquement son développement technologique comme un "troisième chemin" entre les modèles américain et chinois, en mettant l'accent sur l'IA responsable, inclusive et multilingue. Le gouvernement Modi espère faire de l'IA un levier de développement économique massif d'ici 2030.`,
    category: "tech",
    coordinates: [77.6, 12.9],
    location: "Bengaluru, Inde",
    country: "Inde",
    date: "2025-01-15",
    image: "/images/news-india.jpg",
    sources: [
      {
        name: "The Hindu",
        url: "https://thehindu.com",
        logo: "🔴",
        reliability: "high",
      },
      {
        name: "Economic Times",
        url: "https://economictimes.com",
        logo: "🟠",
        reliability: "high",
      },
      {
        name: "MIT Technology Review",
        url: "https://technologyreview.com",
        logo: "🔵",
        reliability: "high",
      },
    ],
    tags: ["Inde", "IA", "Startups", "Tech", "Bengaluru"],
    views: 78600,
  },
];

export const CATEGORY_CONFIG: Record<
  NewsCategory,
  { label: string; color: string; bgColor: string; borderColor: string; pulseColor: string }
> = {
  conflict: {
    label: "Conflit",
    color: "#ef4444",
    bgColor: "bg-red-500",
    borderColor: "border-red-400",
    pulseColor: "bg-red-400",
  },
  climate: {
    label: "Climat",
    color: "#22c55e",
    bgColor: "bg-green-500",
    borderColor: "border-green-400",
    pulseColor: "bg-green-400",
  },
  politics: {
    label: "Politique",
    color: "#3b82f6",
    bgColor: "bg-blue-500",
    borderColor: "border-blue-400",
    pulseColor: "bg-blue-400",
  },
  tech: {
    label: "Tech & IA",
    color: "#a855f7",
    bgColor: "bg-purple-500",
    borderColor: "border-purple-400",
    pulseColor: "bg-purple-400",
  },
  economy: {
    label: "Économie",
    color: "#f59e0b",
    bgColor: "bg-amber-500",
    borderColor: "border-amber-400",
    pulseColor: "bg-amber-400",
  },
};
