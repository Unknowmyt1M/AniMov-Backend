import { Video, Short, NotificationItem } from '../types';

export const CATEGORIES = [
  "All",
  "Action",
  "Romance",
  "Isekai",
  "Slice of Life",
  "Sci-Fi",
  "Fantasy",
  "Recently Added",
  "Trending",
  "Top Rated",
  "Movies",
  "OVAs"
];

export const INITIAL_VIDEOS: Video[] = [
  {
    id: 1,
    title: "Neon Genesis: Cyber City - Episode 12 (Finale)",
    channel: "Studio Trigger",
    channelAvatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Trigger",
    subscribers: "3.4M",
    views: "1.2M",
    viewsCount: 1200000,
    time: "2 hours ago",
    duration: "24:00",
    ep: 12,
    tags: ["SUB", "1080p"],
    thumbnail: "https://images.unsplash.com/photo-1605806616949-1e87b487cb2a?w=800&q=80",
    videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4",
    category: "Sci-Fi",
    description: "The climactic season finale of Cyber City! In a cyberpunk metropolis where magic meets machinery, a young detective uncovers a conspiracy that threatens the very fabric of reality. Witness the ultimate showdown animated with Studio Trigger's signature high-octane sakuga.",
    likes: 84200,
    dislikes: 620,
    isLiked: false,
    isDisliked: false,
    isSubscribed: false,
    isSaved: false,
    comments: [
      {
        id: "c1",
        author: "CyberOtaku99",
        avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=CyberOtaku",
        text: "The sakuga animation at 18:30 gave me literal chills! Studio Trigger never misses with their season finales 🔥",
        time: "1 hour ago",
        likes: 1420
      },
      {
        id: "c2",
        author: "Aoi_Sakura",
        avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Aoi",
        text: "Please tell me Season 2 is confirmed! You can't just leave us on that post-credits cliffhanger 😭",
        time: "45 minutes ago",
        likes: 856
      },
      {
        id: "c3",
        author: "NeoTokyoVibes",
        avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=NeoTokyo",
        text: "The soundtrack during the final clash was peak orchestral synthwave. 10/10 masterclass.",
        time: "20 minutes ago",
        likes: 312
      }
    ]
  },
  {
    id: 2,
    title: "Wandering Swordsman - Episode 4",
    channel: "Bones Animation",
    channelAvatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Bones",
    subscribers: "2.8M",
    views: "850K",
    viewsCount: 850000,
    time: "5 hours ago",
    duration: "23:45",
    ep: 4,
    tags: ["DUB", "HD"],
    thumbnail: "https://images.unsplash.com/photo-1578632767115-351597cf2477?w=800&q=80",
    videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/Sintel.mp4",
    category: "Action",
    description: "A masterless samurai journeys through the misty bamboo forests of the northern provinces, encountering a mysterious rogue martial artist who holds the secrets to the vanished dragon clan.",
    likes: 54100,
    dislikes: 410,
    isLiked: false,
    isDisliked: false,
    isSubscribed: false,
    isSaved: false,
    comments: [
      {
        id: "c4",
        author: "KenjutsuMaster",
        avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Kenjutsu",
        text: "The sword choreography is historically grounded yet wonderfully stylish.",
        time: "3 hours ago",
        likes: 420
      }
    ]
  },
  {
    id: 3,
    title: "Magical Academy: First Year - Episode 1",
    channel: "KyoAni",
    channelAvatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=KyoAni",
    subscribers: "4.1M",
    views: "2.1M",
    viewsCount: 2100000,
    time: "1 day ago",
    duration: "45:00",
    ep: 1,
    tags: ["SUB", "PREMIERE"],
    thumbnail: "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&q=80",
    videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
    category: "Fantasy",
    description: "A double-length special premiere episode introducing the grand halls of Celestion Academy, where ancient arcane arts meet modern teen friendships and high stakes spellcasting tournaments.",
    likes: 198000,
    dislikes: 1100,
    isLiked: false,
    isDisliked: false,
    isSubscribed: false,
    isSaved: false,
    comments: [
      {
        id: "c5",
        author: "MageKnight_Leo",
        avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Leo",
        text: "KyoAni's lighting and background art is on a whole different dimension. Instant Anime of the Season candidate!",
        time: "18 hours ago",
        likes: 2450
      }
    ]
  },
  {
    id: 4,
    title: "Galactic Frontiers - Episode 8",
    channel: "Sunrise",
    channelAvatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Sunrise",
    subscribers: "1.9M",
    views: "420K",
    viewsCount: 420000,
    time: "2 days ago",
    duration: "24:10",
    ep: 8,
    tags: ["SUB", "DUB"],
    thumbnail: "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800&q=80",
    videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
    category: "Sci-Fi",
    description: "The battleship Asteria navigates the treacherous asteroid belt of Kepler-22b while being pursued by unidentified stealth mecha drones. Commander Ren prepares the planetary defense cannon.",
    likes: 31200,
    dislikes: 290,
    isLiked: false,
    isDisliked: false,
    isSubscribed: false,
    isSaved: false,
    comments: [
      {
        id: "c6",
        author: "MechaPilot01",
        avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Mecha",
        text: "Sunrise proves once again why they are the absolute undisputed kings of hard sci-fi mecha warfare.",
        time: "1 day ago",
        likes: 512
      }
    ]
  },
  {
    id: 5,
    title: "Spirit World Detective - Episode 22",
    channel: "MAPPA",
    channelAvatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=MAPPA",
    subscribers: "5.2M",
    views: "3.5M",
    viewsCount: 3500000,
    time: "3 days ago",
    duration: "23:55",
    ep: 22,
    tags: ["SUB", "4K"],
    thumbnail: "https://images.unsplash.com/photo-1541562232579-512a21360020?w=800&q=80",
    videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
    category: "Action",
    description: "Dark spirits infiltrate the underworld parliament in Tokyo. Detective Kazuki unleashes his cursed shadow technique to rescue the captive shrine maiden before the eclipse ritual finishes.",
    likes: 290000,
    dislikes: 2100,
    isLiked: false,
    isDisliked: false,
    isSubscribed: false,
    isSaved: false,
    comments: [
      {
        id: "c7",
        author: "ShinigamiLover",
        avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Shini",
        text: "MAPPA animators really poured their heart and soul into every single frame of this fight sequence!",
        time: "2 days ago",
        likes: 3890
      }
    ]
  },
  {
    id: 6,
    title: "Slice of Tokyo - Episode 5",
    channel: "A-1 Pictures",
    channelAvatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=A1",
    subscribers: "2.2M",
    views: "150K",
    viewsCount: 150000,
    time: "4 days ago",
    duration: "24:00",
    ep: 5,
    tags: ["SUB"],
    thumbnail: "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=800&q=80",
    videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4",
    category: "Slice of Life",
    description: "A cozy rainy afternoon in Shimokitazawa. Three barista students experiment with latte art while preparing for the annual neighbourhood indie music festival.",
    likes: 19500,
    dislikes: 95,
    isLiked: false,
    isDisliked: false,
    isSubscribed: false,
    isSaved: false,
    comments: [
      {
        id: "c8",
        author: "ChillVibesOnly",
        avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Chill",
        text: "The ultimate comfort anime. This episode healed my soul after a long exhausting week at college.",
        time: "3 days ago",
        likes: 670
      }
    ]
  },
  {
    id: 7,
    title: "Demon Hunter's Blade - Movie Trailer",
    channel: "Ufotable",
    channelAvatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Ufo",
    subscribers: "6.8M",
    views: "10M",
    viewsCount: 10000000,
    time: "1 week ago",
    duration: "02:30",
    ep: null,
    tags: ["TRAILER", "4K"],
    thumbnail: "https://images.unsplash.com/photo-1509299349698-dc98ec697624?w=800&q=80",
    videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyBlazes.mp4",
    category: "Movies",
    description: "Official theatrical trailer for the worldwide cinema release of Demon Hunter's Blade: The Infinite Mountain. Coming to IMAX and Dolby Cinema this autumn.",
    likes: 920000,
    dislikes: 4200,
    isLiked: false,
    isDisliked: false,
    isSubscribed: false,
    isSaved: false,
    comments: [
      {
        id: "c9",
        author: "UfotableSimp",
        avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=UfoSimp",
        text: "Unlimited Budget Works strikes again! IMAX tickets booked day one without a second thought.",
        time: "5 days ago",
        likes: 12400
      }
    ]
  },
  {
    id: 8,
    title: "Mecha Assault: Zero - Episode 10",
    channel: "Production I.G",
    channelAvatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=IG",
    subscribers: "2.5M",
    views: "600K",
    viewsCount: 600000,
    time: "1 week ago",
    duration: "24:20",
    ep: 10,
    tags: ["DUB"],
    thumbnail: "https://images.unsplash.com/photo-1535295972055-1c762f4483e5?w=800&q=80",
    videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
    category: "Action",
    description: "The rogue AI unit codenamed 'Ares' breaches the orbital elevator. Squad leader Elena deploys the experimental heavy railgun exoskeleton in a desperate counter-assault.",
    likes: 48000,
    dislikes: 310,
    isLiked: false,
    isDisliked: false,
    isSubscribed: false,
    isSaved: false,
    comments: [
      {
        id: "c10",
        author: "GundamGeek",
        avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Gundam",
        text: "Sound design in this episode is next level. That railgun charging hum through headphones was insane.",
        time: "6 days ago",
        likes: 890
      }
    ]
  }
];

export const INITIAL_SHORTS: Short[] = [
  {
    id: 1,
    title: "Epic Fight Scene AMV 🤯",
    views: "5M",
    thumbnail: "https://images.unsplash.com/photo-1560930950-5c20d801386d?w=400&h=700&fit=crop",
    videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
    channel: "AMV_God",
    channelAvatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=AMVGod",
    likes: 412000
  },
  {
    id: 2,
    title: "Best Anime Moments 2026",
    views: "2.1M",
    thumbnail: "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=400&h=700&fit=crop",
    videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
    channel: "AnimeRecaps",
    channelAvatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Recaps",
    likes: 184000
  },
  {
    id: 3,
    title: "When the DOOM music kicks in",
    views: "8.4M",
    thumbnail: "https://images.unsplash.com/photo-1519669011783-4eaa95fa1b7d?w=400&h=700&fit=crop",
    videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4",
    channel: "BlerdCentral",
    channelAvatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Blerd",
    likes: 720000
  },
  {
    id: 4,
    title: "Sad Anime Edits 💔",
    views: "1.2M",
    thumbnail: "https://images.unsplash.com/photo-1516450360452-9312f5e86fc7?w=400&h=700&fit=crop",
    videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyBlazes.mp4",
    channel: "LofiOtaku",
    channelAvatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=LofiOtaku",
    likes: 98000
  },
  {
    id: 5,
    title: "Top 10 Isekai Protagonists",
    views: "900K",
    thumbnail: "https://images.unsplash.com/photo-1542451542907-6cf80ff362d6?w=400&h=700&fit=crop",
    videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerMeltdowns.mp4",
    channel: "IsekaiWeekly",
    channelAvatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Isekai",
    likes: 67000
  },
  {
    id: 6,
    title: "Sakuga Compilation #42",
    views: "3.3M",
    thumbnail: "https://images.unsplash.com/photo-1552820728-8b83bb6b773f?w=400&h=700&fit=crop",
    videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4",
    channel: "SakugaSakura",
    channelAvatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Sakura",
    likes: 310000
  }
];

export const INITIAL_NOTIFICATIONS: NotificationItem[] = [
  {
    id: "n1",
    title: "New Episode Alert!",
    message: "Neon Genesis: Cyber City Episode 12 is now streaming in 1080p!",
    time: "2 hours ago",
    unread: true,
    type: "episode",
    thumbnail: "https://images.unsplash.com/photo-1605806616949-1e87b487cb2a?w=120&q=80"
  },
  {
    id: "n2",
    title: "Trending AMV Drop",
    message: "AMV_God just published: Epic Fight Scene AMV 🤯",
    time: "4 hours ago",
    unread: true,
    type: "amv",
    thumbnail: "https://images.unsplash.com/photo-1560930950-5c20d801386d?w=120&q=80"
  },
  {
    id: "n3",
    title: "Studio Trigger Announcement",
    message: "Season 2 production officially announced for late 2026!",
    time: "1 day ago",
    unread: false,
    type: "announcement"
  }
];
