export type MediaType = 'music' | 'book' | 'bd';

export interface RSSSource {
  id: string;
  name: string;
  favicon: string;
  title: string;
  date: string;
  url: string;
  excerpt: string;
}

export interface MediaItem {
  id: string;
  type: MediaType;
  title: string;
  artist: string;
  releaseDate: string;
  genre: string;
  publisher: string;
  synopsis: string;
  coverUrl: string;
  color: string;
  accentColor: string;
  rssSources: RSSSource[];
  isNew?: boolean;
}

export const mediaItems: MediaItem[] = [
  {
    id: 'm1',
    type: 'music',
    title: 'Kind of Silence',
    artist: 'Nora Vanthem',
    releaseDate: '12 Jan 2025',
    genre: 'Jazz Ambient',
    publisher: 'Blue Note Records',
    synopsis: "Un voyage introspectif au carrefour du jazz modal et des textures electroniques contemporaines. Nora Vanthem tisse douze compositions epurees ou le silence devient instrument a part entiere. Une oeuvre qui invite a la contemplation.",
    coverUrl: 'https://images.pexels.com/photos/5764281/pexels-photo-5764281.jpeg?auto=compress&cs=tinysrgb&fit=crop&h=600&w=600',
    color: '#1a1a2e',
    accentColor: '#4f6ef7',
    isNew: true,
    rssSources: [
      {
        id: 'r1',
        name: 'Pitchfork',
        favicon: '\u{1F3B5}',
        title: 'Kind of Silence — la renaissance du jazz minimaliste',
        date: '14 Jan 2025',
        url: '#',
        excerpt: "Nora Vanthem livre un album d'une coherence rare, ou chaque note semble pesee au gramme pres. Une artiste a suivre.",
      },
      {
        id: 'r2',
        name: 'Les Inrockuptibles',
        favicon: '\u{1F399}',
        title: 'Nora Vanthem : le silence comme manifeste',
        date: '16 Jan 2025',
        url: '#',
        excerpt: "Entre Miles Davis et Brian Eno, une artiste qui impose sa vision avec autorite. Un disque de l'annee potentiel.",
      },
      {
        id: 'r3',
        name: 'Telerama',
        favicon: '\u{1F4FB}',
        title: "L'album qu'il faut ecouter ce mois-ci",
        date: '20 Jan 2025',
        url: '#',
        excerpt: "Coup de coeur de la redaction. Une oeuvre hors du temps.",
      },
    ],
  },
  {
    id: 'm2',
    type: 'music',
    title: 'Ultraviolet Dreams',
    artist: 'Mele Tupou',
    releaseDate: '3 Fev 2025',
    genre: 'Electronic / Neo-Soul',
    publisher: 'XL Recordings',
    synopsis: "Fusion hypnotique entre la soul urbaine et les synthetiseurs brutalistes. Mele Tupou explore la frontiere entre melancolie digitale et euphorie nocturne sur cet opus de huit titres. Chaque piste est un monde a part entiere.",
    coverUrl: 'https://images.pexels.com/photos/31805824/pexels-photo-31805824.jpeg?auto=compress&cs=tinysrgb&fit=crop&h=600&w=600',
    color: '#16213e',
    accentColor: '#a855f7',
    rssSources: [
      {
        id: 'r4',
        name: 'NME',
        favicon: '\u{1F3B5}',
        title: 'Mele Tupou steps into the future',
        date: '5 Fev 2025',
        url: '#',
        excerpt: 'A record that feels like a transmission from 2030. Bold and beautiful.',
      },
      {
        id: 'r5',
        name: 'Tsugi',
        favicon: '\u{1F39B}',
        title: "Ultraviolet Dreams : l'electro-soul de demain",
        date: '8 Fev 2025',
        url: '#',
        excerpt: "Production milimetree et voix magnetique : un duo gagnant.",
      },
    ],
  },
  {
    id: 'm3',
    type: 'music',
    title: 'Chromatic Drift',
    artist: 'Vessel & The Echoes',
    releaseDate: '19 Fev 2025',
    genre: 'Post-Rock',
    publisher: 'Bella Union',
    synopsis: "Quatrieme album du collectif londonien, Chromatic Drift pousse les limites du post-rock instrumental vers des contrees cinematiques inexplordes. Cordes, guitares et architecture sonore monumentale composent un paysage vertigineux.",
    coverUrl: 'https://images.pexels.com/photos/12204293/pexels-photo-12204293.jpeg?auto=compress&cs=tinysrgb&fit=crop&h=600&w=600',
    color: '#0f3460',
    accentColor: '#22d3ee',
    isNew: true,
    rssSources: [
      {
        id: 'r6',
        name: 'The Quietus',
        favicon: '\u{1F3B8}',
        title: 'Vessel & The Echoes reach new heights',
        date: '21 Fev 2025',
        url: '#',
        excerpt: 'Monumental. Their most ambitious work yet.',
      },
    ],
  },
  {
    id: 'b1',
    type: 'book',
    title: "L'Architecture du Vide",
    artist: 'Celine Marteau',
    releaseDate: '8 Jan 2025',
    genre: 'Roman contemporain',
    publisher: 'Gallimard',
    synopsis: "A Paris, une architecte decouvre que les appartements qu'elle renove recèlent les fragments d'une vie qu'elle pensait avoir oubliee. Un roman sur la memoire, l'espace et ce que nous laissons derriere nous.",
    coverUrl: 'https://images.pexels.com/photos/11652830/pexels-photo-11652830.jpeg?auto=compress&cs=tinysrgb&fit=crop&h=900&w=600',
    color: '#1a0a00',
    accentColor: '#f59e0b',
    isNew: true,
    rssSources: [
      {
        id: 'r7',
        name: 'Le Monde des Livres',
        favicon: '\u{1F4D6}',
        title: 'Celine Marteau — architecte des emotions',
        date: '10 Jan 2025',
        url: '#',
        excerpt: "Une prose ciselee au service d'une histoire qui vous hante longtemps apres la derniere page.",
      },
      {
        id: 'r8',
        name: 'Liberation',
        favicon: '\u{1F4F0}',
        title: 'Les meilleures sorties litteraires de janvier',
        date: '15 Jan 2025',
        url: '#',
        excerpt: "L'Architecture du Vide figure en tete de notre selection mensuelle.",
      },
      {
        id: 'r9',
        name: 'France Culture',
        favicon: '\u{1F399}',
        title: 'Rencontre avec Celine Marteau',
        date: '18 Jan 2025',
        url: '#',
        excerpt: "Un premier roman d'une maturite deconcertante.",
      },
    ],
  },
  {
    id: 'b2',
    type: 'book',
    title: 'The Cartography of Lies',
    artist: 'Rafael Osei',
    releaseDate: '22 Jan 2025',
    genre: 'Thriller litteraire',
    publisher: 'Penguin Press',
    synopsis: "Dans Lagos en 2047, un cartographe decouvre que les nouvelles cartes officielles effacent deliberement certains quartiers de la memoire collective. Un thriller paranoiaque sur le pouvoir, l'identite et la geographie du mensonge.",
    coverUrl: 'https://images.pexels.com/photos/38702030/pexels-photo-38702030.jpeg?auto=compress&cs=tinysrgb&fit=crop&h=900&w=600',
    color: '#0d1b2a',
    accentColor: '#34d399',
    rssSources: [
      {
        id: 'r10',
        name: 'The Guardian Books',
        favicon: '\u{1F4DA}',
        title: "Rafael Osei's debut is unmissable",
        date: '24 Jan 2025',
        url: '#',
        excerpt: "Part thriller, part political manifesto. Extraordinary debut.",
      },
      {
        id: 'r11',
        name: 'Afropages',
        favicon: '\u{1F4D6}',
        title: 'Rafael Osei cartographie le mensonge',
        date: '28 Jan 2025',
        url: '#',
        excerpt: "Une voix puissante dans la litterature africaine contemporaine.",
      },
    ],
  },
  {
    id: 'b3',
    type: 'book',
    title: 'Eclats de Givre',
    artist: 'Hanna Bergstrom',
    releaseDate: '5 Fev 2025',
    genre: 'Litterature nordique',
    publisher: 'Actes Sud',
    synopsis: "Dans la Laponie hivernale, une photographe revient sur les lieux de son enfance et plonge dans les secrets enfouis d'une communaute isolee. Un roman envoutant sur les origines, la survie et les paysages interieurs.",
    coverUrl: 'https://images.pexels.com/photos/9325323/pexels-photo-9325323.jpeg?auto=compress&cs=tinysrgb&fit=crop&h=900&w=600',
    color: '#0e1c2f',
    accentColor: '#93c5fd',
    isNew: true,
    rssSources: [
      {
        id: 'r12',
        name: 'Transfuge',
        favicon: '\u2744',
        title: 'Hanna Bergstrom, lumiere froide du Nord',
        date: '7 Fev 2025',
        url: '#',
        excerpt: "Un roman-paysage d'une beaute glaciale et envoutante.",
      },
    ],
  },
  {
    id: 'c1',
    type: 'bd',
    title: 'Synapse',
    artist: 'Yuki Morimoto',
    releaseDate: '15 Jan 2025',
    genre: 'Science-fiction / Manga',
    publisher: 'Kana',
    synopsis: "Dans un Tokyo post-neurologique, des humains augmentes vivent connectes en reseau permanent. Yuki Morimoto signe un chef-d'oeuvre graphique sur la conscience collective et l'individu face a la dissolution identitaire.",
    coverUrl: 'https://images.pexels.com/photos/6214570/pexels-photo-6214570.jpeg?auto=compress&cs=tinysrgb&fit=crop&h=1067&w=800',
    color: '#1a0033',
    accentColor: '#e879f9',
    isNew: true,
    rssSources: [
      {
        id: 'r13',
        name: 'ActuaBD',
        favicon: '\u{1F4AC}',
        title: "Synapse : le manga de l'annee ?",
        date: '17 Jan 2025',
        url: '#',
        excerpt: "Un dessin d'une precision hallucinante au service d'un recit qui interroge notre rapport a la technologie.",
      },
      {
        id: 'r14',
        name: 'Manga News',
        favicon: '\u{1F1EF}\u{1F1F5}',
        title: 'Yuki Morimoto — le prodige du manga SF',
        date: '20 Jan 2025',
        url: '#',
        excerpt: "Synapse s'impose d'emblee comme un incontournable du genre.",
      },
      {
        id: 'r15',
        name: 'Telerama',
        favicon: '\u{1F4FA}',
        title: 'La BD de la semaine : Synapse',
        date: '22 Jan 2025',
        url: '#',
        excerpt: "Vertigineux. Morimoto renouvelle l'esthetique cyberpunk avec brio.",
      },
    ],
  },
  {
    id: 'c2',
    type: 'bd',
    title: 'Les Murmures du Delta',
    artist: 'Awa Diallo & Cleo Nkosi',
    releaseDate: '29 Jan 2025',
    genre: 'BD franco-belge / Afrofuturisme',
    publisher: 'Dargaud',
    synopsis: "Un road trip epique a travers un Senegal futuriste ou l'eau est devenue la monnaie universelle. Le duo Diallo/Nkosi signe une fable ecologique d'une richesse visuelle stupefiante et d'une profondeur narrative rare.",
    coverUrl: 'https://images.pexels.com/photos/15326117/pexels-photo-15326117.jpeg?auto=compress&cs=tinysrgb&fit=crop&h=1067&w=800',
    color: '#1a0800',
    accentColor: '#fb923c',
    rssSources: [
      {
        id: 'r16',
        name: 'BDGest',
        favicon: '\u{1F4D5}',
        title: "Les Murmures du Delta — chef-d'oeuvre afrofuturiste",
        date: '31 Jan 2025',
        url: '#',
        excerpt: "Une oeuvre majeure qui s'inscrit dans la grande tradition de la BD d'auteur.",
      },
      {
        id: 'r17',
        name: 'France Inter',
        favicon: '\u{1F4FB}',
        title: "La BD qui parle d'eau et d'avenir",
        date: '2 Fev 2025',
        url: '#',
        excerpt: "Bouleversant de beaute et d'intelligence.",
      },
    ],
  },
  {
    id: 'c3',
    type: 'bd',
    title: 'Orbital Drift',
    artist: 'Marco Pellegrini',
    releaseDate: '12 Fev 2025',
    genre: 'Comics / Space Opera',
    publisher: 'Image Comics',
    synopsis: "A bord d'une station orbitale en derive, l'equipage de cinq astronautes doit affronter une entite inconnue tout en gerant les fractures humaines. Pellegrini maitrise l'art du decoupage cinematique avec une virtuosite epoustouflante.",
    coverUrl: 'https://images.pexels.com/photos/20085947/pexels-photo-20085947.jpeg?auto=compress&cs=tinysrgb&fit=crop&h=1067&w=800',
    color: '#001a33',
    accentColor: '#38bdf8',
    isNew: true,
    rssSources: [
      {
        id: 'r18',
        name: 'Comic Book Resources',
        favicon: '\u{1F9B8}',
        title: 'Orbital Drift #1 — a bold debut arc',
        date: '14 Fev 2025',
        url: '#',
        excerpt: "Pellegrini brings cinematic grandeur to sequential art. A must-read.",
      },
    ],
  },
];
