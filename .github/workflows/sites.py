# ============================================================
#  監視するサイトの一覧（ここだけ編集すればOK）
#  サイトを増やしたいときは { ... }, のブロックをコピーして追加します。
#  1つのサイトに複数の方法を書くと、上から順に試して
#  「最初に新着が取れた方法」を使います。
#
#  方法の種類
#   rss     : RSSフィード（一番安定）
#   html    : ページ内のリンクのうち pattern（正規表現）に合うものを新着として扱う
#   sitemap : サイトマップに新しいURLが増えたら新着として扱う
# ============================================================

DIRECTORY_EXCLUDE = [
    r"^https://[^/]+/?$",                       # トップページ
    r"/(about|contact|faq|privacy|terms)/?$",   # 固定ページ
    r"/(shops|categories)/?$",                  # 一覧ページ
]

SITES = [
    {
        "name": "みせコレ",
        "sources": [
            {"type": "html", "url": "https://mise-colle.com/",
             "pattern": r"^https://mise-colle\.com/\d+/$"},
            {"type": "rss", "url": "https://mise-colle.com/feed/"},
        ],
    },
    {
        "name": "虹色マーチ(chalkmessages)",
        "sources": [
            {"type": "rss", "url": "https://chalkmessages.org/feed/"},
        ],
    },
    {
        "name": "ココイコ(cocoico)",
        "sources": [
            {"type": "html",
             "url": ["https://cocoico.jp/", "https://cocoico.jp/places/"],
             "pattern": r"^https://cocoico\.jp/places/[^/?#]+/?$"},
            {"type": "sitemap", "url": "https://cocoico.jp/wp-sitemap.xml",
             "exclude": [r"^https://[^/]+/?$", r"/(contact|terms|privacy-policy)/?$"]},
        ],
    },
    {
        "name": "ゼヒトモ(ブログ)",
        "sources": [
            {"type": "html",
             "url": ["https://www.zehitomo.com/blog", "https://www.zehitomo.com/"],
             "pattern": r"^https://www\.zehitomo\.com/.+/blog/[^/?#]+$"},
        ],
    },
    {
        "name": "蝶々結び(furreality)",
        "sources": [
            {"type": "rss", "url": "https://furreality.org/feed/"},
        ],
    },
    {
        "name": "Machi List(sectorhubs)",
        "sources": [
            {"type": "sitemap", "url": "https://sectorhubs.com/wp-sitemap.xml",
             "exclude": DIRECTORY_EXCLUDE},
            {"type": "rss", "url": "https://sectorhubs.com/feed/"},
        ],
    },
    {
        "name": "お店紹介ひとめ帳(btj-tech-lab)",
        "sources": [
            {"type": "rss", "url": "https://btj-tech-lab.com/blog/feed/"},
            {"type": "html", "url": "https://btj-tech-lab.com/blog/",
             "pattern": r"^https://btj-tech-lab\.com/blog/\d{4}/\d{2}/\d{2}/"},
        ],
    },
    {
        "name": "AreaNetwork",
        "sources": [
            {"type": "sitemap", "url": "https://areanetwork.jp/wp-sitemap.xml",
             "exclude": DIRECTORY_EXCLUDE},
            {"type": "rss", "url": "https://areanetwork.jp/feed/"},
        ],
    },
    {
        "name": "暮らしアルバム",
        "sources": [
            {"type": "html", "url": "https://kurashi-album.com/",
             "pattern": r"^https://kurashi-album\.com/(essay/[A-Za-z0-9_-]+|company/\d+)/?$"},
            {"type": "rss", "url": "https://kurashi-album.com/feed/"},
        ],
    },
]
