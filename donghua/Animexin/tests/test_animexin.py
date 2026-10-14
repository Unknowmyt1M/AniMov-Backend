import base64
from animexin_scraper import parser, players
from animexin_scraper.episode_parser import parse_episode_label


def test_parse_listing_filters_episode_links():
    html = """
    <div class="listupd">
      <article class="bs"><a class="tip" href="https://animexin.dev/anime/martial-master/" title="Martial Master">
        <img src="https://img/p.jpg"/></a><div class="tt"><h2>Martial MasterMartial Master</h2></div>
        <div class="limit"><span class="typez">ONA</span><span class="bt"><span class="epx">Ongoing</span></span></div>
      </article>
      <article class="bs"><a class="tip" href="https://animexin.dev/martial-master-episode-1/" title="Ep 1">x</a></article>
    </div>"""
    page = parser.parse_listing(html, "https://animexin.dev/")
    assert len(page.cards) == 1
    assert page.cards[0].title == "Martial Master"
    assert page.cards[0].card_type == "ONA"


def test_parse_detail_episodes():
    html = """
    <html><head><meta property="og:image" content="https://img/og.jpg"/></head><body>
    <div class="infox"><h1 class="entry-title">Martial Master</h1>
      <div class="rating"><strong>Rating 8</strong></div>
      <div class="spe"><span><b>Status:</b> Ongoing</span><span><b>Type:</b> ONA</span></div></div>
    <div class="entry-content"><p>Synopsis here long enough.</p></div>
    <div class="genxed"><a>Action</a><a>Fantasy</a></div>
    <div class="info-content"><span>Quality: HD, 1080p</span><span>Language: English, Indonesian</span></div>
    <div class="eplister"><ul>
      <li data-index="1"><a href="/ep1/"><div class="epl-num">1</div><div class="epl-title">Episode 1 English Sub</div><div class="epl-date">Jan 1</div></a></li>
    </ul></div></body></html>"""
    d = parser.parse_detail(html, "https://animexin.dev/anime/martial-master/")
    assert d.title == "Martial Master"
    assert d.poster_url == "https://img/og.jpg"
    assert d.genres == ["Action", "Fantasy"]
    assert d.rating == "8"
    assert len(d.episodes) == 1
    assert d.episodes[0].url == "https://animexin.dev/ep1/"


def test_mirror_base64_decode():
    iframe = '<iframe src="https://dailymotion.com/embed/video/x123"></iframe>'
    val = base64.b64encode(iframe.encode()).decode()
    assert players.decode_mirror_value(val) == "https://dailymotion.com/embed/video/x123"


def test_episode_servers_and_embeds_skip_placeholder():
    good = base64.b64encode(b'<iframe src="https://rumble.com/e/abc"></iframe>').decode()
    bad = base64.b64encode(b'<iframe src="https://tickcounter.com/x"></iframe>').decode()
    html = f"""<html><body><h1>Ep 1</h1>
      <select class="mirror"><option value="{good}">Server Rumble</option>
      <option value="{bad}">Server Bad</option></select>
      <div id="pembed"><iframe src="https://ok.ru/videoembed/1"></iframe></div>
      </body></html>"""
    page = parser.parse_episode_page(html, "https://animexin.dev/ep1/")
    urls = [e.url for e in page.embeds]
    assert any("rumble.com" in u for u in urls)
    assert any("ok.ru" in u for u in urls)
    assert not any("tickcounter" in u for u in urls)


def test_episode_label_title_wins():
    m = parse_episode_label("53 [105]", "Episode 52 [104] (Part - 02)")
    assert m.episode_number == 52
    assert m.part == 2


def test_episode_label_bracket_quality_stripped():
    m1 = parse_episode_label("12 [720P] [RAW]")
    assert m1.episode_number == 12
    m2 = parse_episode_label("45 [1080P]")
    assert m2.episode_number == 45


def test_episode_label_pv_word_boundary():
    m_pvp = parse_episode_label("10", "Episode 10 - PvP Arena")
    assert m_pvp.episode_type == "episode"
    m_pv = parse_episode_label("PV 1", "Official PV Teaser")
    assert m_pv.episode_type == "trailer"


def test_storage_clear_embeds_and_conflict(tmp_path):
    from animexin_scraper.storage import Storage
    from animexin_scraper.models import AnimeCard, EpisodeEntry, Embed
    from animexin_scraper.episode_parser import EpisodeMeta
    db_file = str(tmp_path / "test.db")
    store = Storage(db_file)
    aid = store.upsert_anime(AnimeCard(url="https://animexin.dev/anime/test/", title="Test Anime"))
    eid = store.upsert_episode(aid, EpisodeEntry(url="https://animexin.dev/test-ep-1/", raw_label="1", title="Episode 1"), EpisodeMeta(episode_number=1))
    
    # Add embed
    store.add_embed(eid, None, Embed(url="https://dailymotion.com/video/1", provider="dailymotion"))
    assert len(store.embeds_for_episode(eid)) == 1

    # Conflict update should succeed without duplicate or crash
    store.add_embed(eid, None, Embed(url="https://dailymotion.com/video/1", provider="dailymotion_updated"))
    embeds = store.embeds_for_episode(eid)
    assert len(embeds) == 1
    assert embeds[0]["provider"] == "dailymotion_updated"

    # Clear embeds
    store.clear_episode_embeds(eid)
    assert len(store.embeds_for_episode(eid)) == 0
    store.close()

